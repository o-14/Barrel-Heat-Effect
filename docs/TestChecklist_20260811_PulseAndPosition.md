# Pop fix, position, pulsing - 2026-08-11

Build: `dist\GunHeatHaze-0.7.0-pulse-and-position.zip`

## MCM verification: it worked

`Data\MCM\Settings\GunHeat.ini` exists with your edits, and the DLL applied them 112
times during the session. The last config line in the log reads
`hazeRefractionRange=(0, 0.1)` - the panel wrote it, the overlay picked it up mid-session
without a restart, and `heatPerShot` moved `0.0658 -> 0.125 -> 0.19365` as you tuned.

## The "puff" bug - root cause

Two things compounding, and the log confirms both.

**1. The card had refraction baked into the mesh.** The NIF carried
`Refraction Strength = 0.25`. `BGSArtObjectCloneTask` builds the art object
asynchronously, so between the engine finishing the clone and our first `SetHazeStrength`
reaching it, the card rendered at that **full baked 0.25** no matter what the heat curve
said. The log's `art object 3D not ready yet` lines are exactly that window.

That is why it only ever happened *outside* an established cycle, exactly as you
observed: a new attach is the only time a fresh clone appears. Mid-cycle there is no new
attach, so no pop.

Vanilla does the opposite - `MinigunBarrel.nif` bakes `0.0000` and lets its controllers
drive the value from nothing. The card now does the same:

```text
before:  refractionStrength = 0.2500
after:   refractionStrength = 0.0000
```

A freshly attached card is now invisible until the heat curve drives it.

**2. Your `fHeatPerShot=0.25` makes one shot cross the threshold.** With the 10mm caliber
multiplier of 0.7746 that is `0.194` per shot against `fMinHeatToShow=0.18` - so a single
shot legitimately starts a full cycle, which then decays back under the threshold almost
immediately. That is a tuning consequence rather than a bug, and with the baked value now
zero it ramps and falls smoothly instead of popping.

If you want single shots to never trigger, keep `heatPerShot x caliber` under the
threshold: for the 10mm that means `fHeatPerShot` below about **0.23**. At `0.20` it takes
two shots.

## Position and size

The card is now shorter and gets lifted off the barrel at runtime.

| | before | after |
| --- | --- | --- |
| on-screen size (node scale 0.25) | 10.1 x 26.0 | **10.1 x 20.6** |
| position | centred on the muzzle | raised `fArtOffsetUp` units |

The lift is a **runtime** transform on the art object inside the muzzle node's space
(`Y` forward along the barrel, `Z` up), reapplied every tick because the engine rewrites
that transform as the weapon moves. Being runtime means it is INI/MCM tunable with no
mesh rebuild:

```ini
fArtOffsetUp=10.0        ; card is ~20.6 tall, so 10 puts its base at the muzzle
fArtOffsetForward=0.0
fArtOffsetSide=0.0
```

**If it moves the wrong way in game, negate `fArtOffsetUp`.** I could not verify the sign
of the muzzle node's up axis from the binary, so this is the one thing here that is an
assumption rather than a confirmed fact. It is a slider, not a rebuild.

## Experimental per-shot pulsing

Off by default. `[Haze] bPulseEnabled=1`, or the **Experimental** section in MCM.

Each shot fired into an **already-running** cycle restarts a bump that decays
exponentially and is added on top of the smooth curve:

```text
refraction = lerp(min, max, heat) + pulseStrength * exp(-age / decay) * heat
```

Two deliberate choices:

- **Scaled by current heat**, so it does nothing on a cold barrel and is strongest on a
  hot one - it reads as an existing plume being disturbed, not a flash from nothing.
- **Never fires on the shot that starts a cycle**, or it would punch in at the exact
  moment the effect is supposed to be ramping up from zero - which is the pop we just
  removed.

Tuning: `fPulseStrength` (0.06) is bump size; `fPulseDecaySeconds` (0.30) is how fast it
fades. Short values feel like sharp puffs, longer values blur consecutive shots into a
rolling surge.

## Other changes

- **Heat intensity default is now 0.10** (was 0.20) in `GunHeat.ini`, the MCM default and
  the DLL fallback. Your stored MCM value is already 0.1, so nothing changes for you.
- New MCM controls: height above barrel, distance ahead of muzzle, per-shot pulsing,
  pulse strength, pulse decay. 14 controls total.

## Test

1. Install. `GunHeat.dll` is **762880** bytes.
2. **Pop:** fire one shot on a cold barrel, and a 5-7 round burst. Neither should snap in.
3. **Position:** during a normal build-up, the plume should sit above the muzzle and read
   as rising, not wrapped around it. Adjust `fArtOffsetUp` in MCM if needed.
4. **Pulsing:** turn it on, get the barrel hot, then keep firing - the plume should kick
   with each shot.
