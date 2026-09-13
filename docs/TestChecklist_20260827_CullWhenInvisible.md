# Test checklist - 0.12.3 "cull when invisible"

Package: `dist/GunHeatHaze-0.12.3-cull-when-invisible.zip` (13 files, 491906 bytes)
DLL: 796160 bytes. Proven 0.11.4 sources at `_backup/0.11.4-proven/`.

## The instrumentation ruled out this mod's CPU cost

From the 0.12.2 session (191 shots, ~50s of continuous fire):

```
Tick rate: 118 ticks/sec, 524 us total, 66 us worst
Tick rate: 117 ticks/sec, 475 us total, 60 us worst
```

**~500 microseconds of work per second of gameplay - 0.05% of one core.** Steady across the
whole session. The pacer is running at its intended ~118 Hz. One 55ms outlier on the very
first driving tick (art object first becoming resident), then nothing.

The attach path is also clean now: 191 shots, **1** `AttachHaze: art object applied`,
0 detaches.

So the extreme hit is not this mod's CPU work. That leaves the GPU, and the timeline fits:
`art object 3D ready` was logged for the first time ever in 0.12.1, which is the first build
where the card actually rendered - and the first build where you reported the hit surviving
the attach fix.

The Papyrus log gaps support it too. Within a single shot's handling:

```
13:08:55.744 AddHeat: form
13:08:55.786 IsWeaponAllowed   +42ms
13:08:55.803 caliber heat      +17ms
```

17-42ms between consecutive native calls in one event handler is the game thread being
starved, i.e. a symptom of a low framerate, not a cause of one.

## The defect this found

The card was **never culled**. A haze parked at refraction 0, or faded to nothing mid-cycle,
still went through the refraction pass every frame. Refraction samples the scene, and this
card is parented to the muzzle - directly in front of the first-person camera, so it covers
a large part of the screen. It was contributing nothing and costing full price, permanently,
from the moment of the first shot onward.

0.12.3 calls `SetAppCulled(true)` whenever refraction reaches zero and un-culls when it rises
again, on change only.

## RESULT - confirmed fixed (session 14:09-14:13, 730 shots)

Performance is good again, and the A/B was never needed: every `config loaded:` line in the
session reads `renderEnabled=true`, so the card was being drawn normally throughout. The
missing cull was the cause, not merely a suspect.

| measurement | value |
| --- | --- |
| shots | 730 |
| `AttachHaze: art object applied` | 2 |
| `DetachHaze: released` | 0 |
| `muzzle node changed` (weapon switches, re-applied) | 7 |
| `art object 3D ready` | 9 (2 attaches + 7 re-attaches) |
| cull transitions | 3 culled / 3 shown, correctly paired |
| tick cost | ~470 us per second of gameplay |
| warnings / errors | 0 / 0 |

The effect is still driven correctly - refraction p50 `0.0083`, max `0.039`; strength p50
`0.707`, max `0.899` - so culling is not clipping the visible part of the cycle. Transitions
pair cleanly with parking:

```
14:12:15.428  card culled
14:12:16.045  cooled; parking attachment
14:12:19.788  card shown
```

## Root cause, for the record

A refraction surface parented to the muzzle sits directly in front of the first-person
camera and covers a large part of the screen. Fallout 4 draws it every frame regardless of
`refractionPower`, and refraction samples the scene - so a card left attached at strength 0
costs full price while contributing nothing visible. Once 0.12.1 made attachments persist,
that cost became permanent from the first shot of the session onward.

Nothing in the plugin's CPU profile could ever have shown this: measured tick cost was
0.05% of a core throughout.

## Remaining housekeeping

- `bDebugLogging=1` is still on - 739 KB in about four minutes, and every line forces a disk
  flush. Worth setting to 0 for normal play.
- `bRenderEnabled` is now wired up and works; it stays useful as a diagnostic switch.

## Verify

1. **Fire, then stop.** The hit should now end when the shimmer fades, even though the
   attachment stays parked. Log shows `card culled` / `card shown` on each transition.
2. **The A/B that settles it.** Add to `Data\MCM\Settings\GunHeat.ini` under `[Haze]`:

   ```
   bRenderEnabled=0
   ```

   That keeps every system live - attach, tick, heat curve, puffs, logging - and draws
   nothing at all. Fire for a few seconds.

   - **Smooth with `bRenderEnabled=0`, hit returns with `=1`** - confirmed GPU cost of
     drawing the refraction card. The fix is then the asset and its screen coverage, not
     the plugin, and I will work on the card's size and shader flags.
   - **Hit in both cases** - it is not the card being drawn, and I will look outside the
     render path.

Please send the log plus which of those two you saw. `bRenderEnabled` was previously parsed
and logged but never actually used; it is wired up as of this build.

## Note

`bDebugLogging=1` currently costs 5 log lines per shot, each forcing a disk flush. Worth
turning off once we have the answer above - but leave it on for this test.
