# Save-Load Crash Fix - 2026-07-13

## Evidence

- `f4se.log` reports `GunHeat.dll ... loaded correctly` and reaches `RegisterPapyrusFunctions_Hook`.
- `GunHeat.log` reports configuration load and successful native registration.
- The final line resolves `GunHeatControllerQuest`; the next expected `Start dispatched` line is absent.
- No projectile launch, NIF controller, or shader-refraction code ran before the crash.

## Cause

The DLL synchronously acquired a Papyrus quest handle and dispatched `Quest.Start()` from an F4SE game lifecycle message. This happened while a save was restoring VM/object state. The ESP already marks `GunHeatControllerQuest` as `Start Game Enabled`, so this forced bootstrap was both redundant and unsafe.

## Fix

- Removed native `Quest.Start()` dispatch.
- The general game-data message only clears transient visual handles and reloads the INI.
- Existing saves that did not instantiate the newly added start-enabled quest now queue
  `startquest GunHeatControllerQuest` after `kPostLoadGame`, on the next game-thread task.
- The deferred path never acquires or dispatches through a Papyrus VM object handle.

No ESP, Papyrus, NIF, projectile, heat, animation, or refraction behavior changed in this fix.
