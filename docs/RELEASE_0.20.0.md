# GunHeat 0.20.0 - one DLL for four runtimes

Branch `claude/multi-runtime-0200`, worktree `dist/work-0.20.0-multi-runtime`, release commit
`4473f47`. Built on the accepted 0.17.4 (`849e8c7`). **The heat effect, its settings and their
defaults are unchanged**; only the DLL is new.

Every file and hash below is recorded in `docs/release-0.20.0/release-validation.json`.

## Packages

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `dist/GunHeatHaze-0.20.0-multi-runtime.zip` | 653948 | `b404ab6e07d24158ae430b057f49217c7e63a7d6080562361142472d07d8e8b2` |
| `dist/GunHeatHaze-0.20.0-multi-runtime-source.zip` | 3535383 | `79063f4ae338e5455f18ad1f441ca4f32b0abfe0725ee294e17725c43ff4b669` |
| `Data/F4SE/Plugins/GunHeat.dll` | 695808 | `840120d0d4aa814a4c78af60f6affc2300fa8c7e25cabe71ee9ef48ba1181bb6` |

The install archive has the same Data-level layout as every earlier release: 20 files at archive
root. **12 are byte-identical to 0.17.4.** Two scripts, `GunHeatController.psc` and `PlayerAlias.psc`,
differ in the working tree only because git's auto-CRLF rewrote them; the packager shipped the
0.17.4 bytes. New entries: the DLL, `COPYRIGHT.md`, `README.txt`, `THIRD_PARTY_NOTICES.md` and four
files under `Licenses/`.

The source archive is the GPL corresponding source: this repository at `4473f47` plus
`commonlibf4` `2aaefd1`, `commonlib-shared` `e30b310` and `DearModdingUI-API` `9ddb9a8` - 2,222 files.

## Supported runtimes

| Game | F4SE | Address Library file | How the DLL is admitted |
| --- | --- | --- | --- |
| 1.10.163 | 0.6.23 | `version-1-10-163-0.bin` | `F4SEPlugin_Query` returns true for 1.10.163 only |
| 1.10.984 | 0.7.2 or 0.7.3 | `version-1-10-984-0.bin` | listed in `F4SEPlugin_Version.compatibleVersions` |
| 1.11.221 | 0.7.8 | `version-1-11-221-0.bin` | listed in `F4SEPlugin_Version.compatibleVersions` |
| 1.11.240 | 0.7.9 | `version-1-11-240-0.bin` | listed in `F4SEPlugin_Version.compatibleVersions` |

F4SE refuses the DLL on any other version by design. `F4SEPlugin_Load` also refuses anything outside
these four with a line in `GunHeat.log`.

## MCM per runtime

| Game | MCM build | MCM version code | How MCM is admitted |
| --- | --- | ---: | --- |
| 1.10.163 | the build already installed for 1.10.163 | 8 | `F4SEPlugin_Query` |
| 1.10.984 | 1.40 BETA 2 | 9 | `compatibleVersions` 1.10.984 |
| 1.11.221 | 1.11.221 | 11 | `compatibleVersions` 1.11.221 |
| 1.11.240 | 1.11.240 | 11 | `compatibleVersions` 1.11.240 |

Checked from the files rather than assumed:

- **Only `mcm.dll` differs between the builds.** `MCM.swf` - the UI that draws GunHeat's two-page
  panel - and MCM's script, translations and settings files are byte-identical across all three
  archives and to the build installed for 1.10.163, where the Advanced page is confirmed in game.
- **Every `mcm.dll` reads configs from `Data\MCM\Config\` and writes settings to
  `./Data/MCM/Settings/`** - the file GunHeat's DLL overlays, `Data/MCM/Settings/GunHeat.ini`. Slider
  changes reach GunHeat the same way on every runtime.
- **Every version code is at least the panel's `minMcmVersion` of 4.**
- **The panel's 30 settings use only `f`, `b` and `i` prefixes**, all of which MCM registers. The
  `u` prefix MCM cannot register - the cause of the 0.17.4 overlap bug - is not used.

## What changed

| Commit | Change |
| --- | --- |
| `f911e60` | Plan (`docs/MULTI_RUNTIME_PLAN.md`) |
| `3436b97`, `16d3e60` | Vendor Dear-Modding CommonLibF4 as a submodule; `16d3e60` records the intended pin, see below |
| `51e34da` | GPL license, exceptions and third-party notices (`packaging/`) |
| `034587a` | Packager: license extras, source archive, `--baseline` byte checks |
| `05980a8` | Plan correction: two offsets, 1.10.984 added |
| `e04248f` | xmake build, custom `F4SEPlugin_Version` template, pinned build script, CMake guard |
| `5c32026` | Source port and layout asserts |
| `4473f47` | Release DLL staged into `Data/` |

## What is verified, and how

**The loader declaration, read from the binary.** Exports `F4SEPlugin_Query`, `F4SEPlugin_Load` and
`F4SEPlugin_Version`. The version data lists exactly `0x010A3D80`, `0x010B0DD0` and `0x010B0F00` -
F4SE's own constants for 1.10.984, 1.11.221 and 1.11.240 - with no independence bits and
`reservedBreaking` 0. That route is accepted by F4SE 0.7.2, 0.7.8 and 0.7.9, whose loader source was
checked at each tag. Version resource: 0.20.0.0, ProductName GunHeat, GPL-3.0-or-later.

**Every relocation, against the real Address Library databases.** All 13,788 ID entries in the
library were resolved against the 1.10.163, 1.10.984, 1.11.221 and 1.11.240 files from the Address
Library All-in-One archive. Nothing GunHeat reaches is missing on any runtime, including the art
object call the effect is built on:

| Relocation | 1.10.163 | 1.10.984 | 1.11.221 | 1.11.240 |
| --- | --- | --- | --- | --- |
| `TESObjectREFR::ApplyArtObject` | `0x514e50` | `0x58dd60` | `0x5e1cf0` | `0x5e2010` |
| `PlayerCharacter::Singleton` | `0x59d6fd0` | `0x2f6b8f0` | `0x31e2dd0` | `0x31ede50` |
| `TESForm::AllForms` | `0x58d36c8` | `0x2e69988` | `0x30e0e48` | `0x30ebec8` |

The same check shows why the old library could not do this: its next-gen IDs for `PlayerCharacter`,
`TESDataHandler` and `AllForms` are present in the 1.10.984 database and **missing from both 1.11
databases**.

**Memory layout, from the compiler rather than the headers.** The offset of every engine field
GunHeat touches was probed from the compiler - for the old library with the exact flags that built the
proven 0.17.4 DLL, and for the new library in this build. **All 24 values are identical.**
`src/LayoutChecks.cpp` asserts them, so a library update that moves one fails the build.

**Build.** Our sources compile with no warnings at xmake's `allextra` level. **The source archive
rebuilds the DLL on its own.** Extracted to a short path with no repository around it, it built a
695,808-byte DLL - the release DLL's size - with identical exports and a byte-identical
`F4SEPlugin_Version` block. The two files differ in 833 bytes: each embeds its own build location
five times (the PDB path, and library source paths used in log messages), and the two locations
differ in length, which shifts the data after them and the instructions that address it.

## In-game results

### 1.11.240 - passed, 11 September 2026

F4SE 0.7.9 admitted the DLL through `F4SEPlugin_Version`: `plugin GunHeat.dll (00000001 GunHeat
00140000) loaded correctly`. `GunHeat.log` opened with
`GunHeat v0.20.0 on Fallout 4 1.11.240.0 (anniversary runtime)`, then `loaded`. An eight-minute
session with `bDebugLogging=1` wrote 3,284 lines and **not one warning, error or critical line**.

| What the log shows | Value |
| --- | --- |
| Shots reported | 367, all weapon `0000463F` on ammo `0001F278` |
| Art object attaches | **1** for all 367 shots - parking holds, as on 1.10.163 |
| Muzzle node | `ProjectileNode`, resolved through `EquippedWeaponData::fireNode` |
| Plugin CPU | 403 us per second median, 650 us in the worst second (0.065%), worst single tick 356 us |
| Tick rate while driving | 118 Hz median against the 125 Hz target |
| Culled at zero refraction | 6 times, with 3 attachments parked afterwards |
| Peak refraction | 0.066 at the shipped 0.04 default - 0.036 from heat plus 0.030 from puffs - against the vanilla Minigun's 0.20 |
| Puff overlap | reached the configured cap of 6 and never passed it |

Cool-down from a full barrel, measured from the decay samples: heat 1.00 reaches the 0.05
visibility threshold in **19 seconds of unpaused game time**, and the card is culled on that frame.
One decay took 46 seconds of wall clock because 27 of them were spent paused - heat fell only
0.088 to 0.074 across the pause - so the curve follows game time rather than the clock, which is
what it should do.

Not exercised on this runtime: switching weapons mid-effect, and saving and reloading mid-effect
(checklist step 6). One weapon was fired and one load happened.

## Defaults

A default is written in five places: the MCM control's `default`, the `Default: x` its help text
promises the player, `Data/F4SE/Plugins/GunHeat.ini`, `Data/MCM/Config/GunHeat/settings.ini`, and
the member initialiser in `Config.h` that the DLL falls back on when an ini key is missing.
`tools/verify_0200_defaults.py` reads the shipped archive and asserts all five agree for every
control. **All 30 do**, recorded in `docs/release-0.20.0/defaults-validation.json`.

| Setting | Default |
| --- | --- |
| Heat intensity | 0.04 |
| Heat per shot | 0.07 |
| Height above barrel | 1 |
| Debug logging | off |
| Pulse strength, on the Advanced page | 0.01 |

**An existing `Data/MCM/Settings/GunHeat.ini` hides every default above.** MCM keeps each value the
player has ever moved in that overlay, the DLL applies it on top of its own ini, and it outlives
reinstalling the mod - so the panel can open on values from an earlier release. The 1.11.240 session
started on an overlay still holding heat intensity 0.1 and heat per shot 0.15 from earlier tuning,
and only showed 0.04 and 0.07 once those sliders were moved again. Deleting that file, or just the
line for one setting, hands the setting back to the shipped default.

## What is not verified yet - your tests

- **The game itself on 1.10.984 and 1.11.221.** 1.11.240 has now passed, above. That is the first
  evidence from outside 1.10.163: the `F4SEPlugin_Version` route works, and every struct offset the
  effect reads is correct on an anniversary executable. 1.11.221 is the same anniversary branch one
  patch earlier, so it now carries little risk. 1.10.984 is the remaining unknown - it is a different
  runtime family, and no next-gen executable has been examined.
- **MCM in game on 1.10.984 and 1.11.221.** The builds are checked from their files, above. Opening
  the panel, changing an Advanced setting and seeing it persist after a restart is still worth one
  pass per runtime. GunHeat runs without MCM.

## Test checklist

Test **1.10.163 first**: it is the regression gate against the accepted 0.17.4. Then the others in any
order.

For each runtime:

1. Install the matching F4SE, Address Library file and MCM build from the tables above. The All-in-One archive's
   files can all sit in `Data/F4SE/Plugins` together; the plugin loads the one for the running game.
2. In Vortex, install `GunHeatHaze-0.20.0-multi-runtime.zip` with no other GunHeat version active,
   deploy, and fully restart the game.
3. `f4se.log` should list `GunHeat.dll` as loaded. If F4SE refused it, its reason is on that line.
4. `GunHeat.log` should open with a line naming the version and runtime, then `loaded`:

   ```text
   GunHeat v0.20.0 on Fallout 4 1.11.221.0 (anniversary runtime)
   ```

   That is 1.11.221. The version is printed as the game reports it - `1.10.163.0`,
   `1.10.984.0`, `1.11.221.0` or `1.11.240.0` - and the family reads `original`, `next-gen`
   or `anniversary`.
5. Fire a sustained burst. The shimmer should look exactly as in 0.17.4 and fade about 19 seconds
   after the last shot from full heat with the tuned defaults (`fMaxFadeOutSeconds` 20).
6. Switch weapons mid-effect, then save and reload mid-effect.
7. Open the MCM panel, change one setting on the Advanced page, restart the game and confirm it
   held - both in the panel and in `Data/MCM/Settings/GunHeat.ini`.

With `bDebugLogging=1` the log also shows the heat, cull and parking lines used in every earlier
review. For 1.10.163, the plugin's CPU cost should stay around 500 microseconds per second.

**Send back:** `GunHeat.log` and `f4se.log` for each runtime tested, plus the crash log if the game
crashes. Check their timestamps first - each session replaces them.

## Distributing under the GPL

Wherever the mod is published, publish `GunHeatHaze-0.20.0-multi-runtime-source.zip` with it - an
optional file on the same page works - or host this repository publicly at `4473f47`. Keep
`COPYRIGHT.md`, `THIRD_PARTY_NOTICES.md` and `Licenses/` in the install archive. `COPYRIGHT.md`
carves out the texture and mesh, which are derived from Fallout 4 assets and are not the author's to
license under the GPL.

## Building

```powershell
python -B tools/build_0200.py
```

It runs the pinned xmake 3.0.1 from `<local-path>`,
refuses to build if a library submodule has moved off its pin, and never deploys. The DLL lands in
`GunHeatPlugin/build-xmake/windows/x64/releasedbg/`; copy it into `Data/F4SE/Plugins` deliberately
before packaging. The CMake build stops with a message: it belongs to the 0.17.x line.

From the source archive, which has no `.git`, the pin check cannot run: run xmake in `GunHeatPlugin/`
directly (`xmake f -m releasedbg`, then `xmake build GunHeat`).

Extract it to a short path such as `<local-path>`. From a deep folder, the archive's own folder name plus
the library's generated build paths pass Windows' 260-character path limit, and configuration fails
with `cannot open file: ...\src\PCH.h, Unknown Error (3)`. The first from-source test here failed
exactly that way from a folder about 145 characters deep.

```powershell
python -B tools/package_release.py <label> --baseline <previous release zip>
```

## Found along the way

- **Both libraries' header comments are wrong for two fields this effect depends on**:
  `artObject3D` (comment 0xD0, compiled 0xC8) and `refractionPower` (comment 0x78, compiled 0x84).
  The first layout asserts were copied from the comments and failed; the compiled values were then
  probed from the proven 0.17.4 build. Take offsets from the compiler, never from those comments.
- **`3436b97` recorded the wrong submodule commit** - Dear-Modding's `main` tip `491a09a`, eight
  commits past the pin - because `git submodule add` captured the gitlink before the pinned commit was
  checked out. `16d3e60` records `2aaefd1`. The working tree was always at the pin.
- **`Data/Scripts/Source/User/GunHeat/GunHeatController.psc:29` still declares
  `Float heatPerShot = 0.15`**, the pre-0.17.3 default. It is reached only when the DLL's
  `GetHeatPerShot` returns zero or less, which caliber scaling makes impossible - it clamps to 0.001
  or more. With caliber scaling off and a hand-edited `fHeatPerShot=0`, the script would substitute
  0.15 rather than honour the 0. **Fixed in 0.20.1** - see [RELEASE_0.20.1.md](RELEASE_0.20.1.md);
  it was left alone here because fixing it meant recompiling `GunHeatController.pex`, which replaces
  a file in the package that was under test.
- **BPR 3.0.1's `Licenses/CommonLibF4-MIT.txt` contains the GPL text**, not the MIT notice. The real
  MIT text is `res/license/MIT` in the library; GunHeat ships that.

## Rollback

`dist/GunHeatHaze-0.17.4-puff-overlap-fix.zip` is untouched. Install it through Vortex with only one
version active. The pre-port snapshot, with hashes, is `Backups/before-0.20.0-multi-runtime-20260911`.
