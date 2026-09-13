# Stuck effect after weapon switch / reload - 2026-08-26

Build: `dist\GunHeatHaze-0.11.4-stuck-effect-fix.zip`

## The line fix held

`fPuffRise=0` plus the new texture scroll behaved exactly as designed:

```text
scroll accumulator   0 -> 0.9999713     advancing and wrapping at 1.0
puffScroll           0 -> 0.4479        cap is 0.15 x 3 = 0.45
0 warnings, 0 errors, 0 NaN
```

## Why the effect got stuck

**The heat timer was dead.** Across 507 shots there were only 522 `UpdateHeat` calls. With
`timerInterval=0.05` a live timer alone would have produced thousands. And the gaps between
them give it away:

```text
UpdateHeat elapsed:  min=0.0999  median=0.350  max=0.600
```

Those are your inter-shot intervals, not 0.05 s ticks. Every `UpdateHeat` was the one fired
from `OnAnimationEvent`, not from `OnTimer`.

That is the whole symptom. `UpdateHeat` is the only thing that decays heat and recomputes
strength, so with the timer dead:

- heat only moves while you are pulling the trigger,
- the moment you stop, nothing calls `SetHazeStrength` again,
- and `refractionPower` simply keeps whatever value was written last.

The effect freezes at full strength. Confirming it: `StopHaze` ran **zero** times all
session, minimum heat ever reached was **0.116**, and there were **0 detaches** against 2
attaches and 6 re-attaches.

## Why the timer died - my bug

The config-path fix routed the heat curve through `GetHeatSetting()`, and I made that call
`ReloadOverrides()` so slider changes could never get stuck again. `LoadIniConfig()` asks
for nine settings, and it runs on every shot.

Nine file opens and reparses per shot, on the game thread:

```text
applying MCM overrides:  4573
shots:                    507
                       = 9.0 reads per shot
```

That is enough VM and I/O pressure to stop `OnTimer` being serviced.

## Fixes

**1. Throttle the overlay read to once per second.** Same responsiveness for MCM edits,
without hammering the game thread. This is the root-cause fix.

**2. `Clear()` now zeroes refraction before abandoning an effect**, exactly as
`DetachLocked()` already did. Marking an effect finished only asks ProcessLists to reap it;
until then the material keeps its last `refractionPower`, and art object models come from a
shared cache, so an abandoned non-zero value can bleed into the next card. This is what made
a reload come back with the effect already on.

**3. The timer is re-armed on every shot while a cycle is active.** Papyrus timers do not
survive a save load, so a cycle that was running when you saved came back with no timer
behind it. Restarting an existing timer is cheap, and it guarantees a live timer for as long
as you are firing.

## Test

1. Install. `GunHeat.dll` is **782848** bytes.
2. Heat the barrel, stop firing, and watch it fade out on its own - then confirm the log
   shows `StopHaze` / `haze stopped` and a `DetachHaze: released`.
3. Switch weapons mid-effect: it should follow the new weapon and still fade normally.
4. Save mid-effect, reload: the effect should not be stuck on.
5. Sanity check the fix took: `applying MCM overrides` should now be roughly one per second
   of play, not nine per shot.
