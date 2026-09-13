#pragma once

#include <shared_mutex>

class Config
{
public:
	static Config& Get();

	void Load(std::filesystem::path a_path);
	void ReloadOverrides();
	// Written by Mod Configuration Menu when the player changes a setting. Overlays the
	// base ini, so the mod behaves identically when MCM is not installed.
	static constexpr auto MCM_SETTINGS_PATH = "Data/MCM/Settings/BarrelHeatEffect.ini";
	[[nodiscard]] float IntensityCeiling() const noexcept { return intensityCeiling_; }
	[[nodiscard]] bool RenderEnabled() const noexcept { return renderEnabled_; }
	// Route A (engine-owned art object) settings.
	[[nodiscard]] RE::TESFormID ArtObjectFormID() const noexcept { return artObjectFormID_; }
	[[nodiscard]] std::string ArtObjectPlugin() const
	{
		std::shared_lock locker(mutex_);
		return artObjectPlugin_;
	}
	[[nodiscard]] bool PreferFireNode() const noexcept { return preferFireNode_; }
	[[nodiscard]] float RefractionMinStrength() const noexcept { return refractionMinStrength_; }
	[[nodiscard]] float RefractionMaxStrength() const noexcept { return refractionMaxStrength_; }
	// Exponent applied to strength before it is mapped to refraction. 1.0 is the linear
	// mapping. Below 1.0 the shimmer holds visible further into the cool-down without
	// raising the peak, because refraction falls off linearly with heat but perception of
	// a distortion this weak does not - measured: 0.0068 at the last shot decaying to
	// 0.0029 by ten seconds, which reads as the effect ending well before it is culled.
	[[nodiscard]] float VisibilityCurve() const noexcept { return visibilityCurve_; }
	// Local translation applied to the art object inside the muzzle node's space, so the
	// card can be lifted off the barrel without regenerating the mesh.
	[[nodiscard]] float ArtOffsetUp() const noexcept { return artOffsetUp_; }
	[[nodiscard]] float ArtOffsetForward() const noexcept { return artOffsetForward_; }
	[[nodiscard]] float ArtOffsetSide() const noexcept { return artOffsetSide_; }
	// Card size multipliers, applied in the billboarded (screen-aligned) plane.
	[[nodiscard]] float SizeWidth() const noexcept { return sizeWidth_; }
	[[nodiscard]] float SizeHeight() const noexcept { return sizeHeight_; }
	// Movement smear: offsets the card against the muzzle's recent travel.
	[[nodiscard]] bool SmearEnabled() const noexcept { return smearEnabled_; }
	[[nodiscard]] float SmearGain() const noexcept { return smearGain_; }
	[[nodiscard]] float SmearMaxOffset() const noexcept { return smearMaxOffset_; }
	[[nodiscard]] float SmearSmoothing() const noexcept { return smearSmoothing_; }
	// Experimental per-shot pulse layered on top of the smooth heat curve.
	[[nodiscard]] bool PulseEnabled() const noexcept { return pulseEnabled_; }
	[[nodiscard]] float PulseStrength() const noexcept { return pulseStrength_; }
	[[nodiscard]] float PulseDecaySeconds() const noexcept { return pulseDecaySeconds_; }
	[[nodiscard]] float PuffScale() const noexcept { return puffScale_; }
	[[nodiscard]] float PuffRise() const noexcept { return puffRise_; }
	[[nodiscard]] std::uint32_t PuffMaxOverlap() const noexcept { return puffMaxOverlap_; }
	[[nodiscard]] float PuffVariance() const noexcept { return puffVariance_; }
	// Texture-space rise. Scrolling the pattern inside the card cannot drag the card's
	// edges across the screen the way translating the whole card does.
	[[nodiscard]] bool DriveScroll() const noexcept { return driveScroll_; }
	[[nodiscard]] float ScrollTilesPerSecond() const noexcept { return scrollTilesPerSecond_; }
	[[nodiscard]] float PuffScroll() const noexcept { return puffScroll_; }
	// Heat curve. These used to live only in the generic floats_ map, reached from Papyrus
	// through GetIniFloat(). That path proved unreliable - a whole session's LoadIniConfig
	// calls reported the 1.0/ShotThreshold fallback for fHeatPerShot while the DLL's own
	// GetFloat() for the same key returned the correct value - so they are typed members
	// now and Papyrus reads them through a dedicated native.
	[[nodiscard]] float HeatPerShot() const noexcept { return heatPerShot_; }
	[[nodiscard]] float MinHeatToShow() const noexcept { return minHeatToShow_; }
	[[nodiscard]] float MaxIntensity() const noexcept { return maxIntensity_; }
	[[nodiscard]] float FadeInSeconds() const noexcept { return fadeInSeconds_; }
	[[nodiscard]] float FadeOutSeconds() const noexcept { return fadeOutSeconds_; }
	// Hard cap on how long the shimmer stays visible after the last shot, independent of
	// how long the barrel stays hot. 0 disables it and the cool-down curve governs alone.
	[[nodiscard]] float EffectDurationSeconds() const noexcept { return effectDurationSeconds_; }
	[[nodiscard]] float MinFadeOutSeconds() const noexcept { return minFadeOutSeconds_; }
	[[nodiscard]] float MaxFadeOutSeconds() const noexcept { return maxFadeOutSeconds_; }
	// Whether swapping to a different weapon starts that barrel cold. Heat is a property of
	// the barrel you are holding, so carrying it across a switch is physically wrong.
	[[nodiscard]] bool  ResetHeatOnWeaponSwitch() const noexcept { return resetHeatOnWeaponSwitch_; }
	[[nodiscard]] bool DebugLogging() const noexcept { return debugLogging_; }
	[[nodiscard]] bool IsWeaponAllowed(const RE::TESObjectWEAP* a_weapon) const;
	[[nodiscard]] float GetHeatPerShot(const RE::TESObjectWEAP* a_weapon) const;
	// Energy weapons are ordinary WEAPON_TYPE::kGun forms, so nothing about the weapon
	// record separates them from ballistics. The ammo does: a laser fires a fusion cell.
	// Matching on ammo also covers modded weapons, which overwhelmingly reuse the vanilla
	// energy ammo rather than shipping their own.
	[[nodiscard]] float GetFloat(std::string_view a_section, std::string_view a_key, float a_default) const;

private:
	void ParseFile(std::filesystem::path a_path, bool a_optional);
	std::chrono::steady_clock::time_point lastOverrideLoad_{};
	void Finalize();

	float intensityCeiling_{ 1.0F };
	bool renderEnabled_{ true };
	RE::TESFormID artObjectFormID_{ 0x01000802 };
	std::string artObjectPlugin_{ "BarrelHeatEffect.esp" };
	bool preferFireNode_{ true };
	float refractionMinStrength_{ 0.0F };
	float refractionMaxStrength_{ 0.04F };
	float visibilityCurve_{ 1.0F };
	float artOffsetUp_{ 1.0F };
	float artOffsetForward_{ 0.0F };
	float artOffsetSide_{ 0.0F };
	float sizeWidth_{ 0.8F };
	float sizeHeight_{ 0.5F };
	bool smearEnabled_{ true };
	float smearGain_{ 0.015F };
	float smearMaxOffset_{ 6.0F };
	float smearSmoothing_{ 0.10F };
	bool pulseEnabled_{ true };
	float pulseStrength_{ 0.01F };
	float pulseDecaySeconds_{ 0.30F };
	float puffScale_{ 0.1F };
	float puffRise_{ 0.5F };
	std::uint32_t puffMaxOverlap_{ 6 };
	float puffVariance_{ 0.35F };
	bool driveScroll_{ true };
	float scrollTilesPerSecond_{ 0.7F };
	float puffScroll_{ 0.15F };
	float heatPerShot_{ 0.07F };
	float minHeatToShow_{ 0.05F };
	float maxIntensity_{ 0.90F };
	float fadeInSeconds_{ 3.0F };
	float fadeOutSeconds_{ 2.5F };
	float effectDurationSeconds_{ 0.0F };
	float minFadeOutSeconds_{ 8.0F };
	float maxFadeOutSeconds_{ 20.0F };
	bool  resetHeatOnWeaponSwitch_{ true };
	bool debugLogging_{ false };
	bool allowAllWeapons_{ true };
	bool excludeEnergyWeapons_{ true };
	bool caliberScalingEnabled_{ true };
	float caliberReferenceDamage_{ 30.0F };
	float caliberMinMultiplier_{ 0.55F };
	float caliberMaxMultiplier_{ 1.80F };
	float caliberDamageExponent_{ 0.50F };
	std::unordered_set<RE::TESFormID> allowedWeapons_;
	// Defaults are the vanilla energy ammo records, read out of Fallout4.esm with
	// tools\dump_ammo_records.py rather than transcribed from memory - a wrong FormID here
	// fails silently in both directions.
	std::unordered_set<RE::TESFormID> energyAmmo_{
		0x000C1897,  // AmmoFusionCell        - laser weapons
		0x000AB4FE,  // AmmoFusionCellEyebot
		0x001262F2,  // AmmoFusionCellLtBlue
		0x0001DBB7,  // AmmoPlasmaCartridge   - plasma weapons
		0x00075FE4,  // AmmoFusionCore        - Gatling laser
		0x001BBFCA,  // AmmoFusionCoreNoSteal
		0x00178D66,  // AmmoFusionCoreMeltdown
		0x000865EA,  // AmmoFusionCoreKnightMeltdown
		0x0018ABE2,  // AmmoCryoCell          - Cryolator
		0x000DF279,  // AmmoGammaCell         - Gamma gun
		0x001025AA,  // AmmoAlienBlaster      - Alien blaster
		0x0018ABDF,  // Ammo2mmEC             - Gauss rifle
	};
	std::unordered_map<std::string, float> floats_;

	// Config is written from the game thread (AddHeat -> ReloadOverrides, Load on game
	// load) and from the Papyrus VM thread (GetHeatSetting -> ReloadOverrides), while being
	// read from the VM thread on every shot (IsWeaponAllowed, GetHeatPerShot, GetIniFloat)
	// and from the game thread by every tick. Before this lock there was no synchronisation
	// at all, and ParseFile rewrites floats_ - an unordered_map with 72 insertion sites -
	// plus two FormID sets and five std::strings. Concurrent insert-and-rehash while
	// another thread traverses is undefined behaviour, and handing out a const std::string&
	// let a reader hold a buffer that a reload could free underneath it.
	//
	// Scope: exclusive around parsing, shared around the container and string accessors.
	// The scalar float/bool/uint32 accessors stay lock-free by design. They are aligned POD
	// loads that cannot tear on x86-64, so the worst case is one frame reading the previous
	// value of a setting the player just changed - and locking ~20 of them per tick at
	// 125 Hz would cost more than it buys.
	mutable std::shared_mutex mutex_;
};
