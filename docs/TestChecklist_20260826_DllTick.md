# Test checklist - 0.12.0 "DLL-owned heat tick"

Package: `dist/GunHeatHaze-0.12.0-dll-tick.zip` (13 files, 490266 bytes)
DLL: 792064 bytes. Previous proven build kept at `_backup/0.11.4-proven/`.

## What this changes and why

The cool-down was driven from `GunHeatController.OnTimer`. It never worked. Evidence from
the 0.11.4 session log (601 shots):

| measurement | value |
| --- | --- |
| `OnTimer` fires | 116 |
| ...of those, fired while `hazeActive=True` | **0** |
| longest run of back-to-back ignored fires | 106 |
| `StartTimer` calls (one per shot, plus StartHaze) | 601 |
| `StopHaze` | 3 |
| worst `UpdateHeat` gap | `elapsed=17.026993`, frozen at `strength=0.844` |

Two defects behind that:

1. `OnTimer` returned without re-arming whenever its guard failed, and `StopHaze` was only
   reachable from that chain. The first bad fire killed the drive permanently.
2. `StartTimer` does not restart a pending timer, contrary to the comment previously in
   `OnAnimationEvent` - 601 calls produced 116 fires, all landing after the cycle ended.

With no timer landing during a cycle, `OnAnimationEvent` was the only caller of
`UpdateHeat`. Nothing decayed heat between shots, so the effect froze at its last strength
the moment the player stopped firing - on the first weapon, with no switch needed.

The heat model now lives in the DLL (`HazeManager::AdvanceHeat`) and is driven by
`HazeManager::Tick`, a self-re-posting F4SE task that runs on the game thread while any
haze is active. Papyrus reports the shot and nothing else.

Same curve, same settings, same MCM overlay - the port is line-for-line from the old
`UpdateHeat`.

## Verify

1. **The core fix.** Fire until the shimmer is up, then stop. It must fade out on its own
   and disappear. Log should show `Tick: cycle complete for form 00000014; detaching`
   followed by `DetachHaze: released`.
2. **Weapon switch mid-effect.** Heat one barrel, switch while the shimmer is visible. The
   effect moves to the new muzzle (`muzzle node changed`) and still fades on its own.
3. **Save/reload mid-effect.** Reload with the shimmer up. No stuck effect, and firing
   again starts a clean cycle. There is no `hazeActive` flag in the save any more, so the
   old stale-state failure cannot recur.
4. **Timer noise is gone.** `OnTimer: obsolete timer=` may appear a few times from timers
   left pending in an existing save, then never again. No `StartTimer` on the hot path.
5. **Tick cadence.** With `bDebugLogging=1`, `SetHazeStrength:` lines should now be smooth
   and frame-paced for the whole cool-down, not clustered around shots.
6. **MCM still applies.** Change Heat Intensity or a cool-down slider and confirm the next
   burst reflects it. `applying MCM overrides` stays throttled to ~1/sec.

## Notes

- Attach now happens on the **first shot** rather than at the `fMinHeatToShow` threshold.
  The card is authored with `refractionStrength 0` and the visual ramp still gates on
  `fMinHeatToShow`, so nothing renders any earlier than before - it just gives the async
  `BGSArtObjectCloneTask` the whole warm-up to finish in.
- Turn `bDebugLogging` back off for normal play; the last session produced 1.3 MB.
