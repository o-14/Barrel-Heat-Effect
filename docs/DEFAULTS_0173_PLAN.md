# 0.17.3 tuned defaults plan - before editing/building

The user accepted the 0.17.2 effect in game and requested a log review plus six
new defaults. Installed mesh, normal map and DLL match 0.17.2 exactly. Preserve
that mesh and texture unchanged. Back up the accepted source/Data, both asset
files, test log and saved MCM file before changing defaults.

Update all four configuration sources together: Config.h member defaults,
F4SE/Plugins/GunHeat.ini, MCM/Config/GunHeat/config.json (including duplicate
fallback controls and help text), and generated MCM settings.ini defaults.

| Setting | Default | Slider change |
| --- | ---: | --- |
| Heat intensity | 0.04 | None |
| Height above barrel | 1 | None |
| Heat per shot | 0.07 | None |
| Pulse strength | 0.01 | min 0.005, max 0.050, step 0.005 so both endpoints and default are reachable |
| Puff expansion | 0.1 | None |
| Puff rise | 0.5 | min 0, max 1, step 0.1 |

Update stale INI default commentary. Leave runtime clamps and algorithms intact.
A DLL rebuild is required only to synchronize compiled fallback defaults. Fix
the existing CMake list's reference to missing ProjectileEmitter.h for a clean
build, without deleting any source file. Do not import the archived plume DLL.

Keep the installed user's other preferences. After backup, change only the saved
pulse override from 0.02 to the explicitly requested 0.01; otherwise it would mask
the new default. Do not ship anyone's MCM/Settings overlay in the archive.

Validate every MCM control has a matching INI default, all six typed defaults
agree, duplicated controls agree, slider endpoints/defaults are reachable, and
unrelated settings are unchanged. Build Release in the isolated tree, deployment
disabled. Compare the full 0.17.3 package against 0.17.2: only DLL, plugin INI,
MCM config.json and MCM settings.ini may differ. Mesh, texture, ESP and scripts
must match exactly. No Papyrus compilation is needed.

Commit plan/log review, defaults and release independently. Preserve all earlier
versions and publish GunHeatHaze-0.17.3-tuned-defaults.zip as the complete Vortex
mod. Report healthy log evidence without treating it as an unperformed test of
the rebuilt DLL or as a GPU benchmark.
