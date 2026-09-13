# GunHeat 0.20.2 - scroll speed 0.7

One tuning change on top of 0.20.1, which passed in game on 1.11.240: **Scroll speed now defaults to
0.7 tiles per second instead of 0.6.** Nothing else about the effect changed, and no other default
moved.

The four-runtime port is unchanged - same library, same pins, same engine offsets, same loader
declaration. See [RELEASE_0.20.0.md](RELEASE_0.20.0.md) for that, and
[RELEASE_0.20.1.md](RELEASE_0.20.1.md) for the Papyrus fallback fix and the 0.20.1 test results.

## Packages

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `dist/GunHeatHaze-0.20.2-scroll-speed.zip` | 654292 | `dde0554d40e615d2184c593cd386ee2cacdb444374483fcd807cffcaeda16b1c` |
| `dist/GunHeatHaze-0.20.2-scroll-speed-source.zip` | 3559130 | `867628d47c9dcd2e9db57ce8b732f17ef0ab588c22e94db4ec6937908b15272e` |
| `Data/F4SE/Plugins/GunHeat.dll` | 695808 | `8a0e4457dcada277e745b7ebe8f76ae76e37da21e00f5217dd1c5780ba7255f1` |

20 entries at archive root. **15 are byte-identical to 0.20.1**; five changed, each because of this
one setting or the version. Every entry's hash and status is in
`docs/release-0.20.2/package-entries.json`.

| Changed entry | Why |
| --- | --- |
| `F4SE/Plugins/GunHeat.ini` | `fScrollTilesPerSecond=0.7`, and the comment that called 0.6 the chosen rate |
| `MCM/Config/GunHeat/config.json` | the slider's default and the `Default:` in its help text |
| `MCM/Config/GunHeat/settings.ini` | the MCM default MCM initialises the control from |
| `F4SE/Plugins/GunHeat.dll` | the `Config.h` fallback, and version 0.20.2 |
| `README.txt` | version and changelog entry |

## Why 0.7

It was chosen in the 0.20.1 session, not picked on paper. Measured from the `scroll=` values in
`GunHeat.log` - the drift rate between consecutive ticks, taking only samples where no puff was
pushing the texture - the session ran:

| Time | Measured tiles per second |
| --- | ---: |
| 19:49 - 19:53 | 0.600 |
| 19:54 | 0.800 |
| 19:55 - 20:02 | 0.700 |

So 0.6 for four minutes, 0.8 for one, then 0.7 for the last seven. One full tile now takes 1.43
seconds instead of 1.667. For reference the vanilla Minigun runs 0.6, which the ini comment still
records.

A default lives in five places and all five moved, so `tools/verify_0200_defaults.py` still passes
on all 30 controls:

| Where | Value |
| --- | --- |
| `Data/F4SE/Plugins/GunHeat.ini` | `fScrollTilesPerSecond=0.7` |
| the MCM slider's `default` | 0.7 |
| the `Default:` in its help text | 0.7 |
| `Data/MCM/Config/GunHeat/settings.ini` | `fScrollTilesPerSecond=0.7` |
| `GunHeatPlugin/src/Config.h` | `scrollTilesPerSecond_{ 0.7F }` |

**Your own setting already says 0.7.** `Data/MCM/Settings/GunHeat.ini` picked up
`fScrollTilesPerSecond=0.700000` when you moved the slider, and that overlay wins over the shipped
ini either way - so on this machine the new default changes nothing until that line is removed. It
matters for a fresh install.

## How the DLL was checked

The only code change is one constant. Against the 0.20.1 DLL it differs in **18 bytes**:

| Bytes | What |
| --- | --- |
| 3 | the float constant at `0xfc2e`, `0x3f19999a` -> `0x3f333333` - 0.6 to 0.7, sharing the trailing `3f` |
| 1 | the plugin's own version string, `0.20.1` -> `0.20.2` |
| 1 | `F4SEPlugin_Version.pluginVersion`, `0x00140010` -> `0x00140020` |
| 2 | `VS_FIXEDFILEINFO` file and product patch fields |
| 2 | the UTF-16 `FileVersion` and `ProductVersion` strings |
| 9 | the PE timestamp, three debug-directory timestamps, and the PDB age |

`dataVersion` is still 1 and `compatibleVersions` still lists `0x010A3D80`, `0x010B0DD0` and
`0x010B0F00`. The 87-byte non-deterministic code region that separated the shipped 0.20.0 DLL from a
rebuild does not appear here: both builds were made in the same session.

`.pex` files, the mesh, the texture, the esp and the Papyrus sources are byte-identical to 0.20.1.

## In-game results

### 1.10.163 - passed, 11 September 2026. The regression gate against 0.17.4

This is the pass that mattered: the original runtime, where 0.17.4 was proven, reached through
`F4SEPlugin_Query` rather than the `F4SEPlugin_Version` data export the other three use.

F4SE 0.6.23 loaded it - `plugin GunHeat.dll (00000001 GunHeat 00000000) loaded correctly` - and the
log opened with `GunHeat v0.20.2 on Fallout 4 1.10.163.0 (original runtime)`. 3,672 lines, **no
warning, error or critical line**.

| What the log shows | 1.10.163 on 0.20.2 | 0.17.4 baseline |
| --- | --- | --- |
| Plugin CPU, median second | **500 us** | ~500 us |
| Plugin CPU, 95th percentile second | 560 us | - |
| Worst single tick, debug logging aside | 155 us | 279 us |
| Cool-down from full heat to the cull | **19.6 s** | 19 s documented |
| Art object attaches | 1, for 489 shots | 1 per session |
| Muzzle node | `ProjectileNode` via `EquippedWeaponData::fireNode` | same |
| Puff overlap | capped at 6 | 6 |
| Peak refraction | 0.075 at the 0.04 default | - |

Also confirmed here:

- **The new scroll speed.** Measured from the `scroll=` values, the drift ran **0.698 tiles per
  second** across 175 samples - the 0.7 this release ships.
- **The 0.20.1 Papyrus fix, running for the first time.** This session's controller quest actually
  initialised, so `OnQuestInit` fired and logged `Papyrus: LoadIniConfig: heatPerShot=0.070000`. On
  the 1.11.240 session it never ran, because the quest was already going in that save.
- **Caliber scaling on three calibers**: damage 18 -> 0.054, 25 -> 0.064, 30 -> 0.070 per shot.
- **Weapon-switch reset, and what it looks like.** Two switches, each resetting heat (from 0.540 and
  0.561). Both are followed by a cull about 1.4 s later, which is the design rather than a fault: the
  reset zeroes heat and the shimmer already on screen fades out on the normal `fFadeOutSeconds` ramp
  instead of vanishing on the frame of the switch.

### The one 98 ms tick, and why it is not a regression

One tick reported `98292 us total, 97902 us worst`, against 198-863 us across the session's other
184 full seconds, whose worst single ticks top out at 155 us. It is the tick that dumps the node tree, and the gaps between its own log lines account for
all of it:

```text
20:25:10.000  SetHazeStrength: art object 3D ready, root=GunHeatBarrelHaze
20:25:10.071  (+71.0 ms)  AttachHaze tree: GunHeatBarrelHaze [NiNode]
20:25:10.071  (+ 0.0 ms)  AttachHaze tree:   Cylinder026 [NiNode]
20:25:10.097  (+26.0 ms)  AttachHaze tree:     Cylinder026:0 [BSGeometry]
20:25:10.098  (+ 1.0 ms)  SetHazeStrength: form=00000014, heat=0.198895, ...
```

10.000 to 10.098 is 98 ms, matching the reported worst tick; 97 ms of it sits in two gaps between
consecutive `logger::info` calls. The log is **flushed on every info line** by design - `main.cpp`
says so, and diagnosis has leaned on it all along - so the first writes of a session pay for opening
and flushing the file. Those lines only exist with `bDebugLogging=1`, which is off by default, and
the tick does no work between them.

Worth remembering when reading this instrumentation: with debug logging on, the tick cost it reports
includes its own log writes. The honest figure for the effect itself is the 155 us worst tick from
the seconds that are not dumping a tree.

### Cosmetic: f4se.log cannot name the build on 1.10.163

`f4se.log` prints `GunHeat 00000000` there, where the other three runtimes print `GunHeat 00140020`.
`F4SEPlugin_Query` sets `a_info->version = Version::MAJOR`, which is 0 for every 0.x release, while
the `F4SEPlugin_Version` export carries the packed version. Nothing functional depends on it -
`GunHeat.log` names the build on its first line - but on the original runtime `f4se.log` alone cannot
tell 0.20.0 from 0.20.2. A one-line change would fix it, at the cost of another DLL build; it is not
in this release.

## Test checklist

1. Install `GunHeatHaze-0.20.2-scroll-speed.zip` with no other GunHeat version active, deploy, and
   fully restart the game.
2. `GunHeat.log` should open with `GunHeat v0.20.2 on Fallout 4 1.11.240.0 (anniversary runtime)`.
3. Fire a sustained burst. The drift should look exactly as it did for the last seven minutes of the
   0.20.1 session, since that is the value being shipped.
4. To confirm the shipped default rather than your overlay, delete the `fScrollTilesPerSecond` line
   from `Data/MCM/Settings/GunHeat.ini` before starting. The panel should then show 0.7.
5. Still outstanding from 0.20.0: **1.10.984** and **1.11.221**. 1.10.163 and 1.11.240 have both
   passed - see In-game results above and in [RELEASE_0.20.1.md](RELEASE_0.20.1.md).

**Send back:** `GunHeat.log` and `f4se.log`, plus the crash log if the game crashes.

## Rollback

`dist/GunHeatHaze-0.20.1-heatpershot-default.zip` and `dist/GunHeatHaze-0.20.0-multi-runtime.zip`
are untouched, as is `dist/GunHeatHaze-0.17.4-puff-overlap-fix.zip`. Install one of them through
Vortex with only one version active. Or keep 0.20.2 and set `fScrollTilesPerSecond=0.6` in
`Data/F4SE/Plugins/GunHeat.ini`, which is all this release changed. The pre-0.20.2 snapshot is
`Backups/before-0.20.2-scroll-speed-20260911`, which also keeps the 0.20.1 logs, since each session
overwrites them.
