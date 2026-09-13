# Vanilla Projectile Effect Candidates

## Current test

`GunHeatHeatPuffProjectile` (`01000801`) is now cloned from vanilla `FlamerProjectileStreamVaporizer` (`001C5AB5`) and points to a custom NIF:

- Model: `GunHeatHaze\HeatDistortionFlamerRefractionOnly.nif`
- Source clone: `Effects\FlameThrowerProjectileSprayVaporizer01.nif`
- NifSkope edit: removed the visible `m_Flames:0` / `m_Flames:0@#1` `BSTriShape` branches.
- Kept: `m_Refraction:0` and the surrounding flame-stream helper/controller structure.
- Purpose: keep the engine-managed flame-stream projectile rendering path while hiding the visible fire geometry.

The old string-table names can still appear in raw byte scans after NifSkope saves, but the visible block tree no longer contains the flame shapes.

## FlameJet muzzle-flash strip candidate

The stronger strip candidate is the 10:39 working muzzle-flash asset:

- Source: `Effects\FlameJetMuzzleFlash.nif`
- Clone: `Data\Meshes\GunHeatHaze\FlameJetMuzzleFlashRefractionOnly.nif`
- NifSkope edit: removed `BaseThrusterMesh005`, which also removed the fire gradient reference.
- Kept: `BaseRefractionMesh003` / `BaseRefractionMesh003:0`, `AddOnNode45`, and `textures\effects\SmokeVapor01Tile*.dds`.
- Saved size: `2126` bytes, down from the original `8585` bytes.

This is probably a better next test than deleting `m_Flames` from a flamer projectile spray, because the active 10:39 ESP already proves `Effects\FlameJetMuzzleFlash.nif` renders from the current muzzle-flash path. The next controlled ESP test should leave `MODL` as `Effects\FlameJetProjectile.nif` and replace only `NAM1` with `GunHeatHaze\FlameJetMuzzleFlashRefractionOnly.nif`.

## Previous test

`GunHeatHeatPuffProjectile` (`01000801`) is now cloned from vanilla `FlamerProjectileStreamVaporizer` (`001C5AB5`).

- Model: `Effects\FlameThrowerProjectileSprayVaporizer01.nif`
- Projectile flags: `0x00080200`
- Muzzle flash model: removed
- Light: removed
- Explosion: removed
- Collision radius: `0.01`
- Lifetime: `0.70`
- Range: `192.0`

The important discovery is that the flame projectile type is encoded in the projectile flag field. Reducing the flags to only `0x00000200` removes the engine path that renders the spray mesh, which likely caused the previous invisible test.

## Strong candidates

- `001C5AB5 FlamerProjectileStreamVaporizer`
  - `Effects\FlameThrowerProjectileSprayVaporizer01.nif`
  - Best first test because it is a short flame-type projectile and already renders a vapor/spray mesh from `MODL`.

- `001C5AB6 FlamerProjectileStreamMedium`
  - `Effects\FlameThrowerProjectileSprayMedium01.nif`
  - Similar to the vaporizer, but likely more flame-colored and more obvious.

- `000B45EB CryolatorStream`
  - `Effects\CryolatorProjectileSprayMedium01.nif`
  - Good fallback if the flamer visuals are too fiery. It is also flame-type internally, but visually cold/fog-like.

- `001B637B PlasmaFlamerProjectileStream`
  - `Effects\PlasmaThrowerProjectileSpray01.nif`
  - Useful as a renderer test, but visually too green/energy-like for the final mod.

## Weak candidates

- `Effects\SaugusSmokeMirage.nif`, `Effects\GlowingSeaMirageEffect01.nif`, and other ambient mirage/smoke meshes
  - Promising visually, but not seen in vanilla `PROJ` records as projectile `MODL`, so they are less likely to work through the native projectile launch path without additional wrapping.

- `Effects\MPSMinigunMuzzleFlash.nif`
  - This appears to be part of the minigun muzzle wrapper behavior rather than a standalone projectile model. Direct use in our earlier tests did not render reliably.

## Next conversion route

If the vaporizer test is visible, clone `FlameThrowerProjectileSprayVaporizer01.nif` into `Data\Meshes\GunHeatHaze\` and edit its particle textures/colors toward clear heat shimmer. Keep the cloned projectile record based on `001C5AB5` so the engine still treats the visual as a flame-type spray.
