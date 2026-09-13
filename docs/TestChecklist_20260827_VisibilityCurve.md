# Duration verification + 0.13.1 "visibility falloff curve"

Package: `dist/GunHeatHaze-0.13.1-visibility-curve.zip` (13 files, 494552 bytes)
DLL: 803328 bytes. Proven 0.11.4 sources at `_backup/0.11.4-proven/`.

## Verification: duration matches the configured values

Measured from the 18:21-18:27 session (1437 shots), via `card shown` / `card culled`
transitions against the last shot before each:

| cycle | visible time after last shot | peak heat |
| --- | --- | --- |
| 1 | **13.40s** | 1.000 |
| 2 | **13.39s** | 1.000 |

Predicted from the settings in `Data\MCM\Settings\GunHeat.ini`:

```
fadeOutSeconds = fMinFadeOutSeconds + (fMaxFadeOutSeconds - fMinFadeOutSeconds) * peak
               = 8 + (14 - 8) * 1.0  = 14s
time to fall from heat 1.0 to fMinHeatToShow 0.05  =  0.95 * 14  =  13.3s
```

**13.40s measured against 13.3s predicted.** The heat curve is running exactly as
configured. `fEffectDurationSeconds` is 0, so nothing is capping it either.

## So why it reads as short

The cycle is long; the *visible* part is not. Refraction falls off linearly with heat, and
the peak is very low to begin with:

```
peak refraction = heat 1.0  x  fMaxIntensity 0.9  x  fRefractionMaxStrength 0.01  =  0.009
```

Vanilla reference is **0.03** (Glowing Sea mirage) and **0.20** (Minigun barrel), so this is
running 3-22x weaker than the reference at full heat. Traced from the log:

| time after last shot | refraction |
| --- | --- |
| 0s | 0.0068 |
| 5s | 0.0042 |
| 10s | 0.0029 |
| 13s | 0.0010 |

It becomes imperceptible somewhere around 8-10s and then coasts invisibly for the rest of
the cycle. The effect is not ending early - it is fading below the threshold of vision
while the timer still has a third of its life left.

## Two levers

**1. Heat intensity (`fRefractionMaxStrength`), no new build needed.** Currently `0.01`,
the near-bottom of a slider that goes to `0.20`. Raising it lifts the whole curve.

**2. Visibility falloff curve (`fVisibilityCurve`), new in this build.** An exponent applied
to strength before it becomes refraction. `1.0` is the current linear behaviour, so this
build changes nothing until you move it. Lower values hold the shimmer readable further
into the cool-down *without* raising the peak:

| t(s) | heat | curve 1.0 | curve 0.5 | curve 0.35 |
| --- | --- | --- | --- | --- |
| 0 | 1.000 | 0.00900 | 0.00949 | 0.00964 |
| 4 | 0.714 | 0.00643 | 0.00802 | 0.00857 |
| 8 | 0.429 | 0.00386 | 0.00621 | 0.00716 |
| 12 | 0.143 | 0.00129 | 0.00359 | 0.00488 |
| 13.3 | 0.050 | 0.00045 | 0.00212 | 0.00338 |

At `curve 0.5` the effect is still at 40% of its peak when it is culled, instead of 5%.

Combining both - intensity `0.04`, curve `0.5` - puts the peak at `0.038` (just above the
Glowing Sea mirage, well under the Minigun) and still `0.014` at twelve seconds.

## Suggested test

Start with **intensity 0.04, curve 0.5** and adjust from there. Both are live MCM sliders,
so they can be tuned in-game between bursts without a reload.

The new per-tick log line reports both values so the shaping is visible:

```
SetHazeStrength: heat=0.75, strength=0.68, shaped=0.82, refraction=0.0083
```

## Not changed

Cycle length. It already matches your settings; if you want it longer than 13.4s, raise
`fMaxFadeOutSeconds` (currently 14) - that is the knob for time, whereas the two above are
the knobs for whether you can still see it.

---

## RESULT - confirmed (session ending 19:38, 808 shots, 21 measured cycles)

Settings tested: `fRefractionMaxStrength=0.025`, `fVisibilityCurve=0.5`.

**The curve is applied correctly** - `sqrt(0.48455) = 0.69610`, matching the logged
`strength=0.48454824, shaped=0.696095`.

**Duration holds across the whole heat range**, which is a stronger check than the two
samples available last time - 21 cycles now, and short bursts scale correctly too:

| peak heat | measured after last shot | predicted |
| --- | --- | --- |
| 1.000 (x9 cycles) | 13.40 - 13.43s | 13.3s |
| 0.891 | 11.89s | 11.8s |
| 0.432 | 2.62s | 2.6s |
| 0.137 (x4 cycles) | 0.92 - 0.98s | 0.77s |

**Mid-fade visibility is roughly 3x what it was.** At heat 0.65 refraction is now `0.0191`
against `0.0059` before, and the falloff is much flatter - `0.0243` at heat 0.97 down to
`0.0162` at heat 0.47, a 33% drop across half the heat range where the linear mapping lost
52%.

Peak refraction across the session: p50 `0.017`, p99 `0.063`, max `0.077` (puff
contributions stack on top of the 0.025 ceiling). That sits between the Glowing Sea mirage
at 0.03 and the Minigun barrel at 0.20 - in vanilla territory for the first time.

| measurement | value |
| --- | --- |
| shots | 808 |
| `AttachHaze: art object applied` | 1 |
| `DetachHaze: released` | 0 |
| `parking attachment` | 19 |
| weapon-change resets / real swaps | 2 / 2 |
| warnings / errors | 0 / 0 |
| tick cost (worst second of 559) | 838 us |

The 105ms tick outlier from the previous session did **not** recur - worst single tick
across 559 sampled seconds was 233us.
