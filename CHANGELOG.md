# Changelog

This repository begins with public release 1.0.0. Earlier builds were developed privately;
the private version labels below are preserved as historical records because
the earlier history contains Fallout 4-derived art that is not redistributed here. The releases
themselves are documented in full under [`docs/`](docs/).

## 1.0.0 — metadata cleanup

Removed build-machine metadata from compiled-script headers, DLL diagnostics and source text.
No gameplay change. The original 1.0.0 version number is retained for this corrected package.

## 1.0.0 — first public release

Barrel Heat Effect begins public release numbering at 1.0.0. It preserves the effect, settings,
assets and scripts of the private Barrel Heat Effect 1.1.0 build; only version metadata and
release documentation change. See [release notes](docs/RELEASE_PUBLIC_1.0.0.md).

## Private development 1.1.0 — rename

Renamed from **Gun Heat Haze** to **Barrel Heat Effect**. Nothing about the effect changed —
no default, no value, no mesh, no texture, no script.

The plugin, the settings file, the esp and the MCM panel all have new names, so this needs a clean
reinstall rather than an upgrade in place, and `BarrelHeatEffect.esp` has to be enabled in the load
order. To keep settings changed in MCM, rename `Data/MCM/Settings/GunHeat.ini` to
`BarrelHeatEffect.ini`.

The Papyrus namespace, the esp's internal identifiers and the mesh and texture folders keep the old
name on purpose; see `docs/RELEASE_1.1.0.md`.

## Private development 1.0.0 — Gun Heat Haze

First stable release.

- Removed an unused `PROJ` record left from an abandoned projectile experiment. The plugin now adds
  two records instead of three. Existing saves are unaffected: nothing referenced it, and the
  surviving records keep their FormIDs.
- Verified in game on 1.10.163 and 1.11.240.

## 0.21.0

- `Data/F4SE/Plugins/GunHeat.ini` rewritten for players. Every value unchanged — all 45 settings and
  their order verified identical to 0.20.2.
- `f4se.log` now names the build on 1.10.163 too. `F4SEPlugin_Query` reported only the major version,
  which is 0 for any 0.x release, so that runtime logged `GunHeat 00000000`.
- The engineering rationale that used to live in the ini's comments moved to
  [`docs/INI_MAINTAINER_NOTES.md`](docs/INI_MAINTAINER_NOTES.md).

## 0.20.2

- Texture drift default raised from 0.6 to 0.7 tiles per second, chosen in game over 0.6 and 0.8.
- Passed on 1.10.163, the regression gate against the accepted 0.17.4 effect: 500 µs per second
  median CPU against ~500 before, and a 19.6 s cool-down from a full barrel against 19 s documented.

## 0.20.1

- Fixed a Papyrus heat-per-shot fallback still holding the pre-0.17.3 default of 0.15. It applied
  only with caliber scaling off and `fHeatPerShot` hand-edited to 0.
- Passed on 1.11.240: 989 shots across four weapons and four calibers over a single art object
  attach, with no warning or error.

## 0.20.0

- One DLL for Fallout 4 1.10.163, 1.10.984, 1.11.221 and 1.11.240, rebuilt on Dear Modding FO4's
  multi-runtime CommonLibF4.
- The log records the game version and runtime family at startup.
- Every relocation the plugin uses was resolved against all four real Address Library databases, and
  every engine struct offset it reads was probed from the compiler rather than taken from header
  comments — two of which are wrong.
