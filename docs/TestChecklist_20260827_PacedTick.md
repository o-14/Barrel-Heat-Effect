# Test checklist - 0.12.2 "paced tick + instrumentation"

Package: `dist/GunHeatHaze-0.12.2-paced-tick.zip` (13 files, 491333 bytes)
DLL: 795136 bytes. Proven 0.11.4 sources at `_backup/0.11.4-proven/`.

## What 0.12.1 fixed, and what it did not

0.12.1 fixed the attach churn. From its log (9 shots):

| line | 0.12.0 | 0.12.1 |
| --- | --- | --- |
| `AttachHaze: art object applied` | 8 (one per shot) | **1** |
| `DetachHaze: released` | 8 | **0** |
| `art object 3D ready` | 0 | **1** |
| `cooled; parking attachment` | - | 4 |

`art object 3D ready` had never once been logged before this build, so the card is now
actually resident and being driven. The heat curve is healthy too - `SetHazeStrength` lines
land at exactly 0.250s intervals with heat decaying smoothly.

But the performance hit is still there, so it is not the attach path.

## The remaining suspect, and why this build settles it

`Tick()` re-posted itself to the F4SE task queue to get a per-frame cadence. That is only
safe if tasks added *during* a drain are held for the next frame. If the queue instead
drains until empty, a self-re-posting task spins for the entire frame - and nothing in the
log would show it, because the per-tick line is throttled to 4/sec and the heat curve runs
off `steady_clock` regardless of how many times Tick is entered.

Two changes:

1. **A pacer thread replaces the self-re-posting chain.** One permanent thread posts at most
   one `Tick` every 8ms while a haze is being driven, and polls a single atomic at 10 Hz
   when everything is parked. Bounded by construction, whatever the drain semantics are.
2. **The tick is instrumented.** Once a second, with `bDebugLogging=1`:
   `Tick rate: N ticks/sec, X us total, Y us worst`.

## Verify

1. **Fire and watch the framerate.** If the hit is gone, the self-re-posting chain was the
   cause and the pacer fixes it.
2. **Read one `Tick rate:` line.** This is the measurement that matters:
   - `~125 ticks/sec` - the pacer is working as intended.
   - `us total` in the low thousands - the tick body is cheap; if the hit persists it is
     not this code and I will look elsewhere.
   - `us total` in the hundreds of thousands - the tick body itself is expensive, and
     `us worst` says whether it is one bad call or uniform cost.
3. Confirm `heat pacer started (125 Hz while driving, 10 Hz idle)` appears once at load.

Please send the log after firing for a few seconds either way - one `Tick rate:` line tells
me which of the two remaining possibilities it is.

## If the hit is gone

The 8ms interval is conservative. It can go to 16ms (~60 Hz) if any cost remains; the heat
curve is elapsed-time based, so the cadence does not change how the effect looks or how
fast it fades.
