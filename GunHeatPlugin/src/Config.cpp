#include "Config.h"

namespace
{
	std::string Trim(std::string_view a_value)
	{
		auto begin = a_value.begin();
		auto end = a_value.end();

		while (begin != end && std::isspace(static_cast<unsigned char>(*begin))) {
			++begin;
		}
		while (begin != end && std::isspace(static_cast<unsigned char>(*(end - 1)))) {
			--end;
		}

		return { begin, end };
	}

	float ParseFloat(std::string_view a_value, float a_default)
	{
		float result = a_default;
		const auto trimmed = Trim(a_value);
		const auto [ptr, ec] = std::from_chars(trimmed.data(), trimmed.data() + trimmed.size(), result);
		return ec == std::errc{} ? result : a_default;
	}

	bool ParseBool(std::string_view a_value, bool a_default)
	{
		auto trimmed = Trim(a_value);
		std::ranges::transform(trimmed, trimmed.begin(), [](unsigned char a_char) {
			return static_cast<char>(std::tolower(a_char));
		});

		if (trimmed == "1" || trimmed == "true" || trimmed == "yes" || trimmed == "on") {
			return true;
		}
		if (trimmed == "0" || trimmed == "false" || trimmed == "no" || trimmed == "off") {
			return false;
		}
		return a_default;
	}

	bool ParseFormID(std::string_view a_value, RE::TESFormID& a_result)
	{
		auto trimmed = Trim(a_value);
		if (trimmed.starts_with("0x") || trimmed.starts_with("0X")) {
			trimmed.erase(0, 2);
		}

		if (trimmed.empty()) {
			return false;
		}

		RE::TESFormID parsed = 0;
		const auto [ptr, ec] = std::from_chars(trimmed.data(), trimmed.data() + trimmed.size(), parsed, 16);
		if (ec != std::errc{} || ptr != trimmed.data() + trimmed.size()) {
			return false;
		}

		a_result = parsed;
		return true;
	}

	std::uint32_t ParseUInt(std::string_view a_value, std::uint32_t a_default)
	{
		auto trimmed = Trim(a_value);
		std::uint32_t result = a_default;
		const auto [ptr, ec] = std::from_chars(trimmed.data(), trimmed.data() + trimmed.size(), result);
		return ec == std::errc{} && ptr == trimmed.data() + trimmed.size() ? result : a_default;
	}

	std::unordered_set<RE::TESFormID> ParseFormIDList(std::string_view a_value)
	{
		std::unordered_set<RE::TESFormID> result;
		std::size_t start = 0;
		while (start <= a_value.size()) {
			const auto comma = a_value.find(',', start);
			const auto end = comma == std::string_view::npos ? a_value.size() : comma;
			RE::TESFormID formID = 0;
			if (ParseFormID(a_value.substr(start, end - start), formID)) {
				result.insert(formID);
			}
			if (comma == std::string_view::npos) {
				break;
			}
			start = comma + 1;
		}
		return result;
	}
}

Config& Config::Get()
{
	static Config config;
	return config;
}

void Config::Load(std::filesystem::path a_path)
{
	std::unique_lock locker(mutex_);
	ParseFile(a_path, false);

	// Mod Configuration Menu writes the player's choices to Data\MCM\Settings\<mod>.ini
	// in plain [Section] key=value form - the same shape this parser already reads, and
	// the same convention other F4SE mods here use (BPR, UneducatedShooter,
	// WeaponFamiliarity). Because MCM derives the section from the "id:Section" suffix in
	// config.json, naming the MCM ids after our own keys makes this a straight overlay:
	// no Papyrus involvement, and the mod still works with MCM absent.
	ParseFile(MCM_SETTINGS_PATH, true);

	Finalize();
}

void Config::ReloadOverrides()
{
	// Papyrus reads the heat curve through GetHeatSetting(), which lands here, and
	// LoadIniConfig() asks for nine settings on every single shot. Unthrottled that was
	// nine file opens and reparses per shot - 4,573 in one logged session, every one on
	// the game thread. That starved the VM badly enough that the heat timer stopped
	// firing, which froze the effect because only the timer decays heat.
	//
	// One read per second keeps MCM edits feeling immediate while costing nothing.
	// The whole body is exclusive, throttle stamp included: lastOverrideLoad_ is a plain
	// time_point that both the game thread and the Papyrus VM thread reach through here.
	std::unique_lock locker(mutex_);

	const auto now = std::chrono::steady_clock::now();
	if (lastOverrideLoad_ != std::chrono::steady_clock::time_point{} &&
		(now - lastOverrideLoad_) < std::chrono::milliseconds(1000)) {
		return;
	}
	lastOverrideLoad_ = now;

	ParseFile(MCM_SETTINGS_PATH, true);
	Finalize();
}

void Config::ParseFile(std::filesystem::path a_path, bool a_optional)
{
	std::ifstream file(a_path);
	if (!file) {
		if (!a_optional) {
			logger::warn("config not found, using defaults: {}", a_path.string());
		} else if (debugLogging_) {
			logger::info("no MCM overrides at {}", a_path.string());
		}
		return;
	}

	if (a_optional && debugLogging_) {
		logger::info("applying MCM overrides from {}", a_path.string());
	}

	std::string section;
	std::string line;
	// Canonical key wins within a file; reset per file to preserve overlay priority.
	bool canonicalPuffOverlapSeen = false;
	while (std::getline(file, line)) {
		const auto comment = line.find_first_of(";#");
		if (comment != std::string::npos) {
			line.erase(comment);
		}

		line = Trim(line);
		if (line.empty()) {
			continue;
		}

		if (line.front() == '[' && line.back() == ']') {
			section = Trim(std::string_view(line).substr(1, line.size() - 2));
			continue;
		}

		const auto equals = line.find('=');
		if (equals == std::string::npos) {
			continue;
		}

		const auto key = Trim(std::string_view(line).substr(0, equals));
		const auto value = Trim(std::string_view(line).substr(equals + 1));
		const auto fullKey = section + "." + key;

		if (section == "Haze" && key == "fIntensityCeiling") {
			intensityCeiling_ = std::clamp(ParseFloat(value, intensityCeiling_), 0.0F, 1.0F);
			floats_[fullKey] = intensityCeiling_;
		} else if (section == "Haze" && key == "bRenderEnabled") {
			renderEnabled_ = ParseBool(value, renderEnabled_);
			floats_[fullKey] = renderEnabled_ ? 1.0F : 0.0F;
		} else if (section == "Haze" && key == "sArtObjectPlugin") {
			artObjectPlugin_ = value;
		} else if (section == "Haze" && key == "sArtObjectFormID") {
			RE::TESFormID formID = 0;
			if (ParseFormID(value, formID)) {
				artObjectFormID_ = formID;
			}
		} else if (section == "Haze" && key == "bPreferFireNode") {
			preferFireNode_ = ParseBool(value, preferFireNode_);
			floats_[fullKey] = preferFireNode_ ? 1.0F : 0.0F;
		} else if (section == "Haze" && key == "fRefractionMinStrength") {
			refractionMinStrength_ = std::clamp(ParseFloat(value, refractionMinStrength_), 0.0F, 4.0F);
			floats_[fullKey] = refractionMinStrength_;
		} else if (section == "Haze" && key == "fVisibilityCurve") {
			visibilityCurve_ = std::clamp(ParseFloat(value, visibilityCurve_), 0.1F, 4.0F);
			floats_[fullKey] = visibilityCurve_;
		} else if (section == "Haze" && key == "fRefractionMaxStrength") {
			refractionMaxStrength_ = std::clamp(ParseFloat(value, refractionMaxStrength_), 0.0F, 4.0F);
			floats_[fullKey] = refractionMaxStrength_;
		} else if (section == "Haze" && key == "fArtOffsetUp") {
			artOffsetUp_ = std::clamp(ParseFloat(value, artOffsetUp_), -128.0F, 128.0F);
			floats_[fullKey] = artOffsetUp_;
		} else if (section == "Haze" && key == "fArtOffsetForward") {
			artOffsetForward_ = std::clamp(ParseFloat(value, artOffsetForward_), -128.0F, 128.0F);
			floats_[fullKey] = artOffsetForward_;
		} else if (section == "Haze" && key == "fArtOffsetSide") {
			artOffsetSide_ = std::clamp(ParseFloat(value, artOffsetSide_), -128.0F, 128.0F);
			floats_[fullKey] = artOffsetSide_;
		} else if (section == "Haze" && key == "fSizeWidth") {
			sizeWidth_ = std::clamp(ParseFloat(value, sizeWidth_), 0.1F, 4.0F);
			floats_[fullKey] = sizeWidth_;
		} else if (section == "Haze" && key == "fSizeHeight") {
			sizeHeight_ = std::clamp(ParseFloat(value, sizeHeight_), 0.1F, 4.0F);
			floats_[fullKey] = sizeHeight_;
		} else if (section == "Haze" && key == "bSmearEnabled") {
			smearEnabled_ = ParseBool(value, smearEnabled_);
			floats_[fullKey] = smearEnabled_ ? 1.0F : 0.0F;
		} else if (section == "Haze" && key == "fSmearGain") {
			smearGain_ = std::clamp(ParseFloat(value, smearGain_), 0.0F, 0.5F);
			floats_[fullKey] = smearGain_;
		} else if (section == "Haze" && key == "fSmearMaxOffset") {
			smearMaxOffset_ = std::clamp(ParseFloat(value, smearMaxOffset_), 0.0F, 64.0F);
			floats_[fullKey] = smearMaxOffset_;
		} else if (section == "Haze" && key == "fSmearSmoothing") {
			smearSmoothing_ = std::clamp(ParseFloat(value, smearSmoothing_), 0.01F, 2.0F);
			floats_[fullKey] = smearSmoothing_;
		} else if (section == "Haze" && key == "bPulseEnabled") {
			pulseEnabled_ = ParseBool(value, pulseEnabled_);
			floats_[fullKey] = pulseEnabled_ ? 1.0F : 0.0F;
		} else if (section == "Haze" && key == "fPulseStrength") {
			pulseStrength_ = std::clamp(ParseFloat(value, pulseStrength_), 0.0F, 1.0F);
			floats_[fullKey] = pulseStrength_;
		} else if (section == "Haze" && key == "fPuffScale") {
			puffScale_ = std::clamp(ParseFloat(value, puffScale_), 0.0F, 1.5F);
			floats_[fullKey] = puffScale_;
		} else if (section == "Haze" && key == "fPuffRise") {
			puffRise_ = std::clamp(ParseFloat(value, puffRise_), 0.0F, 32.0F);
			floats_[fullKey] = puffRise_;
		} else if (section == "Haze" && (key == "iPuffMaxOverlap" || key == "uPuffMaxOverlap")) {
			// MCM supports i-prefixed integers. Keep u-prefixed INIs readable.
			if (key == "iPuffMaxOverlap" || !canonicalPuffOverlapSeen) {
				canonicalPuffOverlapSeen = key == "iPuffMaxOverlap";
				puffMaxOverlap_ = std::clamp(ParseUInt(value, puffMaxOverlap_), 1U, 24U);
				floats_["Haze.iPuffMaxOverlap"] = static_cast<float>(puffMaxOverlap_);
				floats_["Haze.uPuffMaxOverlap"] = static_cast<float>(puffMaxOverlap_);
			}
		} else if (section == "Haze" && key == "bDriveScroll") {
			driveScroll_ = ParseBool(value, driveScroll_);
			floats_[fullKey] = driveScroll_ ? 1.0F : 0.0F;
		} else if (section == "Haze" && key == "fScrollTilesPerSecond") {
			scrollTilesPerSecond_ = std::clamp(ParseFloat(value, scrollTilesPerSecond_), 0.0F, 8.0F);
			floats_[fullKey] = scrollTilesPerSecond_;
		} else if (section == "Haze" && key == "fPuffScroll") {
			puffScroll_ = std::clamp(ParseFloat(value, puffScroll_), 0.0F, 2.0F);
			floats_[fullKey] = puffScroll_;
		} else if (section == "Haze" && key == "fPuffVariance") {
			puffVariance_ = std::clamp(ParseFloat(value, puffVariance_), 0.0F, 1.0F);
			floats_[fullKey] = puffVariance_;
		} else if (section == "Haze" && key == "fPulseDecaySeconds") {
			pulseDecaySeconds_ = std::clamp(ParseFloat(value, pulseDecaySeconds_), 0.02F, 3.0F);
			floats_[fullKey] = pulseDecaySeconds_;
		} else if (section == "Heat" && key == "fHeatPerShot") {
			heatPerShot_ = std::clamp(ParseFloat(value, heatPerShot_), 0.001F, 1.0F);
			floats_[fullKey] = heatPerShot_;
		} else if (section == "Heat" && key == "fMinHeatToShow") {
			minHeatToShow_ = std::clamp(ParseFloat(value, minHeatToShow_), 0.0F, 1.0F);
			floats_[fullKey] = minHeatToShow_;
		} else if (section == "Heat" && key == "fMaxIntensity") {
			maxIntensity_ = std::clamp(ParseFloat(value, maxIntensity_), 0.0F, 1.0F);
			floats_[fullKey] = maxIntensity_;
		} else if (section == "Heat" && key == "fFadeInSeconds") {
			fadeInSeconds_ = std::clamp(ParseFloat(value, fadeInSeconds_), 0.05F, 30.0F);
			floats_[fullKey] = fadeInSeconds_;
		} else if (section == "Heat" && key == "fFadeOutSeconds") {
			fadeOutSeconds_ = std::clamp(ParseFloat(value, fadeOutSeconds_), 0.05F, 30.0F);
			floats_[fullKey] = fadeOutSeconds_;
		} else if (section == "Heat" && key == "fEffectDurationSeconds") {
			effectDurationSeconds_ = std::clamp(ParseFloat(value, effectDurationSeconds_), 0.0F, 120.0F);
			floats_[fullKey] = effectDurationSeconds_;
		} else if (section == "Heat" && key == "fMinFadeOutSeconds") {
			minFadeOutSeconds_ = std::clamp(ParseFloat(value, minFadeOutSeconds_), 0.1F, 120.0F);
			floats_[fullKey] = minFadeOutSeconds_;
		} else if (section == "Heat" && key == "fMaxFadeOutSeconds") {
			maxFadeOutSeconds_ = std::clamp(ParseFloat(value, maxFadeOutSeconds_), 0.1F, 120.0F);
			floats_[fullKey] = maxFadeOutSeconds_;
		} else if (section == "Heat" && key == "bResetHeatOnWeaponSwitch") {
			resetHeatOnWeaponSwitch_ = ParseBool(value, resetHeatOnWeaponSwitch_);
			floats_[fullKey] = resetHeatOnWeaponSwitch_ ? 1.0F : 0.0F;
		} else if (section == "Debug" && key == "bDebugLogging") {
			debugLogging_ = ParseBool(value, debugLogging_);
			floats_[fullKey] = debugLogging_ ? 1.0F : 0.0F;
		} else if (section == "Weapons" && key == "bAllowAllWeapons") {
			allowAllWeapons_ = ParseBool(value, allowAllWeapons_);
			floats_[fullKey] = allowAllWeapons_ ? 1.0F : 0.0F;
		} else if (section == "Weapons" && key == "sAllowedWeaponFormIDs") {
			allowedWeapons_ = ParseFormIDList(value);
		} else if (section == "Weapons" && key == "bExcludeEnergyWeapons") {
			excludeEnergyWeapons_ = ParseBool(value, excludeEnergyWeapons_);
			floats_[fullKey] = excludeEnergyWeapons_ ? 1.0F : 0.0F;
		} else if (section == "Weapons" && key == "sEnergyAmmoFormIDs") {
			// Replaces the built-in list outright, so a load order with its own energy ammo
			// can be described exactly rather than appended to blindly. An empty value
			// clears it, which disables the filter as surely as the toggle does.
			energyAmmo_ = ParseFormIDList(value);
		} else if (section == "CaliberScaling" && key == "bEnabled") {
			caliberScalingEnabled_ = ParseBool(value, caliberScalingEnabled_);
			floats_[fullKey] = caliberScalingEnabled_ ? 1.0F : 0.0F;
		} else if (section == "CaliberScaling" && key == "fReferenceDamage") {
			caliberReferenceDamage_ = std::clamp(ParseFloat(value, caliberReferenceDamage_), 1.0F, 500.0F);
			floats_[fullKey] = caliberReferenceDamage_;
		} else if (section == "CaliberScaling" && key == "fMinMultiplier") {
			caliberMinMultiplier_ = std::clamp(ParseFloat(value, caliberMinMultiplier_), 0.05F, 10.0F);
			floats_[fullKey] = caliberMinMultiplier_;
		} else if (section == "CaliberScaling" && key == "fMaxMultiplier") {
			caliberMaxMultiplier_ = std::clamp(ParseFloat(value, caliberMaxMultiplier_), 0.05F, 10.0F);
			floats_[fullKey] = caliberMaxMultiplier_;
		} else if (section == "CaliberScaling" && key == "fDamageExponent") {
			caliberDamageExponent_ = std::clamp(ParseFloat(value, caliberDamageExponent_), 0.0F, 2.0F);
			floats_[fullKey] = caliberDamageExponent_;
		}
	}
}

void Config::Finalize()
{
	// The sliders allow fHeatPerShot down to 0.01 and fMinHeatToShow up to 0.6, a
	// combination where heat can never reach the threshold at any fire rate - decay
	// outruns accumulation - so the mod appears broken with no error anywhere. Cap the
	// threshold at what ten shots in quick succession can actually produce, and say so
	// rather than silently overriding the player.
	const auto reachable = std::min(heatPerShot_ * 10.0F, 1.0F);
	if (minHeatToShow_ > reachable) {
		logger::warn("fMinHeatToShow {} is unreachable with fHeatPerShot {} - clamping to {}. "
			"Raise fHeatPerShot or lower the visibility threshold.",
			minHeatToShow_, heatPerShot_, reachable);
		minHeatToShow_ = reachable;
	}

	if (minFadeOutSeconds_ > maxFadeOutSeconds_) {
		std::swap(minFadeOutSeconds_, maxFadeOutSeconds_);
	}
	if (caliberMinMultiplier_ > caliberMaxMultiplier_) {
		std::swap(caliberMinMultiplier_, caliberMaxMultiplier_);
	}

	logger::info("config loaded: ceiling={}, renderEnabled={}, caliberScaling={}, caliberReferenceDamage={}, caliberMultiplier=({}, {}), caliberExponent={}, debugLogging={}, allowAllWeapons={}, allowedWeaponCount={}",
		intensityCeiling_,
		renderEnabled_,
		caliberScalingEnabled_,
		caliberReferenceDamage_,
		caliberMinMultiplier_,
		caliberMaxMultiplier_,
		caliberDamageExponent_,
		debugLogging_,
		allowAllWeapons_,
		allowedWeapons_.size()
	);

	logger::info("art object path: plugin={}, formID={:08X}, preferFireNode={}, hazeRefractionRange=({}, {})",
		artObjectPlugin_,
		artObjectFormID_,
		preferFireNode_,
		refractionMinStrength_,
		refractionMaxStrength_);
}

float Config::GetHeatPerShot(const RE::TESObjectWEAP* a_weapon) const
{
	const auto baseHeat = heatPerShot_;
	if (!caliberScalingEnabled_) {
		return baseHeat;
	}

	RE::BGSEquipIndex equipIndex{};
	equipIndex.index = 0;
	auto* player = RE::PlayerCharacter::GetSingleton();
	auto* ammo = player ? player->GetCurrentAmmo(equipIndex) : nullptr;

	float damageProxy = ammo ? ammo->data.damage : 0.0F;
	if (damageProxy <= 0.0F && a_weapon) {
		damageProxy = static_cast<float>(a_weapon->weaponData.attackDamage);
	}
	damageProxy = std::max(damageProxy, 1.0F);

	const auto rawMultiplier = std::pow(damageProxy / caliberReferenceDamage_, caliberDamageExponent_);
	const auto multiplier = std::clamp(rawMultiplier, caliberMinMultiplier_, caliberMaxMultiplier_);
	const auto result = std::clamp(baseHeat * multiplier, 0.001F, 1.0F);

	if (debugLogging_) {
		const auto* projectile = ammo ? ammo->data.projectile : nullptr;
		logger::info("caliber heat: weapon={:08X}, ammo={:08X}, projectile={:08X}, damageProxy={}, multiplier={}, heatPerShot={}",
			a_weapon ? a_weapon->formID : 0,
			ammo ? ammo->formID : 0,
			projectile ? projectile->formID : 0,
			damageProxy,
			multiplier,
			result);
	}

	return result;
}

bool Config::IsWeaponAllowed(const RE::TESObjectWEAP* a_weapon) const
{
	if (!a_weapon) {
		return false;
	}

	std::shared_lock locker(mutex_);

	// Explicit allowlist entries always pass, so exotic modded weapons that are
	// not typed as guns can still be opted in from the ini.
	if (allowedWeapons_.contains(a_weapon->formID)) {
		return true;
	}

	// Energy weapons are WEAPON_TYPE::kGun exactly like ballistics, so the weapon record
	// cannot distinguish them - the loaded ammo can. Checked after the allowlist so an
	// explicit opt-in still wins, and before allow-all so it actually bites.
	if (excludeEnergyWeapons_ && !energyAmmo_.empty()) {
		RE::BGSEquipIndex equipIndex{};
		equipIndex.index = 0;
		auto* player = RE::PlayerCharacter::GetSingleton();
		const auto* ammo = player ? player->GetCurrentAmmo(equipIndex) : nullptr;
		if (ammo && energyAmmo_.contains(ammo->formID)) {
			if (debugLogging_) {
				logger::info("IsWeaponAllowed: weapon {:08X} excluded, energy ammo {:08X}",
					a_weapon->formID, ammo->formID);
			}
			return false;
		}
	}

	// Allow-all covers every firearm (vanilla or modded) while excluding melee,
	// grenades, and mines, which also route through the weaponFire event path.
	return allowAllWeapons_ && a_weapon->IsGunWeapon();
}

float Config::GetFloat(std::string_view a_section, std::string_view a_key, float a_default) const
{
	const auto fullKey = std::string(a_section) + "." + std::string(a_key);
	std::shared_lock locker(mutex_);
	const auto it = floats_.find(fullKey);
	return it != floats_.end() ? it->second : a_default;
}
