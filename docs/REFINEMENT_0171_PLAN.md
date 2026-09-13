# 0.17.1 refinement plan - written before the opacity trial

The user rejected 0.18.0 and 0.19.0 in game, requested both be archived, and
selected excessive opacity/distortion as the first issue to address on 0.17.1.
The original checkout's 12 runtime files match the original 0.17.1 install archive
byte-for-byte. Work starts from b073124 on codex/refine-0171; no later asset or
DLL changes are carried forward. The user's installed Vortex state is not changed
by restoring source: disable the later mod and deploy 0.17.1 to restore the game.

## Preservation

Before edits, copy and verify the exact 0.17.1 NIF and complete install archive in
Backups/before-0.17.2-opacity-trial-20260909. Earlier complete source backups remain.
Move rejected release packages and the 0.19.0 source snapshot into dist/Archived,
with per-file hashes; preserve their Git branches/worktrees and all backups.
No files are deleted, no historical package is overwritten.

## First trial: distortion amplitude only

Prepare 0.17.2-subtle-refraction as a complete Vortex mod based on 0.17.1.
Keep the exact original geometry, UVs, shader flags, baked strength 0.0, controllers,
DLL, configuration, Papyrus, plume pattern and scroll behavior. Read the vanilla
SmokeVapor01Tile_n normal data locally, make a mod-owned BC5 copy with normal XY
displacement approximately halved at every existing mip, and change only the NIF's
two texture references. This is a weaker version of the original pattern, not a
new plume design. Do not change vertex alpha or assume it provides softness.

The user calls the effect opaque. This trial addresses that impression by reducing
background warping; it does not introduce an opacity shader or guarantee a linear
50% reduction of the engine's visual effect. It intentionally does not solve
remaining plume shape, hard edges or animation in the same trial.

Match the existing vanilla BC5 encoding and mip dimensions. Preserve spatial
features rather than creating radial noise, changing UVs or adding layers.
Verify decoded normal strength, map correlation and every mip. Verify all NIF
blocks except texture-set paths are byte-identical to baseline. Keep the original
DLL hash and compare every unchanged package entry to the 0.17.1 full release.

## Test and next step

Use unchanged MCM settings to compare 0.17.1 and 0.17.2 in the same scene. Check
whether background detail is clearer during sustained fire and cooling, whether
the shimmer is still visible, and whether the original motion is retained. If the
effect still appears colored/opaque despite lower distortion, record that finding
before another shader or texture change. Nobody here can run Fallout 4.

Only after this trial is evaluated, address edges with one texture falloff change,
then animation or plume shape as separate experiments. Retain the accepted 0.17.1
structure and measured runtime. No DLL rebuild is needed for this trial.

Commit the archival record, plan, asset change and full release separately. Use
0.17.2 as an unused patch label on the restored 0.17.x line; never overwrite 0.17.1.
