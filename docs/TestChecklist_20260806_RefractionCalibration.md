# Refraction Calibration Test - 2026-08-06

Build: `dist\GunHeatHaze-0.3.1-refraction-calibration.zip`

## What changed

Only the refraction magnitude. Nothing structural.

| Item | Before | After |
| --- | --- | --- |
| `GunHeatRefractionOnlyStrong.nif` baked Refraction Strength | `0.8000` | `0.2000` |
| `[ProjectileEmitter] fRefractionMaxStrength` | `0.80` | `0.20` |

`0.20` is the vanilla Minigun / FlameJet value. The full vanilla range for this
effect is `0.03` (ambient mirage) to `0.20` - see `docs\Audit_and_Roadmap_20260806.md`.

Delivery, scroll axis, fade curve and the projectile carrier are all untouched.

## Before installing - the game folder has a stale conflicting file

```text
Data/Meshes/GunHeatHaze/GunHeatRefractionOnlyStrong.nif
```

That loose file is the **old 0.80 mesh** (verified 2026-08-06). If it wins over the
new deployment the test is invalid and will look identical to the last run.

Also stale in the game folder:

```text
Data\Scripts\GunHeat\GunHeatController.pex
Data\Scripts\GunHeat\GunHeatNative.pex
Data\Scripts\GunHeat\PlayerAlias.pex
```

Meanwhile `GunHeatHaze.esp`, `GunHeat.dll` and `GunHeat.ini` are **not** present in the
game folder at all, and `GunHeatHaze.esp` is **not** in `plugins.txt`. The mod is
currently not installed - only leftovers from an old direct deploy remain.

Remove the leftovers (or let the new install overwrite them), install the zip, then
confirm `*GunHeatHaze.esp` appears in `plugins.txt`.

## Test setup

1. Launch through F4SE (`1.10.163` / `0.6.23`).
2. First person, vanilla Assault Rifle, unsuppressed. Not the Minigun - it has its own
   native heat effect and is not a clean comparison.
3. Stand facing a well-lit wall with visible detail behind the muzzle. Refraction is
   invisible against flat sky or darkness.
4. Fire a sustained burst.

## What this test is and is not judging

**Judging:** how strong the distortion is, and whether the `SmokeVapor01Tile_n` normal
map reads as heat rather than as warped glass.

**Not judging** - these are known and unaddressed by this build:

- The shimmer sits in world space and will visibly separate from the muzzle when you
  turn or walk. It is carried by projectiles, not attached to the gun.
- It will still pop as individual puffs are born and die.
- It scrolls on U only, where vanilla scrolls V. Expect lateral sliding rather than
  heat rising off the barrel.

## Sweeping without a rebuild

`Config::Load()` runs on both `kGameLoaded` and `kPostLoadGame`, so
`Data\F4SE\Plugins\GunHeat.ini` is re-read **every time a save is loaded**. To try
another value: alt-tab, edit `fRefractionMaxStrength`, load a save, fire again.

Worth sweeping in one session:

```text
0.05   ambient-mirage subtle
0.10   halfway
0.20   vanilla Minigun / FlameJet  (this build)
0.35   deliberately over vanilla, to bracket the answer
```

Note the baked NIF value stays at `0.20` during a sweep; that only matters for the
first frame before the runtime driver takes over, so it does not affect the comparison.

## Outcome to report back

- Which value looked closest to the Minigun barrel.
- Whether the distortion pattern reads as heat at all, independent of strength.
- Whether it is too large / too small on screen (that is card scale, not refraction).

If the look is right at some value, the next step is the delivery rewrite in
`docs\Audit_and_Roadmap_20260806.md` section 4, Route A. If the pattern itself is
wrong at every strength, the scroll axis (U -> V) and the billboard are the next dials,
before any rewrite.
