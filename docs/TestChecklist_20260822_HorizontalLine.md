# Horizontal line on puffs - 2026-08-22

Build: `dist\GunHeatHaze-0.11.3-scroll-rise.zip`

## What I checked

**Ruled out - `ApplySize` corrupting the card's orientation.** `ApplySize` overwrites the
geometry's `local.rotate` with a diagonal scale matrix. If the card had shipped with a
real rotation there, replacing it would have tilted the card and could show it edge-on as
a line. It did not:

```text
[03] BSTriShape  Cylinder026:0   scale=1.0000  rotIdentity=True
```

The 90-degree rotation that stands the disc upright lives on the parent
`NiBillboardNode`, which `ApplySize` never touches. So that is safe.

**Ruled out - a texture tiling seam.** A non-seamless V wrap would also draw a horizontal
line travelling upward, but at a fixed rhythm of one per scroll cycle, firing or not. You
tied it to puffs, which points away from this.

## What it is

`fPuffRise` translated the **whole card** upward on each puff:

```cpp
art3D->local.translate.z = ArtOffsetUp() + smear.z + puff.rise;
```

That moves the card's silhouette across the screen. If the card's edges were soft it would
be invisible; a hard edge sweeping upward is exactly a faint horizontal line moving up on
every puff.

And the edges are almost certainly hard. The mesh data says they should not be - every
vertex at the vertical extremes carries alpha 0:

```text
lowest 4 by Y:  (-41.2, 0) (-39.0, 0) (-38.4, 0) (-32.1, 0)
highest 4 by Y: ( 32.1, 0) ( 38.4, 0) ( 39.0, 0) ( 41.2, 0)
alpha range: 0 .. 255
```

So the falloff written in 0.8.0 is present and correct in the file. If the shader were
honouring it, translating the card could not expose an edge. Seeing a hard edge is
therefore evidence that **Fallout 4's refraction path ignores vertex alpha** - the
question left open in 0.8.0, which I could not settle in Ghidra because refraction is
applied in the compiled HLSL rather than in the exe.

## Fix

The rise now happens in **texture space** instead of geometry space. The pattern scrolls
upward inside a stationary card, so nothing with an edge ever moves:

- `fPuffRise` now defaults to **0** (the slider remains, for anyone who wants real
  geometry movement and can live with the edge).
- New `fPuffScroll` (0.15) - each puff pushes the heat pattern up within the card.
- New `fScrollTilesPerSecond` (0.6) - base scroll rate, now owned by the DLL rather than
  the NIF's V-offset controller. 0.6 tiles/sec is the vanilla Minigun's rate, one full
  tile per 1.667 s.
- `bDriveScroll=0` hands the scroll back to the NIF controller if this misbehaves.

Taking the scroll into the DLL is what makes a puff able to add to it at all, and it has a
side benefit: scroll rate is now configurable rather than baked into the mesh.

## Confidence

The mechanism is inferred from the mesh data plus your description, not observed. The
decisive test is one slider: with **Puff rise** at 0 the line should be gone. If it is
still there with rise at 0, it is not the card moving, and the next suspect is the texture
seam - test that by holding fire and watching whether the line keeps arriving on a steady
rhythm after the puffs stop.

## Test

1. Install. `GunHeat.dll` is **782336** bytes.
2. Fire and watch for the line. With Puff rise defaulting to 0 it should be gone.
3. The puffing should still read as before - expansion and refraction carry it, with
   Puff scroll adding the upward motion.
4. If you want the old behaviour back for comparison, set **Puff rise** to 2.5.
