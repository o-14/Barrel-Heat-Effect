# Add-On Node Detach Test - 2026-08-06

Build: `dist\GunHeatHaze-0.3.4-addon-nodes-detached.zip`

## Why 0.3.3 still showed flame

The 0.3.3 mesh was verified correct **in the game folder** - all four `m_Flames`
BSTriShapes had zeroed vertex positions, the DLL was the new 775168-byte build, and the
INI and scripts were current. The fire rendered anyway.

Because the fire was never geometry in our file.

`GunHeatRefractionOnlyStrong.nif` contains two `BSValueNode` blocks, `AddOnNode196` and
`AddOnNode212`, as direct children of the root, each with **zero children of its own**.
A `BSValueNode` is an add-on node: at load time the engine looks up the `ADDN` record
whose Node Index matches the stored value - 196 and 212 here - and attaches that
record's model at that point in the graph. The flamethrower's fire comes in through
those two indices. No amount of editing the geometry that *is* in the file could remove
it.

## What changed

Both add-on nodes are now detached from the root by nulling their child references
(slots 2 and 4 set to `-1`). The node is no longer in the scene graph, so the engine has
nothing to attach ADDN content to. Block sizes and every other reference are
byte-identical - only two int32 slots changed. New tool:
`tools\detach_nif_child_nodes.py`.

Root children after the change:

```text
FlameThrowerProjectileSprayShort01
├── MoverLight -> LagBone
├── BillboardHelper -> m_Flames:0          (geometry already degenerate)
├── NULL                                   (was AddOnNode196)
├── m_Refraction:0                         <- the only thing that should draw
├── NULL                                   (was AddOnNode212)
├── BillboardHelper@#0 -> m_Flames:0@#1    (degenerate)
├── BillboardHelper@#2 -> m_Flames:0@#3    (degenerate)
└── BillboardHelper@#4 -> m_Flames:0@#5    (degenerate)
```

Only the two add-on nodes changed. The flame billboards were left attached on purpose:
their geometry is provably degenerate, and detaching them too could break the
`mSprayStart` sequence that drives the refraction card's UV scroll. One variable.

Nothing else changed - same DLL, ESP, INI and scripts as 0.3.3.

## Test

1. Install. Confirm `GunHeat.dll` is 775168 bytes and the mesh is 18346 bytes.
2. Fire a sustained burst at a well-lit detailed wall.

In order:

- **No fire at all.** If fire persists, the add-on nodes were not the source and the
  remaining suspect is the `mSprayStart` controller sequence re-adding something.
- **Then judge the refraction** - is there a visible shimmer distorting the wall, and
  does `0.20` read as heat?
- Sweep `fRefractionMaxStrength` (0.10 / 0.20 / 0.35 / 0.60) by editing the INI and
  loading a save. If nothing is visible even at 0.60, the card is not rendering.

## Recommendation regardless of outcome

This asset has now produced three separate hidden engine bindings:

1. `BSBehaviorGraphExtraData` -> `ProjectileSprayRange.hkx`, the likely cause of the
   June scene-graph attach crashes.
2. `BSConnectPoint::Parents`, weapon attachment metadata.
3. `BSValueNode` add-on nodes pulling in flame content by ADDN index.

It is Bethesda's flamethrower spray with a refraction card buried inside, and every
attempt to strip it has uncovered another binding. **It should be replaced with a
purpose-built asset**, per section 5 of `docs\Audit_and_Roadmap_20260806.md` - a
minimal `NiNode -> NiBillboardNode -> BSTriShape` with a `BSLightingShaderProperty` in
refraction mode and `SmokeVapor01Tile_n.dds` in both texture slots. That asset is needed
for the Route A rewrite as well, so it is not throwaway work either way.

You have also now seen the carrier's core defect directly: the effect stays where it was
spawned and does not follow the weapon. That is inherent to using world-space
projectiles and is exactly what Route A fixes by attaching an engine-owned art object to
the weapon's `fireNode`.

The value of this test is narrow and specific: confirm the refraction card renders and
that `0.20` looks like heat. Once that is known, the remaining work is the authored
asset plus the delivery rewrite.
