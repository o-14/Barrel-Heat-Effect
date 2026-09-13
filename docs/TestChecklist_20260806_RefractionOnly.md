# Refraction-Only / Harmless Carrier Test - 2026-08-06

Build: `dist\GunHeatHaze-0.3.3-refraction-only-harmless.zip`

## What the 0.3.2 test proved

Good news first: **the heat model and fade timing work.** Smooth onset, realistic
pulsing, correct build-up over consecutive shots. That part of the design is done and
should carry over unchanged to any future delivery method.

Two defects, both now fixed.

### Defect 1 - the asset was rendering as flame, not refraction

`GunHeatRefractionOnlyStrong.nif` is derived from Bethesda's flamethrower spray. It
still contained **four `m_Flames:0` shapes** next to the one `m_Refraction:0` card we
want. An earlier pass had zeroed only their bounding-sphere *radius*, which does not
stop them drawing - the vertex data was fully intact, so the engine drew the complete
fireball. That is what the screenshots show.

Fixed by zeroing each flame vertex **position**, making every triangle zero-area so the
rasterizer discards it. Block sizes and all reference indices are byte-identical, so
nothing else in the file shifted. New tool: `tools\collapse_nif_shape_geometry.py`.

Remaining geometry: `m_Refraction:0`, 86 verts, bound radius 15.36, on the
`BSLightingShaderProperty` with `Refraction | Fire_Refraction` and Refraction
Strength `0.20`.

### Defect 2 - the carrier projectile was doing real damage

`ProjectileEmitter::Emit` was populating `ProjectileLaunchData` with the real weapon and
ammo:

```cpp
.fromWeapon = RE::BGSObjectInstanceT<RE::TESObjectWEAP>(weapon, nullptr),
.fromAmmo   = shooter->GetCurrentAmmo(equipIndex),
```

So the "harmless visual carrier" inherited the firing weapon's damage **and** its impact
data set - hence NPC damage and bullet decals on walls. The `PROJ` record itself is
clean (no explosion, no impact data, no collision layer), so the record was never the
source.

Both are now passed as null. Caliber scaling is unaffected - heat per shot is computed
separately through `GunHeatNative.GetHeatPerShot(weapon)` on the Papyrus side, which
still receives the real weapon.

DLL rebuilt: `775168` bytes (previous build was `775680`). Use that to confirm the new
binary actually deployed.

## Test

1. Install; confirm the deployed `GunHeat.dll` is **775168 bytes**.
2. First person, well-lit detailed wall behind the muzzle.
3. Fire a sustained burst, ~10-20 rounds.

Check, in order:

- **No flame.** If any fire is still visible, the old mesh is winning the deployment.
- **No damage, no decals.** Fire at a wall and at an enemy. Nothing should be marked or
  hurt by the effect.
- **Then judge the refraction** - is there a visible heat-shimmer distortion of the wall
  behind the muzzle, and does `0.20` read as heat or as warped glass?

## Sweeping strength

`fRefractionMaxStrength` is re-read on every save load. Alt-tab, edit, load a save:

```text
0.10   subtle
0.20   vanilla Minigun / FlameJet  (this build)
0.35   over vanilla
0.60   deliberately excessive, to confirm it is rendering at all
```

If nothing is visible even at `0.60`, the refraction card is not rendering and the
problem is delivery, not tuning.

## Still expected to look wrong

The carrier is still a world-space projectile, so the shimmer will separate from the
muzzle when you turn or walk, and the texture still scrolls on U rather than V. Those
are inherent to the prototype and are what the Route A rewrite in
`docs\Audit_and_Roadmap_20260806.md` replaces.

**This build is a look test, not a candidate shipping build.** Even with damage removed,
spawning 4-7 engine projectiles per second as a rendering primitive is not something to
ship - it churns engine objects and can never stay attached to the barrel.
