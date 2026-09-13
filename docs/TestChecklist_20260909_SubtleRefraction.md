# 0.17.2 subtle-refraction comparison

0.17.1 is the restored baseline. 0.18.0 and 0.19.0 are archived, rejected visual
experiments. They are not prerequisites for this trial.

For an exact in-game rollback, disable the later release in Vortex, enable
`GunHeatHaze-0.17.1-mcm-defaults-fix.zip` and deploy. Source restoration and moving
archives on disk do not change the installed Vortex deployment.

## The one change in this trial

`GunHeatHaze-0.17.2-subtle-refraction.zip` is the full mod. It retains the 0.17.1
DLL, ESP, configuration, scripts, mesh geometry, UVs and animation. The NIF's two
texture paths now use a mod-owned copy of the original vanilla normal pattern,
with approximately half the tangent-space XY displacement at each existing mip.
There are no added plumes, shader changes, new controllers or runtime changes.
Baked refractionStrength remains exactly 0.0.

Expected: the same effect and movement, with less background warping and a less
opaque-looking appearance. This is not literal 50% opacity, and FO4's perceived
distortion need not scale linearly. The existing silhouette and edges may still
be visible. They are a separate trial after the strength comparison.

## Short test

1. Use the same weapon, scene and MCM settings for both versions. From cold,
   sustain fire against a detailed wall or fence, then let the effect cool fully.
2. Compare 0.17.1 and 0.17.2: is the background clearer while the shimmer remains
   visible? Report whether the trial is still too strong, acceptable or too faint.
3. Check that placement, pattern movement and cooling behavior still resemble
   0.17.1. Note any new colored/opaque patch or cycle-start pop as a failure.

Install only one version at a time. Disable the trial and re-enable/deploy the
original full 0.17.1 release to undo it. No DLL rebuild or save migration is needed.

## Preservation and verification

Before the first asset edit, the exact NIF and full 0.17.1 archive were copied to
`Backups/before-0.17.2-opacity-trial-20260909` and verified by hash. The extracted
original vanilla BC5 texture data was also saved there before vector processing.
Earlier full source backups and both rejected-version branches remain available.

Seventeen of eighteen NIF blocks are byte-identical to 0.17.1; only the texture-set
paths changed. All ten DDS mips decode successfully. At 512 pixels, normal RMS is
50.007% of the original and pattern correlation is 0.999898. Smallest mip ratios
are affected by 8-bit quantization. These are vector-data measurements, not an
in-game rendering test. Eleven original package files are byte-identical,
including the DLL, ESP, scripts and every shipped configuration file.

See `subtle-0.17.2/asset-verification.json` and `release-verification.json` for
per-mip measurements and exact package hashes. No Fallout 4 test was possible here.
