# Barrel Heat Effect 1.1.0 - the rename

Gun Heat Haze is now **Barrel Heat Effect**. Nothing about the effect changed: not a default, not a
value, not the mesh, not the texture, not a script. Only names.

**This is a breaking install change.** The plugin, the settings file and the MCM panel all have new
names, so it needs a clean reinstall rather than an upgrade in place.

## Packages

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `dist/BarrelHeatEffect-1.1.0.zip` | 655541 | `98acaa89bdcc1c7111b319474bfe0ddc6c029f0f0fdd6d13994a50ca9a7ee9d1` |
| `dist/BarrelHeatEffect-1.1.0-source.zip` | 3558232 | `233095d2d1df67a9b37a6dd994ef36e4297eb004a3d044f4ec1c5ede6fdb3bf7` |
| `Data/F4SE/Plugins/BarrelHeatEffect.dll` | 696320 | `b50499667522b809608b22ab34ede448c64ae41d38d4043a814b40e21d068cc2` |

## What was renamed

| Was | Now |
| --- | --- |
| `F4SE/Plugins/GunHeat.dll` | `F4SE/Plugins/BarrelHeatEffect.dll` |
| `F4SE/Plugins/GunHeat.ini` | `F4SE/Plugins/BarrelHeatEffect.ini` |
| `GunHeatHaze.esp` | `BarrelHeatEffect.esp` |
| `MCM/Config/GunHeat/` | `MCM/Config/BarrelHeatEffect/` |
| `Data/MCM/Settings/GunHeat.ini` | `Data/MCM/Settings/BarrelHeatEffect.ini` |
| `GunHeat.log` | `BarrelHeatEffect.log` |
| F4SE plugin name `GunHeat` | `BarrelHeatEffect` |
| MCM `modName` / `displayName` | `BarrelHeatEffect` / `Barrel Heat Effect` |
| `GunHeatHaze-<v>.zip` | `BarrelHeatEffect-<v>.zip` |

## What kept the old name, and why

Three things still say GunHeat. None is visible in play, and each would need binary surgery inside
the esp or the NIF to change:

- **The Papyrus namespace `GunHeat:*`, and `Data/Scripts/GunHeat/`.** The namespace is bound inside
  the esp's `VMAD` subrecord as a length-prefixed string. Renaming it means editing that record,
  recompiling all three scripts, and changing the DLL's native registration to match — three coupled
  changes whose only real test is a game session, risking the quest binding for something no player
  sees.
- **The esp's internal strings**: the quest EDID `GunHeatControllerQuest`, which `main.cpp` names in
  its `startquest` command; the `VMAD` binding; the ARTO EDID; and the `MODL` path.
- **`Data/Meshes/GunHeatHaze/` and `Data/Textures/GunHeatHaze/`**, because the mesh path is stored in
  the esp's `MODL` and the texture path inside the NIF.

They surface only in xEdit and in a mod manager's file list. If you want them gone too, that is a
separate job with its own in-game test; `docs/CODEX_HANDOFF_20260911.md` sizes it.

## What players have to do

- **Remove the old version before installing.** Two versions must never be active at once, and the
  old one is a different set of filenames, so a mod manager will not replace it.
- **Enable `BarrelHeatEffect.esp`.** A save made with `GunHeatHaze.esp` loses that plugin. The mod
  stores nothing in the save that matters, so the effect simply starts working again once the new
  plugin is enabled.
- **To keep MCM settings**, rename `Data/MCM/Settings/GunHeat.ini` to `BarrelHeatEffect.ini`. MCM
  looks for settings under the new `modName`, so otherwise the panel starts from the defaults.

## Verified

The rename had to change names and nothing else, so that was measured rather than assumed:

| Check | Result |
| --- | --- |
| Settings in the shipped ini | **all 45 parse identical to 1.0.0**, in the same order, except `sArtObjectPlugin` — which names the esp and must change |
| MCM panel | **all 39 content entries identical**; only `modName` and `displayName` differ |
| The esp | **byte-identical to 1.0.0** — only the filename changed |
| Packaged entries | 12 of 20 byte-identical to 1.0.0; the rest are the renamed files, the DLL and the notices |
| Defaults | all 30 controls agree across all five places, six for `fHeatPerShot` |

The DLL grew 512 bytes, and the growth is entirely `.rdata`: the identity strings are longer and the
section crossed one alignment block. `.text` is exactly the same size. `pluginVersion` and
`F4SEPlugin_Query` both report `0x01010000`, `compatibleVersions` still lists 1.10.984, 1.11.221 and
1.11.240, and the strings `GunHeat.ini`, `GunHeatHaze.esp` and `Data/MCM/Settings/GunHeat.ini` are
gone from the binary. `GunHeatControllerQuest` is still there, deliberately, because the esp still
uses it.

## Test checklist

The rename changes what the game loads, so this needs a real pass — more than the last few releases
did.

1. **Remove the old version entirely**, then install `BarrelHeatEffect-1.1.0.zip` and enable
   `BarrelHeatEffect.esp`.
2. `f4se.log` should read `plugin BarrelHeatEffect.dll (00000001 BarrelHeatEffect 01010000) loaded
   correctly`.
3. The log is now `Documents\My Games\Fallout4\F4SE\BarrelHeatEffect.log`, and should open with
   `BarrelHeatEffect v1.1.0 on Fallout 4 <version> (<family> runtime)`.
4. **Fire a burst.** The art object is resolved by name from the ini — `sArtObjectPlugin` now says
   `BarrelHeatEffect.esp` — so if the rename broke anything, the log says
   `AttachHaze: could not resolve` and no shimmer appears. This is the one thing most likely to be
   wrong.
5. **Open MCM.** The panel should be listed as *Barrel Heat Effect*, with both pages and all 30
   settings. Change one on the Advanced page, restart, confirm it held in
   `Data\MCM\Settings\BarrelHeatEffect.ini`.
6. Still outstanding since 0.20.0: in-game passes on **1.10.984** and **1.11.221**.

**Send back:** `BarrelHeatEffect.log` and `f4se.log`, plus the crash log if the game crashes.

## Rollback

`dist/GunHeatHaze-1.0.0.zip` and every earlier release are untouched. Install one through Vortex with
only one version active, and re-enable `GunHeatHaze.esp`. The pre-rename snapshot is
`Backups/before-rename-barrel-heat-effect-20260911`, which keeps the old esp, ini, DLL, MCM config
folder, README and the four sources that changed.
