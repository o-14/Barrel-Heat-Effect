# Barrel Heat Effect

A Fallout 4 F4SE plugin. A weapon's muzzle distorts the air after sustained fire, the way hot metal
does — refraction only: no glowing barrel, no smoke, no particles, no colour.

It works on every gun, vanilla or modded, without patching any weapon, because it asks the engine
where the equipped weapon's muzzle is — including whatever barrel mod is fitted.

**This repository is the source.** Download the mod itself from the [GitHub release page](https://github.com/o-14/Barrel-Heat-Effect/releases).

## Supported runtimes

One `BarrelHeatEffect.dll` covers all four. F4SE refuses it on any other version by design.

| Fallout 4 | F4SE | Admitted through |
| --- | --- | --- |
| 1.10.163 | 0.6.23 | `F4SEPlugin_Query` |
| 1.10.984 | 0.7.2 / 0.7.3 | `F4SEPlugin_Version.compatibleVersions` |
| 1.11.221 | 0.7.8 | `F4SEPlugin_Version.compatibleVersions` |
| 1.11.240 | 0.7.9 | `F4SEPlugin_Version.compatibleVersions` |

Address Library for F4SE Plugins is required. Mod Configuration Menu is optional and only provides
the settings panel — every setting also lives in `Data/F4SE/Plugins/BarrelHeatEffect.ini`.

Earlier development builds were tested in game on 1.10.163 and 1.11.240;
the renamed public release has not yet had a reported in-game test. 1.10.984 and 1.11.221 are built and statically verified —
every relocation the plugin uses resolves in their Address Library databases — but have not yet been
played.

## What is and is not here

This is a **source-only** repository. The mod's mesh and texture are derived from Fallout 4's own
assets, remain Bethesda's property, and are not redistributed here. They ship only in the release
archive. That is why this repository cannot be built into a playable install on its own, and why its
public history begins at 1.0.0 rather than carrying the development history, which contains those files.

Everything that is the author's own work is here: the plugin source, the Papyrus scripts, the esp,
the settings and MCM panel definitions, the build and verification tooling, and the release notes.

## Building

Requires the Visual Studio 2022 C++ toolchain and [xmake](https://xmake.io) 3.0.1 or later.

```powershell
# Run from a short working directory near the drive root.
git clone --recurse-submodules https://github.com/o-14/Barrel-Heat-Effect.git bhe
cd bhe
$env:XMAKE_EXE = (Get-Command xmake.exe -ErrorAction Stop).Source
python -B tools/build_0200.py
```

The DLL lands in `GunHeatPlugin/build-xmake/windows/x64/releasedbg/BarrelHeatEffect.dll` with a size that can vary by build path.

Three things that will otherwise waste your afternoon:

- **Use a short folder near the drive root.** From a deep folder the library's generated build paths pass
  Windows' 260-character limit and configuration fails with
  `cannot open file: ...\src\PCH.h, Unknown Error (3)`.
- **Build from a shell with a single `PATH`.** In Git Bash, where both `PATH` and `Path` are
  present, xmake fails to find the compiler while installing spdlog — `cannot get program for cc`.
  PowerShell and the VS developer prompt are fine. `tools/build_0200.py` normalises the environment
  and works from either.
- **The build is not reproducible byte-for-byte.** Linker debug identifiers and layout details
  can differ between builds. Compiler/linker flags remove local source paths and retain only
  the PDB filename in the DLL.

`tools/build_0200.py` requires `XMAKE_EXE` and verifies all three dependency pins. It fails clearly
when that executable path is unset. Legacy CMake helpers use `CMAKE_EXE`, `NINJA_EXE`, `VSDEVCMD`,
`VCPKG_ROOT`, `VCPKG_INSTALLED_DIR` and `COMMONLIBF4_DIR`. Historical fixture tools use
`BHE_PROJECT_ROOT`; no local installation path is built into these scripts.

The Papyrus scripts are compiled with the compiler that ships with the game, so a copy of Fallout 4
is needed to build them:

```
# Set FALLOUT4_DIR to your game folder first.
$env:PAPYRUS_COMPILER = Join-Path $env:FALLOUT4_DIR 'Papyrus Compiler/PapyrusCompiler.exe'
python -B tools/compile_papyrus.py <output directory>
```

The compiled `.pex` are **not** committed. They are build output, they cannot be reproduced
byte-for-byte — the compiler reorders its tables on every run — and every `.pex` header embeds the
account name, machine name and source path of whoever compiled it. The release archive carries copies with neutral header metadata. The install packager
neutralizes the three header strings without changing bytecode. `diff_pex.py` requires
`PAPYRUS_ASSEMBLER` to point to the game's assembler. To compare two `.pex` meaningfully, use `tools/diff_pex.py`, which disassembles both and
compares them order-insensitively.

## Layout

| Path | What |
| --- | --- |
| `GunHeatPlugin/src` | the plugin: heat model, art object attachment, config, Papyrus natives |
| `GunHeatPlugin/lib/commonlibf4` | CommonLibF4 (Dear Modding FO4 fork), pinned as a submodule |
| `Data/Scripts/Source/User/GunHeat` | the three Papyrus sources |
| `Data/F4SE/Plugins/BarrelHeatEffect.ini` | every setting, documented for players |
| `Data/MCM/Config/BarrelHeatEffect` | the MCM panel and its defaults |
| `docs/` | release notes, validation records, audits, and the engine findings the effect rests on |
| `tools/` | build, packaging, and the verification scripts described below |

## Verification

Defaults are written in five places — the MCM control, its help text, the plugin ini, the MCM
defaults file, and the `Config.h` initialiser the DLL falls back on. They drift silently if nobody
checks, so:

```
python -B tools/verify_0200_defaults.py <release zip>   # all five agree, for all 30 controls
python -B tools/verify_0174_mcm.py                      # MCM setting types and the panel's shape
```

Run both before committing anything under `Data/F4SE/Plugins/` or `Data/MCM/`.

## A note on the name

The mod was called **Gun Heat Haze** during private development. The first public release is 1.0.0. Three things still carry the old name and are
not bugs: the Papyrus namespace `GunHeat:*`, the identifiers inside the esp, and the
`Data/Meshes/GunHeatHaze` and `Data/Textures/GunHeatHaze` folders. Each is stored inside the esp
or the NIF as a length-prefixed string, so renaming them means binary surgery on the script
binding for something no player sees. [Public 1.0.0 release notes](docs/RELEASE_PUBLIC_1.0.0.md) explain the release numbering;
`docs/RELEASE_1.1.0.md` preserves the private rename record.

## Licence

GPL-3.0-or-later, with the Modding Exception and the GPL-3.0 Linking Exception inherited from
CommonLibF4 — see [LICENSE](LICENSE), [LICENSE-EXCEPTIONS](LICENSE-EXCEPTIONS) and
[COPYRIGHT.md](COPYRIGHT.md).

The mesh and texture are derived from Fallout 4 assets, are not covered by the GPL, and are not in
this repository. [COPYRIGHT.md](COPYRIGHT.md) names them.

Third-party components and their pinned commits are in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
