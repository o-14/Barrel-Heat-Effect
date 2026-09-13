#pragma once

#include <atomic>
#include <vector>

// Route A delivery: hand the heat card to the engine's own hit-effect-art system rather
// than splicing it into the first-person scene graph by hand.
//
// TESObjectREFR::ApplyArtObject (REL::ID 357908) builds an OwnedController that stores
// our NiAVObject* at controller+0x18 and takes a reference on it. OwnedController::
// GetAttachRoot returns that pointer verbatim whenever it is non-null and only falls
// back to GetTargetReference()->Get3D() when it is null - confirmed by decompiling
// 0x140c7d270. So passing an explicit node wins outright, including a first-person one,
// and the engine then owns attachment, positioning, cell/3D swaps, save-load and
// teardown. See docs\GhidraFindings_20260806_ApplyArtObject.md.
//
// a_attachToCamera MUST stay false: that branch builds a different controller which
// never looks at the node we pass.

class HazeManager
{
public:
	static HazeManager& Get();

	bool Attach(RE::TESObjectREFR* a_ref);
	void Detach(RE::TESObjectREFR* a_ref);
	void SetStrength(RE::TESObjectREFR* a_ref, float a_strength);
	void Pulse(RE::TESObjectREFR* a_ref);
	// Reports one shot and lets the DLL own the whole cycle from there: it attaches on the
	// first shot, decays the heat on its own tick and detaches itself when the cycle ends.
	//
	// This exists because Papyrus timers could not be made to drive the cool-down. In a
	// 601-shot test session OnTimer fired 116 times and every single fire landed after the
	// cycle had already ended - not one did useful work. OnTimer also returns without
	// re-arming whenever its guard fails, so the chain dies permanently on its first bad
	// fire, and StopHaze was only ever reachable from that chain. With nothing decaying the
	// heat between shots the effect froze at its last strength the moment you stopped
	// firing. See docs\TestChecklist_20260826_DllTick.md.
	void AddHeat(RE::TESObjectREFR* a_ref, float a_amount, RE::TESFormID a_weaponID);
	// One step of the heat model for every live haze. Posted to the F4SE task interface and
	// re-posted while anything is still active, so it runs on the game thread once a frame.
	void Tick();
	// Starts the pacer thread that drives Tick(). Called once at plugin load.
	//
	// Tick() used to re-post itself to the F4SE task queue, which assumes tasks added
	// during a drain are held for the next frame. That is not something this plugin can
	// verify, and if the queue instead drains until empty, a self-re-posting task spins for
	// the whole frame - invisible in the log, because the per-tick line is throttled and
	// the heat curve runs off steady_clock either way. A pacer that sleeps between posts is
	// bounded by construction regardless of drain semantics.
	void StartPacer();
	[[nodiscard]] bool HasActive(RE::TESFormID a_formID);
	void Clear();

private:
	struct ActiveHaze
	{
		// BSTempEffect derives from NiObject, so holding a smart pointer keeps the
		// effect alive even if ProcessLists decides to reap it mid-cycle.
		RE::NiPointer<RE::ModelReferenceEffect> effect;
		RE::NiPointer<RE::NiAVObject>           attachNode;
		std::string                             attachNodeName;
		std::string                             attachSource;
		// The heat model, moved here from GunHeatController.psc. Same curve, same settings,
		// driven by Tick() instead of by OnTimer.
		float                                   heat{ 0.0F };
		float                                   visible{ 0.0F };
		float                                   peakHeat{ 0.0F };
		std::chrono::steady_clock::time_point   lastShot{};
		bool                                    hasShot{ false };
		std::chrono::steady_clock::time_point   lastHeatTick{};
		bool                                    hasHeatTick{ false };
		// Cool, but still attached. Tearing the art object down at the end of every cycle
		// meant a full ApplyArtObject build-and-teardown per shot once the player fired
		// slower than one cycle (~1.3s for a single shot), which is expensive - and worse,
		// BGSArtObjectCloneTask is asynchronous and never finished inside that window, so
		// artObject3D stayed null and the card never rendered at all. Going idle instead
		// keeps the clone warm and makes repeat shots free.
		bool                                    idle{ false };
		// The per-tick debug line now runs once a frame rather than a couple of times a
		// second, and the logger flushes to disk on every info record - so it is throttled
		// rather than left to issue ~60 synchronous flushes a second on the game thread.
		std::chrono::steady_clock::time_point   lastDebugLog{};
		// Whether the card is currently culled. A faded or parked haze was still being
		// drawn every frame - it went through the refraction pass contributing nothing,
		// and the card sits right in front of the first-person camera, so it is large on
		// screen. Tracked so SetAppCulled is only called on an actual change.
		bool                                    culled{ false };
		// Which weapon this heat belongs to, so a switch can start the new barrel cold.
		// Keyed on the weapon form rather than the muzzle node: node pointers also change
		// on camera transitions and reloads, which would reset heat spuriously.
		RE::TESFormID                           weaponID{ 0 };
		bool                                    warnedMissingArt3D{ false };
		bool                                    loggedArt3D{ false };
		// Experimental puffing. Each shot spawns its own puff and they SUM, rather than one
		// shot restarting a single envelope - that is what turns rapid fire into a rolling
		// billow instead of one repeatedly-reset bump. Each puff also expands and rises as
		// it dissipates, because a bump in refraction alone reads as a flicker rather than
		// as a body of hot air leaving the barrel.
		struct Puff
		{
			std::chrono::steady_clock::time_point born;
			float                                 variance;
		};
		std::vector<Puff>                       puffs;
		std::uint32_t                           puffCounter{ 0 };
		// Movement smear: the card is rigidly parented to the muzzle, so it can never lag
		// on its own. Sampling how far the muzzle travelled between ticks lets us push the
		// card back along that motion, which reads as heat being left behind.
		RE::NiPoint3                            lastNodeWorld{};
		std::chrono::steady_clock::time_point   lastSample{};
		bool                                    hasSample{ false };
		RE::NiPoint3                            smear{};
		// Accumulated texture scroll, in tiles. Owned here rather than by the NIF's own
		// V-offset controller, so puffs can push the pattern upward without moving the card.
		float                                   scroll{ 0.0F };
		std::chrono::steady_clock::time_point   lastScrollSample{};
		bool                                    hasScrollSample{ false };
	};

	// Summed contribution of every live puff for this tick.
	struct PuffState
	{
		float refraction{ 0.0F };
		float scale{ 0.0F };
		float rise{ 0.0F };
		float scroll{ 0.0F };
	};

	// Body of SetStrength once the caller already holds lock_ and has a live entry, so the
	// native path and Tick() drive the visuals through exactly the same code.
	void                       SetStrengthLocked(ActiveHaze& a_haze, RE::TESObjectREFR* a_ref, float a_strength);
	void                       PulseLocked(ActiveHaze& a_haze);
	// Advances heat/visible by a_elapsed. Returns false when the cycle is over.
	[[nodiscard]] bool         AdvanceHeat(ActiveHaze& a_haze, float a_elapsed) const;

	[[nodiscard]] RE::NiPoint3 UpdateSmear(ActiveHaze& a_haze) const;
	[[nodiscard]] PuffState    UpdatePuffs(ActiveHaze& a_haze, float a_heat) const;
	void                       ApplySize(RE::NiAVObject* a_root, float a_puffScale) const;

	[[nodiscard]] RE::BGSArtObject* LookupArtObject() const;
	[[nodiscard]] RE::NiAVObject*   ResolveAttachNode(RE::TESObjectREFR* a_ref, std::string& a_source) const;
	[[nodiscard]] RE::NiAVObject*   FindFireNode(RE::Actor* a_actor) const;
	[[nodiscard]] RE::NiAVObject*   FindMuzzleByName(RE::NiAVObject* a_root) const;
	void                            ApplyRefraction(RE::NiAVObject* a_root, float a_strength) const;
	void                            ApplyScroll(ActiveHaze& a_haze, RE::NiAVObject* a_root, float a_puffScroll) const;
	void                            DetachLocked(RE::TESFormID a_formID);
	// Re-points a live haze at a different muzzle node, e.g. after a weapon switch.
	bool                            Reattach(ActiveHaze& a_haze, RE::TESObjectREFR* a_ref, RE::NiAVObject* a_node) const;

	// Set whenever a haze needs driving; cleared by Tick() when everything has parked. The
	// pacer polls this rather than taking lock_, so an idle barrel never contends with the
	// game thread.
	std::atomic<bool>                                hasWork_{ false };
	std::atomic<bool>                                pacerStarted_{ false };
	// Tick instrumentation, reported once a second under bDebugLogging.
	std::atomic<std::uint32_t>                       tickCount_{ 0 };
	std::atomic<std::uint64_t>                       tickMicros_{ 0 };
	std::atomic<std::uint64_t>                       tickMaxMicros_{ 0 };
	std::mutex                                       lock_;
	std::unordered_map<RE::TESFormID, ActiveHaze>    active_;
};
