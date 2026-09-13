#include "HazeManager.h"

#include "Config.h"

#include <thread>

namespace
{
	constexpr std::uint32_t MAX_TREE_DUMP_NODES = 160;

	std::string_view GetObjectName(const RE::NiAVObject* a_object)
	{
		if (!a_object) {
			return "<null>"sv;
		}

		const auto name = a_object->name.c_str();
		if (!name || !*name) {
			return "<unnamed>"sv;
		}

		return name;
	}

	void DumpObjectTree(RE::NiAVObject* a_object, std::uint32_t a_depth, std::uint32_t& a_count)
	{
		if (!a_object || a_count >= MAX_TREE_DUMP_NODES) {
			return;
		}

		const auto* typeName = "NiAVObject";
		if (netimmerse_cast<RE::NiNode*>(a_object)) {
			typeName = "NiNode";
		} else if (netimmerse_cast<RE::BSGeometry*>(a_object)) {
			typeName = "BSGeometry";
		}

		logger::info("AttachHaze tree: {}{} [{}]",
			std::string(static_cast<std::size_t>(a_depth) * 2, ' '),
			GetObjectName(a_object),
			typeName);
		++a_count;

		if (auto* node = netimmerse_cast<RE::NiNode*>(a_object)) {
			auto& children = node->children;
			for (RE::NiTObjectArray<RE::NiPointer<RE::NiAVObject>>::size_type i = 0; i < children.size(); ++i) {
				DumpObjectTree(children[i].get(), a_depth + 1, a_count);
				if (a_count >= MAX_TREE_DUMP_NODES) {
					logger::info("AttachHaze tree: ... truncated after {} node(s)", MAX_TREE_DUMP_NODES);
					return;
				}
			}
		}
	}

	void ForEachGeometry(RE::NiAVObject* a_object, const std::function<void(RE::BSGeometry&)>& a_callback)
	{
		if (!a_object) {
			return;
		}

		if (auto* geometry = netimmerse_cast<RE::BSGeometry*>(a_object)) {
			a_callback(*geometry);
		}

		if (auto* node = netimmerse_cast<RE::NiNode*>(a_object)) {
			auto& children = node->children;
			for (RE::NiTObjectArray<RE::NiPointer<RE::NiAVObject>>::size_type i = 0; i < children.size(); ++i) {
				ForEachGeometry(children[i].get(), a_callback);
			}
		}
	}
}

HazeManager& HazeManager::Get()
{
	static HazeManager manager;
	return manager;
}

RE::BGSArtObject* HazeManager::LookupArtObject() const
{
	const auto& config = Config::Get();
	const auto formID = config.ArtObjectFormID();
	if (!formID) {
		return nullptr;
	}

	if (auto* art = RE::TESForm::GetFormByID<RE::BGSArtObject>(formID)) {
		return art;
	}

	auto* dataHandler = RE::TESDataHandler::GetSingleton();
	if (!dataHandler) {
		return nullptr;
	}

	const auto resolved = dataHandler->LookupFormID(formID & 0x00FFFFFF, config.ArtObjectPlugin());
	if (!resolved) {
		return nullptr;
	}

	if (config.DebugLogging()) {
		logger::info("AttachHaze: resolved art object {:06X} in {} to {:08X}",
			formID & 0x00FFFFFF, config.ArtObjectPlugin(), resolved);
	}

	return RE::TESForm::GetFormByID<RE::BGSArtObject>(resolved);
}

// The engine already resolves a fire node for whatever weapon is equipped, including its
// attached muzzle mods, so reading it covers vanilla and modded guns with no per-weapon
// patching. GetCurrentFireLocation does NOT use this field - it interpolates the
// fireLocations stance grid instead - so whether fireNode is the first- or third-person
// instance still has to be settled in-game. That is what the attach-source logging is for.
RE::NiAVObject* HazeManager::FindFireNode(RE::Actor* a_actor) const
{
	if (!a_actor) {
		return nullptr;
	}

	auto* process = a_actor->currentProcess;
	if (!process || !process->middleHigh) {
		return nullptr;
	}

	for (auto& equipped : process->middleHigh->equippedItems) {
		auto* object = equipped.item.object;
		if (!object || !object->IsWeapon()) {
			continue;
		}

		auto* data = equipped.data.get();
		if (!data) {
			continue;
		}

		auto* weaponData = static_cast<RE::EquippedWeaponData*>(data);
		if (weaponData->fireNode) {
			return weaponData->fireNode;
		}
	}

	return nullptr;
}

RE::NiAVObject* HazeManager::FindMuzzleByName(RE::NiAVObject* a_root) const
{
	if (!a_root) {
		return nullptr;
	}

	const auto name = GetObjectName(a_root);
	if (name.starts_with("Muz"sv) ||
		name.find("Muzzle"sv) != std::string_view::npos ||
		name.find("muzzle"sv) != std::string_view::npos) {
		return a_root;
	}

	if (auto* node = netimmerse_cast<RE::NiNode*>(a_root)) {
		auto& children = node->children;
		for (RE::NiTObjectArray<RE::NiPointer<RE::NiAVObject>>::size_type i = 0; i < children.size(); ++i) {
			if (auto* result = FindMuzzleByName(children[i].get())) {
				return result;
			}
		}
	}

	return nullptr;
}

RE::NiAVObject* HazeManager::ResolveAttachNode(RE::TESObjectREFR* a_ref, std::string& a_source) const
{
	const auto& config = Config::Get();

	if (config.PreferFireNode()) {
		if (auto* fireNode = FindFireNode(a_ref->As<RE::Actor>())) {
			a_source = "EquippedWeaponData::fireNode";
			return fireNode;
		}
		if (config.DebugLogging()) {
			logger::info("AttachHaze: no fireNode on the equipped weapon; falling back to name search");
		}
	}

	auto* firstPerson = a_ref->Get3D(true);
	if (auto* named = FindMuzzleByName(firstPerson)) {
		a_source = "first-person muzzle-like node";
		return named;
	}

	auto* thirdPerson = a_ref->Get3D(false);
	if (auto* named = FindMuzzleByName(thirdPerson)) {
		a_source = "third-person muzzle-like node";
		return named;
	}

	if (config.DebugLogging()) {
		if (firstPerson) {
			logger::info("AttachHaze: first-person root {}", GetObjectName(firstPerson));
			std::uint32_t dumped = 0;
			DumpObjectTree(firstPerson, 0, dumped);
		} else {
			logger::info("AttachHaze: no first-person root");
		}
	}

	if (firstPerson) {
		a_source = "first-person root (no muzzle node found)";
		return firstPerson;
	}

	a_source = "none";
	return nullptr;
}

bool HazeManager::Attach(RE::TESObjectREFR* a_ref)
{
	if (!a_ref) {
		logger::warn("AttachHaze: rejected null reference");
		return false;
	}

	// Pick up any MCM edits before the cycle starts, so tuning applies on the next burst
	// instead of waiting for a save reload.
	Config::Get().ReloadOverrides();

	const auto& config = Config::Get();
	std::scoped_lock locker(lock_);
	DetachLocked(a_ref->formID);

	auto* art = LookupArtObject();
	if (!art) {
		logger::warn("AttachHaze: art object {:08X} not found in {}",
			config.ArtObjectFormID(), config.ArtObjectPlugin());
		return false;
	}

	std::string source;
	auto* attachNode = ResolveAttachNode(a_ref, source);
	if (!attachNode) {
		logger::warn("AttachHaze: no attach node available");
		return false;
	}

	logger::info("AttachHaze: attaching to '{}' via {}", GetObjectName(attachNode), source);

	// -1.0f goes straight into BSTempEffect::lifetime, which makes the effect persistent
	// until we end it. a_attachToCamera must be false or a_3D is discarded.
	auto* effect = a_ref->ApplyArtObject(art, -1.0F, nullptr, false, false, attachNode, false);
	if (!effect) {
		// Registration destroys the effect when Init() fails, so null is a real failure.
		logger::warn("AttachHaze: ApplyArtObject returned null (Init failed)");
		return false;
	}

	// Named assignment rather than an aggregate initialiser: ActiveHaze now carries the
	// heat model too, and positional init silently binds to whatever field happens to sit
	// at that index once a member is inserted above it.
	ActiveHaze haze{};
	haze.effect = RE::NiPointer<RE::ModelReferenceEffect>{ effect };
	haze.attachNode = RE::NiPointer<RE::NiAVObject>{ attachNode };
	haze.attachNodeName = std::string(GetObjectName(attachNode));
	haze.attachSource = source;
	active_.insert_or_assign(a_ref->formID, std::move(haze));

	logger::info("AttachHaze: art object applied to form {:08X}", a_ref->formID);
	return true;
}

// Swapping weapons leaves the art object parented to the previous weapon's muzzle node.
// That node still exists - we hold a reference to it - but it is no longer part of the
// rendered first-person weapon, so the effect silently stops being visible while every log
// line still reads healthy. Ending the old effect and re-applying to the new node is the
// only way back, because ApplyArtObject binds the attach root once at creation.
bool HazeManager::Reattach(ActiveHaze& a_haze, RE::TESObjectREFR* a_ref, RE::NiAVObject* a_node) const
{
	auto* art = LookupArtObject();
	if (!art || !a_node) {
		return false;
	}

	if (auto* effect = a_haze.effect.get()) {
		ApplyRefraction(effect->artObject3D.get(), 0.0F);
		effect->finished = true;
		effect->lifetime = 0.0F;
	}

	auto* effect = a_ref->ApplyArtObject(art, -1.0F, nullptr, false, false, a_node, false);
	if (!effect) {
		logger::warn("Reattach: ApplyArtObject returned null for the new muzzle node");
		return false;
	}

	a_haze.effect = RE::NiPointer<RE::ModelReferenceEffect>{ effect };
	a_haze.attachNode = RE::NiPointer<RE::NiAVObject>{ a_node };
	a_haze.attachNodeName = std::string(GetObjectName(a_node));
	a_haze.warnedMissingArt3D = false;
	a_haze.loggedArt3D = false;
	// The smear samples motion of a specific node; carrying the old sample across would
	// register the switch itself as one enormous jump.
	a_haze.hasSample = false;
	a_haze.smear = RE::NiPoint3{};
	return true;
}

// Scrolls the pattern INSIDE the card rather than moving the card. Translating the whole
// card upward drags its edges across the screen, which is what produced the horizontal
// line: the card's silhouette is hard, so its boundary is visible as it travels. Advancing
// the texture V offset makes the heat rise within a stationary card, and no edge moves.
//
// This takes ownership of V from the NIF's own controller. Both write the material's
// texCoordOffset, so whichever runs last in a frame wins; owning it here makes the result
// deterministic and lets the scroll rate follow config.
void HazeManager::ApplyScroll(ActiveHaze& a_haze, RE::NiAVObject* a_root, float a_puffScroll) const
{
	const auto& config = Config::Get();
	if (!config.DriveScroll() || !a_root) {
		return;
	}

	const auto now = std::chrono::steady_clock::now();
	if (a_haze.hasScrollSample) {
		const auto delta = std::chrono::duration<float>(now - a_haze.lastScrollSample).count();
		if (delta > 0.0F && delta < 0.5F) {
			a_haze.scroll += config.ScrollTilesPerSecond() * delta;
		}
	}
	a_haze.lastScrollSample = now;
	a_haze.hasScrollSample = true;

	// Keep it bounded; the texture wraps, so only the fractional part matters.
	a_haze.scroll = std::fmod(a_haze.scroll, 1.0F);

	const auto offset = -(a_haze.scroll + a_puffScroll);
	ForEachGeometry(a_root, [offset](RE::BSGeometry& a_geometry) {
		for (auto& property : a_geometry.properties) {
			auto* shader = netimmerse_cast<RE::BSShaderProperty*>(property.get());
			if (!shader || !shader->material) {
				continue;
			}
			if (shader->material->GetType() != RE::BSShaderMaterial::Type::kLighting) {
				continue;
			}
			shader->material->texCoordOffset[0].y = offset;
			shader->material->texCoordOffset[1].y = offset;
		}
	});
}

void HazeManager::Detach(RE::TESObjectREFR* a_ref)
{
	if (!a_ref) {
		return;
	}

	std::scoped_lock locker(lock_);
	DetachLocked(a_ref->formID);
}

void HazeManager::DetachLocked(RE::TESFormID a_formID)
{
	const auto it = active_.find(a_formID);
	if (it == active_.end()) {
		return;
	}

	// The effect is owned by ProcessLists. Rather than unhooking it by hand, mark it
	// finished and let the temp-effect update reap it on the next tick.
	if (auto* effect = it->second.effect.get()) {
		ApplyRefraction(effect->artObject3D.get(), 0.0F);
		effect->finished = true;
		effect->lifetime = 0.0F;
	}

	active_.erase(it);
	if (Config::Get().DebugLogging()) {
		logger::info("DetachHaze: released art object for form {:08X}", a_formID);
	}
}

void HazeManager::ApplyRefraction(RE::NiAVObject* a_root, float a_strength) const
{
	if (!a_root) {
		return;
	}

	ForEachGeometry(a_root, [a_strength](RE::BSGeometry& a_geometry) {
		for (auto& property : a_geometry.properties) {
			auto* shader = netimmerse_cast<RE::BSShaderProperty*>(property.get());
			if (!shader || !shader->material) {
				continue;
			}
			if (shader->material->GetType() != RE::BSShaderMaterial::Type::kLighting) {
				continue;
			}

			// refractionPower is read into the constant buffer every draw, which is why
			// this is the lever that actually fades Fallout 4 refraction. Object alpha
			// and fadeAmount do not touch it.
			static_cast<RE::BSLightingShaderMaterialBase*>(shader->material)->refractionPower = a_strength;
		}
	});
}

void HazeManager::SetStrength(RE::TESObjectREFR* a_ref, float a_strength)
{
	if (!a_ref) {
		return;
	}

	std::scoped_lock locker(lock_);
	const auto it = active_.find(a_ref->formID);
	if (it == active_.end()) {
		return;
	}

	SetStrengthLocked(it->second, a_ref, a_strength);
}

void HazeManager::SetStrengthLocked(ActiveHaze& a_haze, RE::TESObjectREFR* a_ref, float a_strength)
{
	const auto& config = Config::Get();
	auto* effect = a_haze.effect.get();
	if (!effect) {
		return;
	}

	// Weapon switches do not end the heat cycle, so without this the art object stays on
	// the old weapon's muzzle node for the rest of the cycle - and if you keep firing, heat
	// never reaches zero, so the cycle never ends and it never recovers.
	if (config.PreferFireNode()) {
		if (auto* current = FindFireNode(a_ref->As<RE::Actor>())) {
			if (current != a_haze.attachNode.get()) {
				const auto previous = a_haze.attachNodeName;
				if (Reattach(a_haze, a_ref, current)) {
					logger::info("SetHazeStrength: muzzle node changed ('{}' -> '{}'), art object re-applied",
						previous, a_haze.attachNodeName);
					effect = a_haze.effect.get();
					if (!effect) {
						return;
					}
				}
			}
		}
	}

	auto* art3D = effect->artObject3D.get();
	if (!art3D) {
		// BGSArtObjectCloneTask populates this asynchronously, so a few empty frames
		// right after attach are expected rather than an error.
		if (config.DebugLogging() && !a_haze.warnedMissingArt3D) {
			logger::info("SetHazeStrength: art object 3D not ready yet for form {:08X}", a_ref->formID);
			a_haze.warnedMissingArt3D = true;
		}
		return;
	}

	if (config.DebugLogging() && !a_haze.loggedArt3D) {
		logger::info("SetHazeStrength: art object 3D ready, root={}", GetObjectName(art3D));
		std::uint32_t dumped = 0;
		DumpObjectTree(art3D, 0, dumped);
		a_haze.loggedArt3D = true;
	}

	// Lift the card off the barrel so it reads as heat rising rather than a patch wrapped
	// around the muzzle. The muzzle node's local axes are Y forward along the barrel and
	// Z up, and the engine rewrites this transform as the weapon moves, so it is reapplied
	// every tick rather than once at attach.
	const auto clampedHeat = std::clamp(a_strength, 0.0F, config.IntensityCeiling());
	const auto puff = UpdatePuffs(a_haze, clampedHeat);

	ApplySize(art3D, puff.scale);

	const auto smear = UpdateSmear(a_haze);
	art3D->local.translate.x = config.ArtOffsetSide() + smear.x;
	art3D->local.translate.y = config.ArtOffsetForward() + smear.y;
	art3D->local.translate.z = config.ArtOffsetUp() + smear.z + puff.rise;

	const auto clamped = clampedHeat;
	// Shape the strength before mapping it to refraction. The cool-down is long - measured
	// at 13.4s, matching the configured curve exactly - but refraction falls off linearly
	// with heat, so the shimmer stops being perceptible well before the cycle ends. A
	// curve below 1.0 keeps it readable for more of that time without raising the peak.
	const auto shaped = (config.VisibilityCurve() == 1.0F) ?
		clamped :
		std::pow(clamped, config.VisibilityCurve());
	const auto refraction =
		std::lerp(config.RefractionMinStrength(), config.RefractionMaxStrength(), shaped) +
		puff.refraction;

	// Nothing below contributes anything the player can see once refraction reaches zero,
	// and drawing it is not free: bRenderEnabled=0 additionally forces this path so the
	// mod can be run with every system live but nothing drawn.
	const auto shouldDraw = config.RenderEnabled() && refraction > 0.0001F;
	if (a_haze.culled == shouldDraw) {
		a_haze.culled = !shouldDraw;
		art3D->SetAppCulled(a_haze.culled);
		if (config.DebugLogging()) {
			logger::info("SetHazeStrength: form={:08X} card {}", a_ref->formID,
				a_haze.culled ? "culled" : "shown");
		}
	}

	if (!shouldDraw) {
		ApplyRefraction(art3D, 0.0F);
		return;
	}

	ApplyScroll(a_haze, art3D, puff.scroll);
	ApplyRefraction(art3D, refraction);

	const auto logNow = std::chrono::steady_clock::now();
	const auto sinceLog = std::chrono::duration<float>(logNow - a_haze.lastDebugLog).count();
	if (config.DebugLogging() && sinceLog >= 0.25F) {
		a_haze.lastDebugLog = logNow;
		logger::info("SetHazeStrength: form={:08X}, heat={}, strength={}, shaped={}, refraction={}, puffs={}, puffRefr={}, puffScale={}, puffScroll={}, scroll={}, node={} ({})",
			a_ref->formID, a_haze.heat, clamped, shaped, refraction, a_haze.puffs.size(),
			puff.refraction, puff.scale, puff.scroll, a_haze.scroll,
			a_haze.attachNodeName, a_haze.attachSource);
	}
}

// One step of the heat curve, ported verbatim from GunHeatController.psc. Returns false
// once the cycle has fully cooled, which is what tells Tick() to detach.
bool HazeManager::AdvanceHeat(ActiveHaze& a_haze, float a_elapsed) const
{
	const auto& config = Config::Get();

	// Hotter barrels stay hot longer.
	const auto peak = std::clamp(a_haze.peakHeat, 0.0F, 1.0F);
	const auto fadeOutSeconds = std::max(
		config.MinFadeOutSeconds() +
			((config.MaxFadeOutSeconds() - config.MinFadeOutSeconds()) * peak),
		0.01F);

	a_haze.heat = std::max(a_haze.heat - (a_elapsed / fadeOutSeconds), 0.0F);

	auto target = a_haze.heat;
	if (target < config.MinHeatToShow()) {
		target = 0.0F;
	}

	// Independent cap on how long the shimmer may stay up after the last shot. Heat keeps
	// decaying on its own curve regardless, so firing again inside the cool-down resumes
	// from the accumulated heat rather than starting cold.
	const auto duration = config.EffectDurationSeconds();
	if (duration > 0.0F && a_haze.hasShot) {
		const auto since =
			std::chrono::duration<float>(std::chrono::steady_clock::now() - a_haze.lastShot).count();
		if (since > duration) {
			target = 0.0F;
		}
	}

	// Heat decay governs how long the barrel stays hot; the visual ramp governs how fast
	// the shimmer itself appears and disappears.
	const auto rampSeconds = std::max(
		(target > a_haze.visible) ? config.FadeInSeconds() : config.FadeOutSeconds(),
		0.01F);
	const auto maxDelta = a_elapsed / rampSeconds;

	if (a_haze.visible < target) {
		a_haze.visible = std::min(a_haze.visible + maxDelta, target);
	} else if (a_haze.visible > target) {
		a_haze.visible = std::max(a_haze.visible - maxDelta, target);
	}
	a_haze.visible = std::clamp(a_haze.visible, 0.0F, 1.0F);

	return a_haze.heat > 0.0F || a_haze.visible > 0.0F;
}

void HazeManager::AddHeat(RE::TESObjectREFR* a_ref, float a_amount, RE::TESFormID a_weaponID)
{
	if (!a_ref) {
		return;
	}

	// Attach() used to be the place MCM edits were picked up, but attachments are now
	// parked and reused, so it barely runs. ReloadOverrides throttles itself to once a
	// second, so calling it per shot costs at most one file read per second.
	Config::Get().ReloadOverrides();

	const auto& config = Config::Get();

	bool needAttach = false;
	{
		std::scoped_lock locker(lock_);
		needAttach = !active_.contains(a_ref->formID);
	}

	// Attaching on the first shot rather than at a heat threshold is safe because the card
	// is authored with refractionStrength 0 and the visual ramp still gates on
	// fMinHeatToShow - nothing renders until the heat curve says so. It also means the
	// async BGSArtObjectCloneTask has the whole warm-up to finish in.
	if (needAttach && !Attach(a_ref)) {
		return;
	}

	{
		std::scoped_lock locker(lock_);
		const auto it = active_.find(a_ref->formID);
		if (it == active_.end()) {
			return;
		}

		auto& haze = it->second;
		// Only pulse into a cycle that is already showing. The shot that starts a cycle must
		// not pulse, or the effect punches in at the exact moment it should be ramping up
		// from nothing.
		const auto wasVisible = haze.visible > 0.0F;

		// A different barrel starts cold. visible is deliberately left alone so any shimmer
		// still up fades out on the normal ramp rather than vanishing on the frame of the
		// switch; it simply now ramps toward the new weapon's much lower target.
		if (config.ResetHeatOnWeaponSwitch() && haze.weaponID != 0 && haze.weaponID != a_weaponID) {
			logger::info("AddHeat: weapon changed ({:08X} -> {:08X}); resetting heat from {}",
				haze.weaponID, a_weaponID, haze.heat);
			haze.heat = 0.0F;
			haze.peakHeat = 0.0F;
			haze.puffs.clear();
		}
		haze.weaponID = a_weaponID;

		if (haze.idle) {
			// Waking a parked attachment. Drop the stale timestamp or the first tick would
			// bill the whole idle period as one decay step.
			haze.idle = false;
			haze.hasHeatTick = false;
			haze.hasSample = false;
			haze.hasScrollSample = false;
		}

		haze.heat = std::min(haze.heat + a_amount, 1.0F);
		haze.peakHeat = std::max(haze.peakHeat, haze.heat);
		haze.lastShot = std::chrono::steady_clock::now();
		haze.hasShot = true;

		if (wasVisible) {
			PulseLocked(haze);
		}

		if (config.DebugLogging()) {
			logger::info("AddHeat: form={:08X}, shot={}, heat={}, visible={}, peak={}",
				a_ref->formID, a_amount, haze.heat, haze.visible, haze.peakHeat);
		}
	}

	hasWork_.store(true, std::memory_order_relaxed);
}

void HazeManager::StartPacer()
{
	if (pacerStarted_.exchange(true)) {
		return;
	}

	const auto* tasks = F4SE::GetTaskInterface();
	if (!tasks) {
		logger::warn("heat pacer not started: F4SE task interface unavailable");
		pacerStarted_.store(false);
		return;
	}

	// One permanent thread, so there is no start/stop race to get wrong. It posts at most
	// one Tick per interval; when nothing is being driven it polls an atomic at 10 Hz and
	// touches neither the lock nor the game thread.
	std::thread([tasks]() {
		auto& self = HazeManager::Get();
		for (;;) {
			if (self.hasWork_.load(std::memory_order_relaxed)) {
				tasks->AddTask([]() { HazeManager::Get().Tick(); });
				std::this_thread::sleep_for(std::chrono::milliseconds(8));
			} else {
				std::this_thread::sleep_for(std::chrono::milliseconds(100));
			}
		}
	}).detach();

	logger::info("heat pacer started (125 Hz while driving, 10 Hz idle)");
}

void HazeManager::Tick()
{
	const auto& config = Config::Get();
	const auto  now = std::chrono::steady_clock::now();

	bool more = false;

	{
		std::scoped_lock locker(lock_);

		for (auto& [formID, haze] : active_) {
			if (haze.idle) {
				continue;
			}

			auto elapsed = 0.0F;
			if (haze.hasHeatTick) {
				elapsed = std::chrono::duration<float>(now - haze.lastHeatTick).count();
			}
			haze.lastHeatTick = now;
			haze.hasHeatTick = true;

			if (elapsed <= 0.0F) {
				continue;
			}

			// Loading screens, menus and pauses would otherwise cash out as one enormous
			// decay step and wipe the cycle instantly - which is exactly how the old
			// timer-driven build died, with a single elapsed=17.0 update.
			elapsed = std::min(elapsed, 0.25F);

			const auto alive = AdvanceHeat(haze, elapsed);

			if (auto* ref = RE::TESForm::GetFormByID<RE::TESObjectREFR>(formID)) {
				SetStrengthLocked(haze, ref, haze.visible * config.MaxIntensity());
			}

			if (!alive) {
				// Park rather than detach. The attachment costs nothing at refraction 0 and
				// keeping it means the next shot reuses a clone that is already resident
				// instead of paying for a fresh ApplyArtObject.
				haze.idle = true;
				if (auto* effect = haze.effect.get()) {
					if (auto* art3D = effect->artObject3D.get()) {
						ApplyRefraction(art3D, 0.0F);
						if (!haze.culled) {
							haze.culled = true;
							art3D->SetAppCulled(true);
						}
					}
				}
				if (config.DebugLogging()) {
					logger::info("Tick: form {:08X} cooled; parking attachment", formID);
				}
			} else {
				more = true;
			}
		}
	}

	hasWork_.store(more, std::memory_order_relaxed);

	// How often is this actually running, and how long does it take? Guessing at that is
	// what cost the last two builds.
	const auto spent = static_cast<std::uint64_t>(
		std::chrono::duration_cast<std::chrono::microseconds>(
			std::chrono::steady_clock::now() - now).count());
	tickMicros_.fetch_add(spent, std::memory_order_relaxed);
	auto highest = tickMaxMicros_.load(std::memory_order_relaxed);
	while (spent > highest &&
		!tickMaxMicros_.compare_exchange_weak(highest, spent, std::memory_order_relaxed)) {
	}

	const auto ticks = tickCount_.fetch_add(1, std::memory_order_relaxed) + 1;
	static std::chrono::steady_clock::time_point lastReport{};
	if (std::chrono::duration<float>(now - lastReport).count() >= 1.0F) {
		lastReport = now;
		if (config.DebugLogging()) {
			logger::info("Tick rate: {} ticks/sec, {} us total, {} us worst",
				ticks, tickMicros_.load(std::memory_order_relaxed),
				tickMaxMicros_.load(std::memory_order_relaxed));
		}
		tickCount_.store(0, std::memory_order_relaxed);
		tickMicros_.store(0, std::memory_order_relaxed);
		tickMaxMicros_.store(0, std::memory_order_relaxed);
	}
}

// Push the card back along whatever direction the muzzle just travelled, so swinging the
// weapon or walking leaves the heat trailing behind instead of moving perfectly rigidly
// with the barrel. Sampled at the heat tick rate (~20 Hz) and smoothed, since that is too
// coarse to use raw.
RE::NiPoint3 HazeManager::UpdateSmear(ActiveHaze& a_haze) const
{
	const auto& config = Config::Get();
	auto* node = a_haze.attachNode.get();
	if (!config.SmearEnabled() || !node) {
		a_haze.smear = RE::NiPoint3{};
		a_haze.hasSample = false;
		return a_haze.smear;
	}

	const auto now = std::chrono::steady_clock::now();
	const auto worldPos = node->world.translate;

	RE::NiPoint3 target{};
	if (a_haze.hasSample) {
		const auto delta = std::chrono::duration<float>(now - a_haze.lastSample).count();
		// Ignore absurd gaps: loading screens, menus and pauses would otherwise register
		// as one enormous jump.
		if (delta > 0.001F && delta < 0.5F) {
			const RE::NiPoint3 velocity{
				(worldPos.x - a_haze.lastNodeWorld.x) / delta,
				(worldPos.y - a_haze.lastNodeWorld.y) / delta,
				(worldPos.z - a_haze.lastNodeWorld.z) / delta
			};

			// local.translate lives in the muzzle node's space, so the world-space
			// velocity has to be rotated into that frame before it can be used as one.
			const auto localVelocity = node->world.rotate.Transpose() * velocity;
			target = localVelocity * -config.SmearGain();

			const auto length = std::sqrt(
				(target.x * target.x) + (target.y * target.y) + (target.z * target.z));
			const auto limit = config.SmearMaxOffset();
			if (length > limit && length > 0.0F) {
				const auto scale = limit / length;
				target = target * scale;
			}
		}
	}

	const auto delta = a_haze.hasSample ?
		std::chrono::duration<float>(now - a_haze.lastSample).count() : 0.0F;
	const auto tau = std::max(config.SmearSmoothing(), 0.001F);
	const auto blend = std::clamp(1.0F - std::exp(-std::max(delta, 0.0F) / tau), 0.0F, 1.0F);
	a_haze.smear.x += (target.x - a_haze.smear.x) * blend;
	a_haze.smear.y += (target.y - a_haze.smear.y) * blend;
	a_haze.smear.z += (target.z - a_haze.smear.z) * blend;

	a_haze.lastNodeWorld = worldPos;
	a_haze.lastSample = now;
	a_haze.hasSample = true;
	return a_haze.smear;
}

void HazeManager::ApplySize(RE::NiAVObject* a_root, float a_puffScale) const
{
	const auto& config = Config::Get();
	// Puffs billow upward more than sideways, so the vertical axis takes the full
	// expansion and the horizontal axis only part of it.
	const auto width = config.SizeWidth() * (1.0F + (a_puffScale * 0.6F));
	const auto height = config.SizeHeight() * (1.0F + a_puffScale);

	// NiTransform::scale is a single float, so a non-uniform scale has to live in the
	// rotation matrix. The geometry is the only place in this chain where that works:
	// its parent NiBillboardNode has its rotation overwritten every frame to face the
	// camera, so a scale written there would be wiped, while a scale written BELOW it is
	// applied inside the already camera-facing frame. That makes X width and Y height in
	// screen space, which is what the sliders mean.
	//
	// Caveat: bounding spheres are scaled by NiTransform::scale, not by this matrix, so
	// very large multipliers can cull slightly early. The config clamps to 0.1-4.0.
	ForEachGeometry(a_root, [width, height](RE::BSGeometry& a_geometry) {
		auto& rotate = a_geometry.local.rotate;
		rotate.entry[0] = RE::NiPoint4{ width, 0.0F, 0.0F, 0.0F };
		rotate.entry[1] = RE::NiPoint4{ 0.0F, height, 0.0F, 0.0F };
		rotate.entry[2] = RE::NiPoint4{ 0.0F, 0.0F, 1.0F, 0.0F };
	});
}

// Each puff peaks shortly after it is born and then dissipates, rather than starting at
// full strength and only decaying. x * e^(1-x) peaks at exactly 1.0 when age == tau, which
// gives a burst-then-billow shape instead of a step.
namespace
{
	float PuffEnvelope(float a_age, float a_tau)
	{
		if (a_age <= 0.0F || a_tau <= 0.0F) {
			return 0.0F;
		}
		const auto x = a_age / a_tau;
		return x * std::exp(1.0F - x);
	}
}

HazeManager::PuffState HazeManager::UpdatePuffs(ActiveHaze& a_haze, float a_heat) const
{
	PuffState state;
	const auto& config = Config::Get();
	if (!config.PulseEnabled() || a_haze.puffs.empty()) {
		a_haze.puffs.clear();
		return state;
	}

	const auto now = std::chrono::steady_clock::now();
	const auto tau = std::max(config.PulseDecaySeconds(), 0.02F);
	const auto lifetime = tau * 8.0F;  // envelope is under 1% of peak by then
	const auto variance = config.PuffVariance();

	for (auto it = a_haze.puffs.begin(); it != a_haze.puffs.end();) {
		const auto age = std::chrono::duration<float>(now - it->born).count();
		if (age > lifetime) {
			it = a_haze.puffs.erase(it);
			continue;
		}

		const auto envelope = PuffEnvelope(age, tau);
		const auto scatter = 1.0F + (variance * ((it->variance * 2.0F) - 1.0F));

		// Refraction is scaled by current heat so puffs do nothing on a cold barrel, but
		// size and rise are not - a puff leaving a barely-warm barrel should still be a
		// puff, just a faint one.
		state.refraction += config.PulseStrength() * envelope * a_heat * scatter;
		state.scale += config.PuffScale() * envelope * scatter;
		state.rise += config.PuffRise() * envelope * scatter;
		state.scroll += config.PuffScroll() * envelope * scatter;
		++it;
	}

	// Full-auto stacks a lot of puffs; without a ceiling the sum runs away.
	state.refraction = std::clamp(state.refraction, 0.0F, config.PulseStrength() * 3.0F);
	state.scale = std::clamp(state.scale, 0.0F, config.PuffScale() * 3.0F);
	state.rise = std::clamp(state.rise, 0.0F, config.PuffRise() * 3.0F);
	state.scroll = std::clamp(state.scroll, 0.0F, config.PuffScroll() * 3.0F);
	return state;
}

void HazeManager::Pulse(RE::TESObjectREFR* a_ref)
{
	const auto& config = Config::Get();
	if (!a_ref || !config.PulseEnabled()) {
		return;
	}

	std::scoped_lock locker(lock_);
	const auto it = active_.find(a_ref->formID);
	if (it == active_.end()) {
		return;
	}

	PulseLocked(it->second);
}

void HazeManager::PulseLocked(ActiveHaze& a_haze)
{
	const auto& config = Config::Get();
	if (!config.PulseEnabled()) {
		return;
	}

	auto& haze = a_haze;
	// Oldest puff is dropped rather than refused, so sustained fire keeps producing fresh
	// billows instead of going static once the cap is reached.
	const auto limit = std::max<std::size_t>(config.PuffMaxOverlap(), 1);
	while (haze.puffs.size() >= limit) {
		haze.puffs.erase(haze.puffs.begin());
	}

	// Cheap deterministic scatter so consecutive puffs differ - real turbulence is not
	// periodic, and identical repeats read as a machine blinking.
	haze.puffCounter = (haze.puffCounter * 1664525U) + 1013904223U;
	const auto seed = static_cast<float>((haze.puffCounter >> 8) & 0xFFFF) / 65535.0F;
	haze.puffs.push_back({ std::chrono::steady_clock::now(), seed });
}

bool HazeManager::HasActive(RE::TESFormID a_formID)
{
	std::scoped_lock locker(lock_);
	return active_.contains(a_formID);
}

void HazeManager::Clear()
{
	std::scoped_lock locker(lock_);
	if (Config::Get().DebugLogging()) {
		logger::info("Clear: releasing {} active art object(s)", active_.size());
	}

	for (auto& [formID, haze] : active_) {
		if (auto* effect = haze.effect.get()) {
			// Zero it first, exactly as DetachLocked does. Marking the effect finished only
			// asks ProcessLists to reap it; the material keeps whatever refractionPower was
			// last written until then, and art object models come from a shared cache, so an
			// abandoned non-zero value can persist into the next card that uses it.
			ApplyRefraction(effect->artObject3D.get(), 0.0F);
			effect->finished = true;
			effect->lifetime = 0.0F;
		}
	}
	active_.clear();
}
