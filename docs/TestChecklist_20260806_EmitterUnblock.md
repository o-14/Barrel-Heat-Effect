# Emitter Unblock Test - 2026-08-06

Build: `dist\GunHeatHaze-0.3.2-emitter-unblock.zip`

Supersedes `GunHeatHaze-0.3.1-refraction-calibration.zip`, which could not render
anything. Install this one instead.

## Why 0.3.1 showed nothing

`GunHeat.log` from that session: **1030 shots recorded, 0 projectiles launched.**
Every shot ended in `ProjectileEmitter: skipped; strength 0 below minimum 0.05`, and
`AttachHaze` was never called once. Two independent blockers.

### Blocker 1 - heat could never reach its own threshold

Heat decays at `1 / fadeOutSeconds`, and `GetCurrentFadeOutSeconds()` returns
`fMinFadeOutSeconds + (fMax - fMin) * peakHeat`. Because `peakHeat` never got above
one shot's worth, `fadeOutSeconds` stayed at ~2.16 s, so **a cold barrel cooled at
~0.46 heat/sec** - the system cooled fastest exactly when it was trying to start.

Against `fHeatPerShot=0.035` scaled by caliber (0.023-0.032 per shot), break-even was
~59 ms between shots, i.e. **~1023 RPM just to hold steady**. The Assault Rifle is
around 270 RPM. Heat asymptoted near 0.03 and `fMinHeatToShow=0.18` was unreachable.

### Blocker 2 - a disabled attach path also disabled the emitter

`StartHaze()` treated `GunHeatNative.AttachHaze()` returning false as fatal and called
`StopHaze()`, which zeroes `heat`, `visibleStrength` and `peakHeat`. With
`[Haze] bAttachEnabled=0` - the crash-safe setting in place since June -
`HazeManager::Attach` returns false at the config gate. So even if heat had crossed the
threshold, the cycle would have reset instantly. The projectile emitter is fed from
`SetHazeStrength`, which only ever received 0. No INI value works around this.

**The refraction calibration never ran.** 0.20 vs 0.80 has still not been on screen.

## What changed in 0.3.2

**`GunHeatController.psc`** (recompiled with the CK Papyrus compiler, 2.8.0.4):

- `StartHaze()` no longer aborts when `AttachHaze` returns false. The scene-graph path
  is optional; the emitter is the renderer when it is disabled.
- `DebugLog()` now calls the native `Log()` directly. The old
  `GetIniFloat("Debug", "bDebugLogging") > 0.0` guard was returning 0 at runtime, which
  is why no Papyrus-side line ever reached the log despite `bDebugLogging=1`. `Log()`
  applies the same check natively using the flag the DLL actually read.

**`GunHeat.ini`** heat curve:

| Key | Before | After |
| --- | --- | --- |
| `fHeatPerShot` | `0.035` | `0.085` |
| `fMinFadeOutSeconds` | `2.0` | `8.0` |
| `fMaxFadeOutSeconds` | `8.0` | `14.0` |
| `fFadeInSeconds` | `1.40` | `0.80` |

Cold-state decay drops from 0.462 to 0.125 heat/sec. Predicted behaviour:

| Weapon | Shots to first visible haze |
| --- | --- |
| Assault Rifle (dmg 25, ~4.5/s) | ~4 |
| 10mm (dmg 18, ~3/s) | ~7 |
| weap `0015B043` (dmg 13, ~3/s) | ~13 |
| Any weapon at 1 shot/sec | never - by design |

Refraction stays at `0.20` from 0.3.1. The DLL, ESP and mesh are unchanged.

## Test

1. Install, confirm `*GunHeatHaze.esp` in `plugins.txt`, and confirm the stale
   `Data\Meshes\GunHeatHaze\GunHeatRefractionOnlyStrong.nif` in the game folder is
   overwritten - it is the old 0.80 mesh and would invalidate the strength reading.
2. First person, facing a well-lit detailed wall.
3. Hold the trigger on the Assault Rifle for ~2 seconds.

## Reading the log first, before judging the look

`Documents\My Games\Fallout4\F4SE\GunHeat.log` should now contain lines that were
entirely absent last time:

```text
Papyrus: weaponFire: weapon=..., heat=..., visible=..., strength=...
Papyrus: StartHaze: AttachHaze returned false; continuing emitter-only heat cycle
ProjectileEmitter: launched copy=1/1, form=..., handle=<nonzero>
ProjectileEmitter: controller sequence mSprayStart activated=true
ProjectileEmitter: runtime faded ... refraction=... controllerStarted=true
```

- If `weaponFire:` lines appear but `heat=` never climbs past ~0.18, the curve still
  needs more `fHeatPerShot`.
- If `launched copy` appears with `handle=0`, the projectile form is not resolving.
- If `launched copy` appears with a nonzero handle and you still see nothing, then the
  problem really is visual - strength, scale, or placement - and that is the reading we
  wanted from 0.3.1.

Note `DebugLog` is now unguarded and the heat timer runs at 20 Hz, so the log grows
quickly. Set `[Debug] bDebugLogging=0` once diagnosis is done.

## Still expected to look wrong

Unchanged from 0.3.1 and not addressed by this build: the shimmer is carried by
world-space projectiles so it separates from the muzzle when you turn, individual puffs
pop, and the texture scrolls on U instead of V.

## Housekeeping spotted, not changed

`[Haze] sHazeArtObject` still points at `GunHeatHaze\AssaultRifleHeatMuzzle.nif` and
`sAttachNode=Camera` - both stale diagnostic leftovers. They are inert while
`bAttachEnabled=0`, but they show up in the config line at the top of every log and are
misleading when reading it.
