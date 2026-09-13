# Barrel Heat Effect 1.0.0 — first public release

The first public release is **1.0.0**, using the renamed Barrel Heat Effect build previously
labelled 1.1.0 in private development. Only version metadata and release documentation change.
The effect code, settings, mesh, texture, ESP and Papyrus scripts remain unchanged.

The install package is `BarrelHeatEffect-1.0.0.zip`; the source tag is `v1.0.0`.
The DLL must report packed plugin version `0x01000000` in both loader paths.
Historical `RELEASE_1.0.0.md` describes the earlier Gun Heat Haze build;
`RELEASE_1.1.0.md` records the private rename and retains its original hashes and test results.
Those documents are historical evidence, not verification of this public package.

## Runtime support and test limits

| Fallout 4 | F4SE | Evidence |
| --- | --- | --- |
| 1.10.163 | 0.6.23 | Earlier development build tested in game; admitted through Query |
| 1.10.984 | 0.7.2 / 0.7.3 | Statically checked in development; no reported game test |
| 1.11.221 | 0.7.8 | Statically checked in development; no reported game test |
| 1.11.240 | 0.7.9 | Earlier development build tested in game |

One DLL declares all four runtimes. Address Library for F4SE Plugins is required;
Mod Configuration Menu is optional. The renamed/reversioned release has not been tested in game.
The three `compatibleVersions` entries remain 1.10.984, 1.11.221 and 1.11.240.
Build output is not byte-reproducible; build paths affect its contents and size.

## Clean installation

- Remove the old version before installing, including Gun Heat Haze; never enable both.
- Install the complete archive with Vortex and enable `BarrelHeatEffect.esp`.
- To retain old MCM preferences, back up and rename `Data/MCM/Settings/GunHeat.ini` to
  `BarrelHeatEffect.ini`. If that destination already exists, preserve it and compare the files
  before replacing it. An existing Barrel Heat Effect settings overlay remains authoritative.

The internal GunHeat script namespace, ESP identifiers, mesh folder and texture folder are
intentionally retained, as explained in the private rename notes.

## Source and licence

GPL-3.0-or-later with the CommonLibF4 Modding and Linking Exceptions; see `LICENSE`,
`LICENSE-EXCEPTIONS`, `COPYRIGHT.md` and `THIRD_PARTY_NOTICES.md`.
The public repository is source-only, including pinned dependency gitlinks. Fallout 4-derived art
is excluded from its tree and history. Install archives contain the required game-derived assets.
Private `-source.zip` archives contain art and must not be uploaded as GitHub release assets.
