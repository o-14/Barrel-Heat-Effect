# GunHeat 0.20.1 - the Papyrus heat-per-shot fallback

Branch `claude/multi-runtime-0200`, worktree `dist/work-0.20.0-multi-runtime`. One behavioural
change on top of 0.20.0, which passed in game on 1.11.240: the Papyrus fallback for heat per shot
was still the pre-0.17.3 value. **The effect, every setting and every default are unchanged.**

Everything about the four-runtime port - the loader declaration, the relocations, the struct
layouts, the MCM build per runtime - is in [RELEASE_0.20.0.md](RELEASE_0.20.0.md) and still applies.
This release changes no library, no pin and no engine offset.

## Packages

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `dist/GunHeatHaze-0.20.1-heatpershot-default.zip` | 654201 | `e7eb520a85d75bcb00dd4a191c00afbcd5b6b06a5e4685415c5a6d0a0a98b860` |
| `dist/GunHeatHaze-0.20.1-heatpershot-default-source.zip` | 3581779 | `5ca4e4aa0846d2535123f41f8a70f515af45f2f911999f788d5c5f44d87e4ae2` |
| `Data/F4SE/Plugins/GunHeat.dll` | 695808 | `5f9c733717a30ebf8fe68aad76545be9d006d03c0b76916a3100a696d18c2bf5` |

20 entries at archive root, as always. **16 are byte-identical to 0.20.0**; four changed, and every
entry's hash and status is in `docs/release-0.20.1/package-entries.json`.

| Changed entry | Why |
| --- | --- |
| `Scripts/Source/User/GunHeat/GunHeatController.psc` | the fallback, 0.15 -> 0.07 |
| `Scripts/GunHeat/GunHeatController.pex` | recompiled from it |
| `F4SE/Plugins/GunHeat.dll` | version 0.20.1, so the log names the build under test |
| `README.txt` | version and changelog entry |

## The fix

`GunHeatController` asks the DLL what a shot is worth and keeps its own value for the case where
the native answers zero or less:

```papyrus
Float shotHeat = GunHeat:GunHeatNative.GetHeatPerShot(equippedWeapon)
If shotHeat <= 0.0
    shotHeat = heatPerShot      ; was 0.15, the pre-0.17.3 default
EndIf
```

That guard exists because `GetIniFloat` was once observed returning 0 for an entire session. The
constant beside it was never moved when the default became 0.07 in 0.17.3.

Reachability, checked in `Config::GetHeatPerShot`:

- **With caliber scaling on, the default, it cannot fire.** The result is
  `std::clamp(baseHeat * multiplier, 0.001F, 1.0F)`, so the native never answers zero.
- **With `[CaliberScaling] bEnabled=0` and `fHeatPerShot=0` written by hand, it fires** - MCM's
  slider stops at 0.01, so only an edited ini reaches it - and the barrel then heated at 0.15 a
  shot, more than twice the documented rate, rather than at the 0 that was asked for.

It is now 0.07 and `tools/verify_0200_defaults.py` asserts it, so `fHeatPerShot` is checked in six
places: the MCM control's default, the `Default:` in its help text, `GunHeat.ini`,
`MCM/Config/GunHeat/settings.ini`, the `Config.h` initialiser, and this fallback. Run against the
**0.20.0** archive the same check now fails on the fallback, which makes that release the
regression fixture for it.

## How the compiled script was checked

A `.pex` cannot be verified with a hash. The compiler emits its variable, property, function and
user-flag tables in a different order on every run - two compiles of identical source here differed
in **2,460 of 3,668 bytes** - and the header stores the source path, the user, the machine and two
timestamps. Nor can the shipped file be reproduced: it was compiled in a different directory.

So `tools/diff_pex.py` disassembles two `.pex` with the game's `PapyrusAssembler`, keys each table
by name, renumbers labels in order of first appearance and collapses whitespace outside string
literals. Against the `.pex` inside the 0.20.0 archive it reports **one** difference:

```text
variable heatPerShot:
  - .initialValue 0.150000
  + .initialValue 0.070000

compared {'variable': 7, 'property': 5, 'function': 10, 'userFlag': 6}
```

All 10 functions, 5 properties, 6 user flags and the other 6 variables are identical, and every
`;@line` is unchanged - the edit is one line, so no debug line number moved. The control for the
ordering normalisation is two compiles of the same source, which come back semantically identical.

`tools/compile_papyrus.py` does the compiling, with this workspace's `Source\User` first on the
import path so the game's deployed copies cannot be picked up instead.

## How the DLL was checked

Only `GUNHEAT_VERSION` changed, so the DLL should differ only in version fields. Compared against a
**0.20.0 rebuilt with the same pinned toolchain**, it differs in **11 bytes**:

| Bytes | What |
| --- | --- |
| 1 | the plugin's own version string, `0.20.0` -> `0.20.1` |
| 1 | `F4SEPlugin_Version.pluginVersion`, `0x00140000` -> `0x00140010` |
| 2 | `VS_FIXEDFILEINFO` file and product patch fields |
| 2 | the UTF-16 `FileVersion` and `ProductVersion` strings |
| 5 | the PE timestamp, three debug-directory timestamps, and the PDB age |

`compatibleVersions` still lists `0x010A3D80`, `0x010B0DD0` and `0x010B0F00` - 1.10.984, 1.11.221
and 1.11.240 - and `F4SEPlugin_Query` still admits 1.10.163 only.

Compared against the **shipped** 0.20.0 DLL there is also an 87-byte code region at file offset
`0x5cb0`. Rebuilding 0.20.0 from unchanged source reproduces that same region, so it is link
non-determinism between build sessions, not an effect of the bump. The string `0.20.0` still appears
five times in the DLL: the worktree path, in the PDB reference and in library source paths used by
log messages.

**Not repeated for this release:** the standalone build from the source archive. It was verified at
0.20.0 and the packaging code path, the pins and the build script are unchanged.

## Test checklist

The DLL is the 0.20.0 code with a new version number, so this is a short pass, not the four-runtime
exercise again.

1. Install `GunHeatHaze-0.20.1-heatpershot-default.zip` with no other GunHeat version active,
   deploy, and fully restart the game.
2. `GunHeat.log` should open with `GunHeat v0.20.1` and the same runtime line as before:

   ```text
   GunHeat v0.20.1 on Fallout 4 1.11.240.0 (anniversary runtime)
   ```

3. Fire a sustained burst. It should look exactly as it did on 0.20.0 - the fallback this release
   touches does not run with the shipped settings, so any visible change is a regression.
4. With `bDebugLogging=1`, `caliber heat:` lines should still read `heatPerShot=0.07` at the
   defaults. `Papyrus: LoadIniConfig: heatPerShot=0.070000` appears only if the controller quest
   initialises this session - it will not on a save where the quest is already running. See
   In-game results below.
5. Still outstanding from 0.20.0, unchanged by this release: **1.10.163** as the regression gate
   against 0.17.4, then **1.10.984** and **1.11.221**.

If you want the fallback itself exercised, set `[CaliberScaling] bEnabled=0` and `fHeatPerShot=0`
in `Data\F4SE\Plugins\GunHeat.ini`, delete the `fHeatPerShot` line from
`Data\MCM\Settings\GunHeat.ini` so the overlay cannot win, and fire: the log should report
`heatPerShot=0.07`, where 0.20.0 reported 0.15. Put both back afterwards.

**Send back:** `GunHeat.log` and `f4se.log`, plus the crash log if the game crashes.

## In-game results

### 1.11.240 - passed, 11 September 2026

F4SE 0.7.9 admitted the new build by its new number: `plugin GunHeat.dll (00000001 GunHeat
00140010) loaded correctly`, and the log opened with `GunHeat v0.20.1 on Fallout 4 1.11.240.0
(anniversary runtime)`. A fifteen-minute session wrote 8,527 lines with **no warning, error or
critical line**, and a much wider exercise than the 0.20.0 pass:

| What the log shows | Value |
| --- | --- |
| Shots reported | 989 |
| Weapons | 4 - `0000463F`, `00004822`, `00024F55`, `0004F46A`, all allowed |
| Ammo | 4 - `0001F276`, `0001F278`, `0001F66B`, `0004CE87` |
| Weapon switches | 8, each resetting heat; two of them already cold |
| Art object attaches | **1** for all 989 shots |
| Culled at zero refraction | 27, with 23 attachments parked |
| Plugin CPU | 664 us in the worst second (0.066%), 117-118 Hz against the 125 Hz target |
| Peak refraction | 0.084 at the 0.04 default - 0.036 from heat plus the puff sum |
| Puff overlap | reached the cap of 6 and never passed it |
| Session end | culled, then parked - no stuck effect |

**Caliber scaling, across four real calibers**, which no earlier session had covered:

| Ammo | Damage proxy | Multiplier | Heat per shot |
| --- | ---: | ---: | ---: |
| `0004CE87` | 13 | 0.658 | 0.046 |
| `0001F276` | 18 | 0.775 | 0.054 |
| `0001F278` | 30 | 1.000 | 0.070 |
| `0001F66B` | 37 | 1.111 | 0.078 |

**The checklist's `LoadIniConfig` line did not appear, and that is correct.** `startquest` ran, but
`OnQuestInit` did not: the quest was already running in that save, so the deferred start was a no-op
and the controller's script instance came back from the save with its registration intact - which is
why the shots were still reported. `OnGameLoaded` never runs either; the quest carries no filled
alias, as its own comment says.

That has one consequence worth knowing for the fix in this release. Papyrus stores a script
instance's variables in the save, so an existing save keeps the `heatPerShot` it already had; a new
`.pex` only changes the value a **new** instance starts from. The corrected 0.07 therefore applies on
a new game, or if the quest is ever reset - and since the fallback cannot fire with the shipped
settings at all, nothing about play depends on it either way.

## Rollback

`dist/GunHeatHaze-0.20.0-multi-runtime.zip` is untouched, as is
`dist/GunHeatHaze-0.17.4-puff-overlap-fix.zip`. Install either through Vortex with only one version
active. The pre-0.20.1 snapshot is `Backups/before-0.20.1-heatpershot-default-20260911`, which also
keeps the 1.11.240 logs this release was judged on, since each session overwrites them.
