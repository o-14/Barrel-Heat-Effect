# Stronger puffing - 2026-08-21

Build: `dist\GunHeatHaze-0.11.0-puffing.zip`

## Restore point for the proven build

```text
Backups\GunHeatHaze-v0.10.0-WORKING-snapshot-20260821.zip   (112 files + RESTORE.md)
dist\GunHeatHaze-0.10.0-effect-duration.zip                 (installable, no rebuild)
```

If this build is worse, reinstall the `dist` zip and you are back exactly where you were.

## What was limiting the old pulse

The 0.7.0 pulse was **one** envelope per haze, and each shot *restarted* it:

```text
refraction += pulseStrength * exp(-age / decay) * heat
```

Three consequences, all of which read as "a bump" rather than "a puff":

1. **No accumulation.** Rapid fire kept resetting the same envelope, so ten shots looked
   much like one. Real puffing from sustained fire should pile up.
2. **Instant attack.** It jumped to full and only decayed - a step, not a burst.
3. **Refraction only.** Nothing moved or grew, so it flickered in place rather than
   reading as a body of hot air leaving the barrel.

The Minigun sells its puffing largely through the **V-offset tile scroll** (one full tile
per 1.667 s, which our card already matches) plus movement. Strength modulation alone was
never going to get there.

## What changed

**Puffs now accumulate.** Each shot spawns its own puff with its own birth time, and they
**sum**. Sustained fire rolls into a continuous billow instead of one repeatedly-reset
bump. Capped by `uPuffMaxOverlap` (6), dropping the oldest so long bursts keep producing
fresh billows rather than going static.

**Burst-then-dissipate envelope.** Replaced `exp(-age/tau)` with `x * e^(1-x)` where
`x = age/tau`. That peaks at exactly 1.0 when `age == tau` and falls away after, so each
puff swells in and dissipates instead of snapping on.

**Puffs expand.** Each one briefly swells the card through the same size matrix the
width/height sliders use. The vertical axis takes the full expansion and the horizontal
only 60% of it, so puffs billow upward rather than ballooning evenly.

**Puffs rise.** Each adds a transient upward offset that decays with its envelope, so a
shot visibly pushes heat up off the barrel.

**Puffs differ.** A per-puff random scatter (`fPuffVariance`) means consecutive puffs are
not identical - identical repeats read as a machine blinking rather than turbulence.

Refraction is still scaled by current heat, so puffs do nothing on a cold barrel. Size and
rise are deliberately **not** heat-scaled: a puff off a barely-warm barrel should still be
a puff, just a faint one.

## New MCM controls (Experimental)

| Control | Default | What it does |
| --- | --- | --- |
| Puff expansion | 0.18 | how much each puff swells the effect |
| Puff rise | 2.5 | how far each puff drifts up, in game units |
| Puff overlap | 6 | how many puffs stack; higher = continuous billow, lower = distinct shots |
| Puff variance | 0.35 | scatter between consecutive puffs |

Setting **Puff expansion** and **Puff rise** to 0 reduces this to the old
refraction-only behaviour, so the previous look is still reachable without reinstalling.

Panel is now 25 controls.

## Test

1. Install. `GunHeat.dll` is **776704** bytes.
2. Get the barrel hot, then hold the trigger - the plume should roll and billow rather
   than flicker at one size.
3. Fire single shots into a hot barrel - each should swell and drift up as it fades.

Tuning if it is too much: drop **Puff expansion** first, then **Puff overlap**. If it is
too subtle, raise **Puff overlap** and **Pulse strength** together.

The debug log now reports the live puff state per tick:

```text
SetHazeStrength: ... puffs=4, puffRefr=..., puffScale=..., puffRise=...
```
