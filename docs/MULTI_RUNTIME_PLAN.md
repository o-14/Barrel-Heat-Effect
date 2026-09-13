# Multi-runtime plan: 1.10.163 + 1.11.221 + 1.11.240 in one package

Prepared 2026-09-11 from the accepted 0.17.4 worktree (`849e8c7`). **Scope later extended to 1.10.984
(F4SE 0.7.2/0.7.3) at the user's request; the implementation covers four runtimes.** **Investigation only - no
source, build or package was changed.** Implementation waits on the decisions at the end.

## How BPR 3.0.1 does it

One `BPR.dll` (679,424 bytes) serves 1.10.163, 1.11.191, 1.11.221 and 1.11.240. It exports
all four F4SE entry points:

| Export | Read by |
| --- | --- |
| `F4SEPlugin_Query` | F4SE 0.6.23 (1.10.163) - the OG loader calls this |
| `F4SEPlugin_Version` | F4SE 0.7.x (1.11.x) - a data export the loader reads instead of calling Query |
| `F4SEPlugin_Load`, `F4SEPlugin_Preload` | both |

It is built on **Dear-Modding-FO4 `commonlibf4` @ `2aaefd1`** (2026-09-04) with
**`commonlib-shared` @ `e30b310`**. That library:

- carries up to **three relocation IDs per symbol** (OG / NG / AE). A two-entry ID reuses
  its NG value on 1.11.x. **71 of 1,119 IDs were renumbered for 1.11.x.**
- classifies the running exe by file version (`REX::FModule::GetRuntimeIndex`) and fails
  with a clear dialog on unknown versions.
- loads `Data/F4SE/Plugins/version-<exe version>.bin`. For F4SE this is always the flat
  "V0" format, 1.11.x included - so the Address Library *format* is not a blocker.

It ships no Address Library files; the player installs the matching one.

## Why our current CommonLibF4 cannot do this

Our build uses alandtse/CommonLibF4 (`5189b7b`, June 2026, MIT, CMake). Upstream HEAD
`ba22620` (July 28) was checked too - same gaps:

| Gap | Evidence | Consequence on 1.11.x |
| --- | --- | --- |
| No 1.11.x runtimes | constants stop at `RUNTIME_1_10_984` | no AE family at all |
| Only OG+NG IDs | `RelocationID(og, ng)`, no third slot | the 71 renumbered IDs resolve wrong |
| `ApplyArtObject` is OG-only | `REL::ID(357908)` | our delivery call has no NG/AE address |
| Plugin bits are NG-only | `UsesAddressLibrary()` sets `1<<1` | rejected by F4SE 0.7.8/0.7.9 unless listed |

The renumbered IDs include **`PlayerCharacter::Singleton`, `TESDataHandler::Singleton` and
`TESForm::AllForms`** - behind `GetFormByID`, which the tick calls ~125 times a second.
Staying on alandtse would mean maintaining our own 1.11.x ID table for every path CommonLib
touches, with no 1.11.x install to catch a miss. **Recommendation: move to Dear-Modding.**

## What the port touches in our code

**Relocated functions** (Dear-Modding IDs):

| Call | OG | NG / 1.11.x |
| --- | --- | --- |
| `TESObjectREFR::ApplyArtObject` | 357908 | 2205200 (same on 1.11.x) |
| `AIProcess::GetCurrentAmmo` | 1154936 | 2232300 |
| `Console::ExecuteCommand` | 1061864 | 2248537 |
| `PlayerCharacter::Singleton` | 412034 | 2690919 / **4798212** |
| `TESDataHandler::Singleton` | 711558 | 2688883 / **4796135** |
| `TESForm::AllForms` | 422985 | 2689178 / **4796465** |

**Struct offsets: all 20 we read are identical in both libraries** - checked per class, not
by name: `Actor::currentProcess` 300, `AIProcess::middleHigh` 8,
`MiddleHighProcessData::equippedItems` 288, `EquippedWeaponData::fireNode` 30,
`ModelReferenceEffect::artObject3D` C8, `ReferenceEffect::finished` 40,
`BSTempEffect::lifetime` 10, `BSGeometry::properties` 130, `BSShaderProperty::material` 58,
`BSShaderMaterial::texCoordOffset` C, `BSLightingShaderMaterialBase::refractionPower` 84,
`NiAVObject::local/world` 30/70, `NiNode::children` 120, `TESObjectWEAP::weaponData` 198,
`TESAmmo::data` 160, `AMMO_DATA::projectile/damage` 0/10, plus the equipped-item fields.
So the switch should not disturb the working 1.10.163 build.

> **Corrected during the 0.20.0 build.** These figures first came from the `// NN` comments
> in the headers, which are stale in *both* libraries for two fields: `artObject3D` (comment
> 0xD0) and `refractionPower` (comment 0x78). The compiled offsets, probed from the proven
> 0.17.4 build with its exact compiler flags, are 0xC8 and 0x84 - and Dear-Modding compiles to
> the same values. All 24 probed values agree. `src/LayoutChecks.cpp` asserts the compiled ones.

Dear-Modding encodes runtime-specific layouts in only `BSGraphics.h` and `SCRIPT_FUNCTION.h`,
neither of which we use - it treats our classes as identical on all three runtimes.

**Source changes** (2,108 lines total; the rest compiles as-is by name check - 70 distinct RE
method names, all present):

- `NiNode`: `node->GetRuntimeData().children` -> `node->children` at 3 sites. alandtse's
  split is `RelocateMember(this, 0x120, 0x160)` - 0x160 is VR only; same memory.
- `main.cpp`: `F4SE::Init(a_f4se, InitInfo)`; add `F4SEPlugin_Version`; Query accepts only
  1.10.163.
- Logging: Dear-Modding builds spdlog with `std::format`, so `fmt::`/`FMT_STRING` (3 uses)
  go. 58 `logger::` calls keep working through a small shim; the `[%H:%M:%S.%e]` pattern is
  kept because diagnosis depends on it.
- `static_assert` on every offset above, so a future library bump that shifts one fails the
  build instead of the game.

## Declaring exactly the three versions

F4SE 0.7.x accepts a plugin if **either** it declares 1.11.137-era address and layout
independence (`1<<2` bits), **or** the exact runtime is in `compatibleVersions`. Proposed:
`CompatibleVersions({1.11.221, 1.11.240})`, no independence bits. That loads on exactly the
two requested 1.11 builds and refuses 1.11.137/159/169/191, which nobody will have tested.
1.10.163 goes through `F4SEPlugin_Query`, as today.

| Runtime | F4SE | Address Library file |
| --- | --- | --- |
| 1.10.163 | 0.6.23 | `version-1-10-163-0.bin` (installed here) |
| 1.11.221 | 0.7.8 | `version-1-11-221-0.bin` |
| 1.11.240 | 0.7.9 | `version-1-11-240-0.bin` |

## Build

Dear-Modding is **xmake + C++23**; only `commonlib-shared` has a CMakeLists. xmake 3.0.1 is on
this machine but only inside another project's `.tools`; the plan copies a pinned xmake into
this project. First build downloads spdlog 1.16.0 through xrepo. The existing CMake build is
left untouched for the historical line.

## Risks that cannot be closed from here

The installed game is **1.10.163 with only `version-1-10-163-0.bin`**. The OG path is fully
testable; the 1.11.x paths are not.

- Layouts are verified identical *between libraries*, not against a 1.11.x exe. BPR proves
  the fields it uses; `fireNode`, `artObject3D` and `refractionPower` are probably outside
  that set.
- `ApplyArtObject` on 1.11.x relies on Dear-Modding's table saying its NG ID carried over.
- A missing ID fails loudly in a dialog; a wrong-but-present ID would fail silently.

Until tested on a 1.11.x install, release notes should say 1.11.x support is **built but
unvalidated**. MCM on 1.11.x needs an AE build of MCM itself; GunHeat runs without MCM.

## Steps once approved

Each a separate commit; nothing existing deleted.

0. Back up worktree source, DLL and hashes to `Backups/before-<version>-multi-runtime-<date>`.
1. Branch from `849e8c7`.
2. Vendor Dear-Modding at the two pinned commits, plus licenses.
3. Add `xmake.lua` and a pinned xmake.
4. Port as above.
5. Build; verify the four exports and the `F4SEPlugin_Version` bytes with the PE reader
   used on BPR.
6. **Gate: your 1.10.163 regression test** - same look, same logs, same tick cost.
7. 1.11.221 / 1.11.240 tests, if installs can be arranged.
8. Package a complete Vortex archive with licenses and source (see below).

## Decisions needed

1. **Licensing.** Dear-Modding is **GPL-3.0-or-later with the Modding Exception**. Shipping
   a DLL linked to it obliges shipping or offering GunHeat's source under the same license.
   BPR complies by bundling licenses and notices. GunHeat has no license today.
2. **1.11.x testing.** Whether a 1.11.221 and/or 1.11.240 install can be arranged, or
   whether 1.11.x ships marked unvalidated.
3. **Version label.** 0.18.0 and 0.19.0 belong to the archived rejected releases; proposed
   **0.20.0**.

## Handoff review notes

The 2026-09-11 handoff is accurate and was followed. Three additions:

- **0.17.4 is not deployed.** `f4se.log` (2026-09-11 00:57) shows no GunHeat plugin, matching
  the handoff's deployment note. Reinstall before the regression gate.
- "CommonLibF4's build options include multiple runtime families" is true, but the checkout
  stops at 1.10.984 and has no 1.11.x support.
- The embedded DLL version is still 0.1.0. `F4SEPlugin_Version.pluginVersion` should carry
  the real version in the port.
