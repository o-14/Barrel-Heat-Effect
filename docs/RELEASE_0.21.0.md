# GunHeat 0.21.0 - the end-user release

Nothing about the effect changed. This release makes the mod presentable to someone who has never
read a line of this project: the settings file and the readme are now written for a player, and
`f4se.log` names the build on every runtime instead of three out of four.

The port itself is untouched - same library, same pins, same engine offsets, same four runtimes.
[RELEASE_0.20.0.md](RELEASE_0.20.0.md) covers that, and 0.20.2 passed in game on **1.10.163** and
0.20.1 on **1.11.240**; see [RELEASE_0.20.2.md](RELEASE_0.20.2.md) and
[RELEASE_0.20.1.md](RELEASE_0.20.1.md).

## Packages

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `dist/GunHeatHaze-0.21.0.zip` | 655162 | `e898402513aeba0088240c2746002b08711608b490481b216e726505999ec1e0` |
| `dist/GunHeatHaze-0.21.0-source.zip` | 3516512 | `82a8ab7839fcb08ca5a17a6fdf77726a2191d259e509a5b69203bbbe9fc01c4c` |
| `Data/F4SE/Plugins/GunHeat.dll` | 695808 | `f27b609561ff050f4511d6ae1f7f016f7b8984450608f27a60dbef3bd259a8bc` |

**17 of the 20 packaged entries are byte-identical to 0.20.2.** The three that changed are the DLL,
the settings file and `README.txt`. Every hash and status is in
`docs/release-0.21.0/release-validation.json`.

## f4se.log now names the build on 1.10.163

`F4SEPlugin_Query` set `a_info->version = Version::MAJOR`, which is 0 for every 0.x release, so
1.10.163 - the only runtime admitted through `Query` rather than the `F4SEPlugin_Version` export -
logged `plugin GunHeat.dll (00000001 GunHeat 00000000) loaded correctly` and could not distinguish
one build from another. It now reports `Version::PACKED`, built with the library's own
`REL::Version::pack()` so it is the same number the version export carries: **0x00150000** for
0.21.0. Both paths now agree.

Against the 0.20.2 DLL the binary differs in **22 bytes, and exactly one of them is code**: the
immediate at `0x2589d`, `0x00000000` to `0x00150000`, with no change in instruction length. The other
21 are the version string, `pluginVersion`, two `VS_FIXEDFILEINFO` pairs, the two UTF-16 resource
strings, four timestamps and the PDB age. `compatibleVersions` still lists 1.10.984, 1.11.221 and
1.11.240, and `Query` still admits 1.10.163 only.

## The settings file, rewritten for a player

`Data/F4SE/Plugins/GunHeat.ini` is what a player opens to change the effect. It explained itself in
the project's own terms: "Route A", `TESObjectREFR::ApplyArtObject`, `EquippedWeaponData::fireNode`, a
pointer to a Ghidra findings document, the retune rationale with logged shot counts and an RPM
break-even calculation, and a setting still marked EXPERIMENTAL two months after it became a default.
Someone who wanted the shimmer a bit smaller had to read past all of it.

It now describes what each setting does and what changing it will look like, with the MCM overlay trap
stated at the top, because that is the one thing that makes an edit appear to do nothing.

**No value changed.** All **45 settings in 5 sections**, and their order, parse identical to the
0.20.2 archive; the packager's `--baseline` check covers the file as a whole and a parse-and-compare
covers the settings. The file went from 10,243 to 9,173 bytes.

The engineering reasoning is not lost. [INI_MAINTAINER_NOTES.md](INI_MAINTAINER_NOTES.md) keeps it,
including the two parts that are genuinely non-obvious:

- why `[Heat]` was retuned on 2026-08-06 - a cold barrel cooled *fastest*, so 1,030 logged shots
  never crossed the visibility threshold;
- that `fMinFadeOutSeconds` is not only the short-burst cool-down but the cooling rate while heat is
  still building, which is why it cannot be set low.

## README.txt, rewritten as the readme

It is now what a Nexus page can stand on: what the mod does in two lines, the runtime and F4SE table,
install and uninstall, how to tell it is working, the four settings worth knowing, compatibility, and
how to report a problem - which asks for the two logs and warns that both are overwritten each
session.

Three claims were checked rather than assumed:

- **"cannot conflict with weapon, ammo or balance mods"** - the esp was walked record by record. It
  declares `Fallout4.esm` as its only master and adds three records under its own index (`QUST`
  `01000800`, `PROJ` `01000801`, `ARTO` `01000802`). **It overrides nothing.**
- **the CPU figure** is the measured 1.10.163 median of 500 us per second, not an estimate.
- **uninstalling** is no longer described as leaving nothing behind. A save that has run a Papyrus
  script keeps a reference to it; that is true of every script mod and it does no harm, but the readme
  now says so instead of implying a clean removal.

An ENB compatibility claim was cut to a statement about the mechanism - the shimmer is the game's own
refraction effect, the same kind the Minigun uses - because no ENB has actually been tested with it.

## Found while cleaning up

- **The esp carries an unused `PROJ` record**, `01000801`, left from the abandoned projectile
  experiment. It is 263 bytes, referenced by nothing, and has shipped since early on. Left in place
  deliberately: removing a record from a shipped esp is a save-compatibility question and the author's
  call, not tidying.
- **The repository tracks 29 Fallout 4-derived `.nif` and `.dds` files, of which only two ship.** That
  matters for publishing on GitHub rather than for this release, and it is the first thing
  [GITHUB_HANDOFF.md](GITHUB_HANDOFF.md) deals with.

## Test checklist

Short pass. The effect code is 0.20.2's, already played on 1.10.163.

1. Install `GunHeatHaze-0.21.0.zip` with no other GunHeat version active, deploy, restart the game.
2. On **1.10.163**, `f4se.log` should now read `plugin GunHeat.dll (00000001 GunHeat 00150000) loaded
   correctly` - that is the fix. On the other three it already read a real version and should now read
   `00150000` too.
3. `GunHeat.log` should open with `GunHeat v0.21.0 on Fallout 4 <version> (<family> runtime)`.
4. Fire a sustained burst. It must look exactly as it did on 0.20.2; any visible difference is a
   regression, since only comments and a version number changed.
5. Open `Data\F4SE\Plugins\GunHeat.ini` and read it as a player would. If any setting's description
   does not match what changing it actually does, that is the bug this release is most likely to have.
6. Still outstanding since 0.20.0: in-game passes on **1.10.984** and **1.11.221**.

**Send back:** `GunHeat.log` and `f4se.log`, plus the crash log if the game crashes.

## Rollback

`dist/GunHeatHaze-0.20.2-scroll-speed.zip` is untouched, as is every earlier release including
`dist/GunHeatHaze-0.17.4-puff-overlap-fix.zip`. Install one through Vortex with only one version
active. The pre-0.21.0 snapshot is `Backups/before-0.21.0-end-user-release-20260911`, which keeps the
0.20.2 settings file in full - its comments were the engineering record - alongside the 0.20.2 DLL and
the sources this release changed.
