# Heat Puff Projectile Prototype

Date: 2026-06-23

Goal:

- Create a harmless, short-lived, engine-owned projectile record that can later be spawned by the F4SE plugin as the heat haze visual.

## Added ESP Record

Plugin:

- `Data\GunHeatHaze.esp`

New projectile:

- FormID: `01000801`
- Editor ID: `GunHeatHeatPuffProjectile`
- Source clone: `AssaultRifleProjectile` / `PROJ:0000481F`
- Model: `GunHeatHaze\AssaultRifleHeatMuzzle.nif`

Neutralized projectile settings:

- Type: cloned beam type
- Flags: `0x00000200`
  - keeps pass-through behavior only
  - removes muzzle flash, explosion, alt trigger, and vanilla penetration flags
- Speed: `90`
- Range: `120`
- Light: `NULL`
- Muzzle flash light: `NULL`
- Explosion: `NULL`
- Sound: `NULL`
- Muzzle flash duration: `0`
- Fade duration: `0.25`
- Impact force: `0`
- Collision radius: `0.01`
- Lifetime: `0.35`
- Collision layer: `NULL`
- Tracer frequency: `0`
- VATS projectile: `NULL`

The record is intentionally safe to load, but it is not yet spawned by the runtime.

## Tooling

Added:

- `tools\build_heat_puff_projectile_esp.py`

The builder preserves existing `PROJ` records in the ESP and adds/replaces `GunHeatHeatPuffProjectile`.

Command used:

```powershell
python tools\build_heat_puff_projectile_esp.py --esp Data\GunHeatHaze.esp
```

## Runtime Config

Added:

```ini
[ProjectileEmitter]
bEnabled=0
sHeatProjectileFormID=01000801
```

The emitter is disabled until the native launch function is identified and hooked safely.

## Native Plugin Changes

`Config` now parses:

- `ProjectileEmitter.bEnabled`
- `ProjectileEmitter.sHeatProjectileFormID`

The config log includes:

- `projectileEmitterEnabled`
- `heatProjectileFormID`

## Live Install

Copied live:

- `Data/GunHeatHaze.esp`
- `Data/F4SE/Plugins/GunHeat.ini`
- `Data/F4SE/Plugins/GunHeat.dll`
- `Data/F4SE/Plugins/GunHeat.pdb`

## Engine Launch Function

Verified old-gen Fallout 4 `1.10.163` relocation for:

```cpp
RE::ProjectileHandle(RE::ProjectileLaunchData const&)
```

- Address Library ID: `1452334`
- Hex ID: `0x16292E`
- Runtime offset from `version-1-10-163-0.bin`: `0xFCA260`


## Next Step

Use this relocation behind `ProjectileEmitter.bEnabled` to spawn `GunHeatHeatPuffProjectile` from the player's current fire location after heat crosses the threshold.
