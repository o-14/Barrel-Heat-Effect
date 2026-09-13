# Edge fade and movement smear - 2026-08-11

Build: `dist\GunHeatHaze-0.8.0-edgefade-smear.zip`

## Restore point

Before any of this, the working 0.7.1 state was snapshotted:

```text
Backups\GunHeatHaze-v0.7.1-WORKING-snapshot-20260811.zip   (109 files + RESTORE.md)
dist\GunHeatHaze-0.7.1-defaults.zip                        (ready-made installable)
```

The snapshot holds `Data`, the plugin source, `tools` and `docs`, so it can rebuild from
scratch. The `dist` zip can simply be reinstalled without rebuilding. Revert instructions
are in `RESTORE.md` inside the snapshot.

## 1. Edge fade

The hard rim came from refraction strength being uniform right up to the geometry
boundary and then stopping. Two useful things turned up while investigating:

**The card already carried authored vertex alpha.** Saugus's mesh ships 18 vertices at
alpha 0 and 73 at 255 - a rough silhouette ramp Bethesda authored - but
`Vertex_Alpha` was never set in the shader flags, so it was ignored.

**Vanilla's closest analogue does set it.** `FlameJetMuzzleFlash.nif`'s
`BaseRefractionMesh003` - small, viewed close up, refraction-only, exactly our case - has
an identical vertex descriptor (`VERTEX, UV, NORMAL, TANGENT, COLORS`, stride 24) and
flags `0x80418009`, which includes `Vertex_Alpha`.

So `tools\apply_vertex_alpha_falloff.py` now writes a smooth falloff and enables the flag:

```text
Shader Flags 1  0x80408201 -> 0x80408209   (+Vertex_Alpha)

alpha 224-255:  55 verts    (interior, solid)
alpha 160-191:   6 verts
alpha 128-159:  12 verts
alpha   0- 31:  18 verts    (rim, gone)
```

The falloff uses **normalised elliptical distance**, not raw radius. The card is about
40 x 82 local units, so a plain radius would treat a vertex at the left edge (r~20) as
interior while fading one at the top (r~41) to nothing - leaving the left and right edges
exactly as hard as before. Normalising each axis by its own half-extent fades all edges
evenly.

Texture-space falloff was rejected: the V offset scrolls a full tile every 1.667 s, so
anything baked into the texture would slide around with it. Vertex alpha is fixed to the
geometry.

**The one unknown:** whether FO4's lighting-shader refraction path actually modulates by
vertex alpha. I could not settle this in Ghidra, because refraction is applied in the
compiled HLSL shader rather than in the exe - the C++ only feeds constants. The flamer
card is strong circumstantial evidence, not proof. If the edges look unchanged in game,
that is the answer, and the fallback is curving the card so its rim turns away from the
viewer.

Tunable without a rebuild of anything but the mesh:

```bash
python tools/apply_vertex_alpha_falloff.py Data/Meshes/GunHeatHaze/GunHeatBarrelRefractionCard.nif --shape Cylinder026 --inner 0.30
```

Lower `--inner` starts the fade closer to the centre (softer, smaller solid core).

## 2. Movement smear

The card is rigidly parented to the muzzle node, so it cannot lag on its own. The DLL now
samples the muzzle's world position each heat tick, converts the resulting velocity into
the muzzle node's local frame with `world.rotate.Transpose()`, and offsets the card
backwards along that motion:

```text
target = -(localVelocity) * fSmearGain     clamped to fSmearMaxOffset
smear  = exponential approach to target, time constant fSmearSmoothing
local.translate = base offsets + smear
```

Sanity guards: samples with a gap outside 1 ms - 500 ms are discarded, so loading screens,
menus and pauses cannot register as one enormous jump and fling the card away.

| Setting | Default | What it does |
| --- | --- | --- |
| `bSmearEnabled` | 1 | on/off |
| `fSmearGain` | 0.015 | offset units per unit/sec of muzzle speed |
| `fSmearMaxOffset` | 6.0 | hard cap, so a fast turn cannot throw it off the barrel |
| `fSmearSmoothing` | 0.10 | settle time |

At a walk (~300 units/sec) that is roughly 4.5 units of lag against a 20-unit-tall card;
a fast turn saturates at the 6-unit cap.

Note this is smear, not a trail of discrete puffs. It was the option least likely to
regress what already works - stamped puffs would reintroduce the per-object popping that
took two builds to remove. If the smear reads as too subtle, raising `fSmearGain` is the
first thing to try before considering the puff approach.

## MCM

Three new controls in a new **Movement** section: movement smear, smear amount, smear
limit. Panel is now 17 controls across 7 sections, every one carrying its default in the
help text.

## Test

1. Install. `GunHeat.dll` is **765952** bytes.
2. **Edges:** get the barrel hot and ramp to a high value - the rim should fade out rather
   than stopping at a visible boundary.
3. **Smear:** with the effect active, swing the weapon side to side and walk - the heat
   should lag behind the barrel slightly and settle when you stop.
