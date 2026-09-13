# Gun Heat Haze asset improvement plan

Status: planning only. The user explicitly instructed: do not build anything yet.

Actual repository: `<local-path>`.
Read `docs/ASSET_BRIEF.md` and `docs/HANDOFF.md` before preparing this revision.
Their established findings are constraints, not hypotheses to re-investigate.

Baseline: clean `master` at `a39b4c5` (handoff and brief), following `0df1fda`
(Gun Heat Haze 0.17.1). Read-only inspection with the existing NIF tools confirms
the 11,865-byte, 18-block asset, NiBillboardNode, 91-vertex rendered card, both
stock smoke texture references, and the listed controller/editor-marker blocks.
Baseline NIF SHA256:
`98DDD6FD6738D79B1C54E3DD78CBBD7C6E9E54C630F77C9405669BC70AAD7FF9`.

No asset generation, mesh edits, texture edits, DLL/Papyrus builds, packaging,
deployment, or cleanup will occur during this planning stage. No files will be
deleted. Existing releases, older assets, and backups will remain untouched.

## 1. Protect the baseline before later implementation

- Commit this document separately. Wait for the user's instruction to proceed
  beyond planning.
- Before implementation, recheck the working tree and create a uniquely named,
  dated source backup outside the source tree. Include tracked source and tools,
  documentation, current Data assets, and relevant untracked working inputs;
  record exclusions for build caches and historical archives explicitly.
- Verify the backup inventory and SHA256 hashes against the originals. Git alone
  is not the requested source backup. Do not overwrite any existing backup.
- Work in a new isolated checkout/branch (`codex/heat-haze-asset`) so the original
  checkout and older versions remain unchanged. Keep the untouched baseline NIF
  in the verified backup as well as Git.
- Inspect texture packaging, shader fields, controller reachability, references,
  and UV ranges using the documented layout. Presence of a controller block alone
  is not evidence that it is reached by the active controller chain.

## 2. Prepare one visual revision

- Keep the existing single billboard card for the first in-game trial to hold geometry and overdraw
  constant. Defer layered cards, different layer scroll rates, and tapering until
  the texture has been evaluated in game.
- Author a dedicated normal/flow texture with fine, vertically biased turbulence.
  Avoid broad smoke-like curls. Use a new, dedicated texture filename; do not
  overwrite the existing HeatHazeFlowTile_n.dds or any historical texture.
- The brief does not specify DDS encoding or exact shader channel semantics.
  Inspect available texture inputs and export support before selecting encoding,
  channel packing, and mip generation; document that choice.
- Put edge falloff in the texture. Blend distortion toward a neutral normal at
  the boundaries and include the requested soft top/bottom alpha gradient, subject
  to the documented channel semantics. Do not rely on vertex alpha.
- Design repeat behavior around measured UV ranges and the documented runtime
  scrolling. A gradient in a scrolling texture moves with its UVs; it is not a
  guaranteed stationary card-edge mask. Inspect a complete scroll cycle before
  delivery for moving bands and exposed edges. If the current material cannot
  provide stationary falloff with the chosen map, explain the limitation and
  propose the smallest next change before adding layers or altering the DLL.
- Point the NIF at the packaged texture. Retain billboard parenting, a drivable
  BSLightingShaderProperty, refraction flags, refractionPower, and texCoordOffset.
- Bake refractionStrength at exactly 0.0. Add no glow, emissive output, or smoke.
- In the future working copy only, remove the controlledVar=0 BSLightingShaderPropertyFloatController and detached
  EditorMarker021 blocks, repairing links with the existing binary tools.
- Make no C++ or Papyrus changes. If the documented asset contract reveals a real
  need for an additive DLL change, describe that need explicitly before doing it.

## 3. Verify and commit

- Use dump_nif_shader_values.py, inspect_nif_blocks.py, and applicable repository
  validators to confirm zero baked refraction, preserved flags/material access,
  valid references, removed leftovers, and the correct texture path.
- Inspect decoded texture channels, neutral edge falloff, repeat boundaries,
  mipmaps, DDS metadata, and packaged file presence.
- Confirm the geometry/layer count has not increased and review the diff for
  unintended changes. Static verification cannot establish FO4's visual result.
- Commit each distinct change separately: the plan, mechanical NIF cleanup, and
  the texture plus its NIF path update as one coupled asset change. Deliver these
  together as one proposed in-game revision; do not generate further visual
  variants before receiving the user's observations.
- Provide a single rollback command restoring the exact baseline NIF from the
  verified backup. Leave the new texture on disk, unreferenced, so rollback
  deletes nothing and does not disturb unrelated files. Preserve older packages;
  any future trial package must have a unique name.

## 4. User's in-game check

Expected result: fine rising hot-air distortion with softer boundaries and less
smoke-like structure, using the existing runtime heat ramp and a single card.

1. Check cycle start and cooling for pops or residual visible distortion.
2. Check sustained fire against contrasting backgrounds for hot-air appearance,
   hard edges, scrolling bands, and repeat seams.
3. Check first-person aiming and third-person views for muzzle alignment and any
   visible rectangular silhouette.
4. Compare performance with the baseline during sustained fire.

No Fallout 4 testing is available in this environment. Report static checks as
static checks and leave appearance/performance conclusions to the user's trial.
