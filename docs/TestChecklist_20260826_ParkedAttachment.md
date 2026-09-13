# Test checklist - 0.12.1 "parked attachment"

Package: `dist/GunHeatHaze-0.12.1-parked-attachment.zip` (13 files, 490214 bytes)
DLL: 792576 bytes. Proven 0.11.4 sources still at `_backup/0.11.4-proven/`.

## What 0.12.0 got wrong

0.12.0 correctly moved the heat tick into the DLL, and that part works. But it also
detached the art object the moment a cycle cooled. From the 0.12.0 session log (8 shots):

| line | count |
| --- | --- |
| `AttachHaze: art object applied` | 8 |
| `Tick: cycle complete ... detaching` | 8 |
| `DetachHaze: released` | 8 |
| `SetHazeStrength: art object 3D not ready yet` | 8 |
| `SetHazeStrength: art object 3D ready` | **0** |

One full `ApplyArtObject` build and teardown per shot. That is the performance hit.

The cycle is short by design: with the player's `Data\MCM\Settings\GunHeat.ini`
(`fMinFadeOutSeconds=8`, `fMaxFadeOutSeconds=14`), one shot gives `heat=0.15` decaying at
`1.0/8.9` per second, so heat reaches zero in about **1.3 seconds**. Fire slower than that
and every shot is its own complete cycle.

0.11.4 hid this: its cycle never ended, because the timer was dead, so it attached once and
stayed. Making cycles actually end exposed the churn.

The same numbers explain why nothing rendered - `BGSArtObjectCloneTask` is asynchronous and
1.3 seconds never gave it time to finish, so `artObject3D` stayed null for the whole life of
every cycle.

## The change

A cooled cycle now **parks** instead of detaching: refraction is written to 0 and the entry
stays in `active_`, so the next shot reuses a clone that is already resident. The tick chain
stops while everything is parked and restarts on the next shot, so an idle barrel costs
nothing.

Also in this build:
- `Config::ReloadOverrides()` moved to `AddHeat` (throttled to 1/sec) - it used to live in
  `Attach`, which now barely runs, and MCM edits would have stopped applying.
- The per-tick debug line is throttled to 4/sec. It now runs once a frame, and the logger
  flushes to disk on every info record.
- Log lines carry timestamps (`[%H:%M:%S.%e]`). Diagnosing this repeatedly came down to
  "how long was the gap", which the old bare-level pattern could not answer.
- The per-tick line now includes `heat=` alongside `strength=`.

## Verify

1. **Performance.** Fire single shots several seconds apart. No stutter per shot. The log
   should show `AttachHaze: art object applied` **once**, not once per shot.
2. **It renders.** `SetHazeStrength: art object 3D ready, root=...` should now appear -
   this line has never once been logged. If it still does not, the card is not the issue and
   the clone is failing for another reason.
3. **Parking.** After the shimmer fades, expect `Tick: form 00000014 cooled; parking
   attachment` and **no** `DetachHaze: released`.
4. **Reuse.** Fire again after it parks. It should ramp back up with no attach line.
5. **Weapon switch.** Switch mid-cycle and after a park. Expect `muzzle node changed` and one
   re-apply, not one per shot.
6. **Save/reload mid-effect.** No stuck effect.
7. **MCM.** Change Heat Intensity or a cool-down slider; the next burst should reflect it.

## Note on cycle length

`fEffectDurationSeconds=3.0` in the current MCM settings caps how long the shimmer stays up
after the last shot, but heat decay still governs cycle length - and for a single shot that
is ~1.3s. If single shots should leave a longer-lived shimmer, raise `fMinFadeOutSeconds` or
`fHeatPerShot`; both are MCM sliders.
