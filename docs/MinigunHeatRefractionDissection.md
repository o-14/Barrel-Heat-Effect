# Minigun Heat Refraction Dissection

## Restored baseline

The live ESP has been restored to the known-visible FlameJet diagnostic state.

- `GunHeatHeatPuffProjectile` (`01000801`)
- `MODL`: `Effects\FlameJetProjectile.nif`
- `NAM1`: `Effects\FlameJetMuzzleFlash.nif`
- DNAM flags: `0x40a0c`
- Muzzle flash light: `00004B29`
- Muzzle flash duration: `0.5`
- Lifetime: `0.8`

The F4SE DLL weapon-cache fix should stay in place. That change is independent from the visual asset test and is what lets `ProjectileLaunchData.fromWeapon` use the weapon that fired.

## Minigun records

The vanilla minigun projectile is `0003ADFB MiniGunProjectile`.

- Projectile `MODL`: `Effects\DefaultTracerBeam.nif`
- Projectile type: beam
- Muzzle flash `NAM1`: `Weapons\Minigun\MiniGunMuzzeFlash.nif`

This means the minigun's special muzzle visuals are not coming from the projectile model. They are coming from the `NAM1` muzzle-flash wrapper.

## Wrong heat target

`Weapons\Minigun\MiniGunMuzzeFlash.nif` contains:

- Root: `MiniGunMuzzeFlash`
- Mesh: `MuzzleFlahMesh:0`
- Texture: `textures\Effects\FireWallTile_d.dds`
- Gradient: `textures\Effects\Gradients\FireSharpGrad.dds`

This is the card-like muzzle visual we already saw. It is not the persistent barrel heat distortion.

## Strong heat target

`Weapons\Minigun\MinigunBarrel.nif` contains two distinct visual branches:

- `Minigun_Barrel` / `Minigun_Barrel:0`
  - Visible metal barrel geometry.
  - Uses `materials\Weapons\Minigun\MinigunBarrel.BGSM`.
  - This is the part that caused the visual bug where the minigun barrel appeared on another weapon.

- `BaseRefractionMesh` / `BaseRefractionMesh:0`
  - The likely heat diffraction geometry.
  - Uses `textures\Effects\SmokeVapor01Tile_n.dds`.
  - Appears under the same barrel root and is separate from the metal barrel mesh.

This is the branch to isolate. We should not use the full `MinigunBarrel.nif` as an effect asset because it includes the metal barrel geometry.

## Secondary asset

`Weapons\Minigun\GunLgOverheatMPSLight.nif` contains:

- Root: `GunLgOverheatMPSLight`
- Light: `OverheatLight`
- Controllers: radius, dimmer, color

The dumped WEAP/PROJ/OMOD records do not directly reference this file. It looks like a supporting overheat light, not the main visible heat distortion mesh.

## Recommended next asset step

Use NifSkope to create a trimmed copy of `Weapons\Minigun\MinigunBarrel.nif`:

1. Save as `Data\Meshes\GunHeatHaze\MinigunBarrelRefractionOnly.nif`.
2. Keep the root structure needed by the file.
3. Keep `BaseRefractionMesh` and `BaseRefractionMesh:0`.
4. Keep relevant connect points such as `P-Muzzle` only if NifSkope shows them as parents for the refraction branch.
5. Remove or hide `Minigun_Barrel` and `Minigun_Barrel:0`.
6. Remove references to `materials\Weapons\Minigun\MinigunBarrel.BGSM` and minigun barrel color/specular textures if they are orphaned after removing the metal barrel.
7. Preserve the refraction texture reference to `textures\Effects\SmokeVapor01Tile_n.dds`.

Once that trimmed asset exists, test it through the existing attach path or a muzzle-flash wrapper path. It should not be tested as a fake projectile; the visual we want is a local barrel-attached refraction mesh.
