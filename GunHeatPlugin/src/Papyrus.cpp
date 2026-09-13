#include "Papyrus.h"

#include "Config.h"
#include "HazeManager.h"

namespace
{
	RE::TESObjectREFR* LookupRef(RE::TESFormID a_formID)
	{
		return RE::TESForm::GetFormByID<RE::TESObjectREFR>(a_formID);
	}

	bool QueueGameTask(std::string_view a_name, std::function<void()> a_task)
	{
		const auto* tasks = F4SE::GetTaskInterface();
		if (!tasks) {
			logger::warn("Papyrus: {} failed; F4SE task interface unavailable", a_name);
			return false;
		}

		tasks->AddTask([name = std::string(a_name), task = std::move(a_task)]() mutable {
			if (Config::Get().DebugLogging()) {
				logger::info("Papyrus: running queued {}", name);
			}
			task();
		});
		return true;
	}

	bool AttachHaze(std::monostate, RE::TESObjectREFR* a_ref)
	{
		if (!a_ref) {
			logger::warn("Papyrus: AttachHaze rejected null reference");
			return false;
		}

		const auto formID = a_ref->formID;
		const auto queued = QueueGameTask("AttachHaze", [formID]() {
			HazeManager::Get().Attach(LookupRef(formID));
		});
		if (Config::Get().DebugLogging()) {
			logger::info("Papyrus: AttachHaze form={:08X}, queued={}", formID, queued);
		}
		return queued;
	}

	void DetachHaze(std::monostate, RE::TESObjectREFR* a_ref)
	{
		if (!a_ref) {
			logger::info("Papyrus: DetachHaze ignored null reference");
			return;
		}

		const auto formID = a_ref->formID;
		const auto queued = QueueGameTask("DetachHaze", [formID]() {
			HazeManager::Get().Detach(LookupRef(formID));
		});
		if (Config::Get().DebugLogging()) {
			logger::info("Papyrus: DetachHaze form={:08X}, queued={}", formID, queued);
		}
	}

	// Reports one shot. Everything after this - attach, heat decay, the visual ramp, puffs
	// and the eventual detach - is owned by the DLL's own tick, so the cool-down no longer
	// depends on a Papyrus timer landing.
	void AddHeat(std::monostate, RE::TESObjectREFR* a_ref, float a_amount, RE::TESObjectWEAP* a_weapon)
	{
		if (!a_ref) {
			logger::info("Papyrus: AddHeat ignored null reference");
			return;
		}

		const auto formID = a_ref->formID;
		const auto weaponID = a_weapon ? a_weapon->formID : 0;
		const auto queued = QueueGameTask("AddHeat", [formID, a_amount, weaponID]() {
			HazeManager::Get().AddHeat(LookupRef(formID), a_amount, weaponID);
		});
		if (Config::Get().DebugLogging()) {
			logger::info("Papyrus: AddHeat form={:08X}, amount={}, weapon={:08X}, queued={}",
				formID, a_amount, weaponID, queued);
		}
	}

	void SetHazeStrength(std::monostate, RE::TESObjectREFR* a_ref, float a_strength)
	{
		if (!a_ref) {
			logger::info("Papyrus: SetHazeStrength ignored null reference");
			return;
		}

		const auto formID = a_ref->formID;
		const auto queued = QueueGameTask("SetHazeStrength", [formID, a_strength]() {
			auto* ref = LookupRef(formID);
			HazeManager::Get().SetStrength(ref, a_strength);
		});
		if (Config::Get().DebugLogging()) {
			logger::info("Papyrus: SetHazeStrength form={:08X}, strength={}, queued={}", formID, a_strength, queued);
		}
	}

	void PulseHeat(std::monostate, RE::TESObjectREFR* a_ref)
	{
		if (!a_ref || !Config::Get().PulseEnabled()) {
			return;
		}

		const auto formID = a_ref->formID;
		QueueGameTask("PulseHeat", [formID]() {
			HazeManager::Get().Pulse(LookupRef(formID));
		});
	}

	// Lets Papyrus reconcile its own persisted hazeActive flag against reality. The DLL
	// clears every active haze on game load, but hazeActive lives in the save and survives,
	// so a save made mid-cycle comes back with the two disagreeing.
	bool HasActiveHaze(std::monostate, RE::TESObjectREFR* a_ref)
	{
		return a_ref ? HazeManager::Get().HasActive(a_ref->formID) : false;
	}

	bool IsWeaponAllowed(std::monostate, RE::TESObjectWEAP* a_weapon)
	{
		const auto allowed = Config::Get().IsWeaponAllowed(a_weapon);
		if (Config::Get().DebugLogging()) {
			logger::info("Papyrus: IsWeaponAllowed form={:08X}, allowed={}",
				a_weapon ? a_weapon->formID : 0,
				allowed);
		}
		return allowed;
	}

	float GetHeatPerShot(std::monostate, RE::TESObjectWEAP* a_weapon)
	{
		return Config::Get().GetHeatPerShot(a_weapon);
	}

	float GetIniFloat(std::monostate, RE::BSFixedString a_section, RE::BSFixedString a_key)
	{
		return Config::Get().GetFloat(a_section.c_str(), a_key.c_str(), 0.0F);
	}

	// Reads the typed heat-curve settings straight off Config, bypassing the generic
	// floats_ map that GetIniFloat() uses. Also refreshes the MCM overlay first, so a
	// slider change is picked up even when no heat cycle is currently running - the
	// previous design only refreshed inside StartHaze(), which meant that setting
	// fHeatPerShot low enough to stop cycles starting also stopped the config being
	// re-read, locking the mod out until a save reload.
	float GetHeatSetting(std::monostate, RE::BSFixedString a_key)
	{
		auto& config = Config::Get();
		config.ReloadOverrides();

		const std::string_view key(a_key.c_str() ? a_key.c_str() : "");
		if (key == "fHeatPerShot") return config.HeatPerShot();
		if (key == "fMinHeatToShow") return config.MinHeatToShow();
		if (key == "fMaxIntensity") return config.MaxIntensity();
		if (key == "fFadeInSeconds") return config.FadeInSeconds();
		if (key == "fFadeOutSeconds") return config.FadeOutSeconds();
		if (key == "fEffectDurationSeconds") return config.EffectDurationSeconds();
		if (key == "fMinFadeOutSeconds") return config.MinFadeOutSeconds();
		if (key == "fMaxFadeOutSeconds") return config.MaxFadeOutSeconds();

		logger::warn("GetHeatSetting: unknown key {}", key);
		return 0.0F;
	}

	void Log(std::monostate, RE::BSFixedString a_message)
	{
		if (Config::Get().DebugLogging()) {
			logger::info("Papyrus: {}", a_message.c_str());
		}
	}
}

bool Papyrus::Register(RE::BSScript::IVirtualMachine* a_vm)
{
	if (!a_vm) {
		return false;
	}

	a_vm->BindNativeMethod("GunHeat:GunHeatNative", "AttachHaze", AttachHaze);
	a_vm->BindNativeMethod("GunHeat:GunHeatNative", "DetachHaze", DetachHaze);
	a_vm->BindNativeMethod("GunHeat:GunHeatNative", "SetHazeStrength", SetHazeStrength);
	a_vm->BindNativeMethod("GunHeat:GunHeatNative", "AddHeat", AddHeat);
	a_vm->BindNativeMethod("GunHeat:GunHeatNative", "PulseHeat", PulseHeat);
	a_vm->BindNativeMethod("GunHeat:GunHeatNative", "HasActiveHaze", HasActiveHaze);
	a_vm->BindNativeMethod("GunHeat:GunHeatNative", "IsWeaponAllowed", IsWeaponAllowed);
	a_vm->BindNativeMethod("GunHeat:GunHeatNative", "GetHeatPerShot", GetHeatPerShot);
	a_vm->BindNativeMethod("GunHeat:GunHeatNative", "GetIniFloat", GetIniFloat);
	a_vm->BindNativeMethod("GunHeat:GunHeatNative", "GetHeatSetting", GetHeatSetting);
	a_vm->BindNativeMethod("GunHeat:GunHeatNative", "Log", Log);

	logger::info("registered Papyrus natives");
	return true;
}
