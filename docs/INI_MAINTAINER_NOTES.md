# Why the settings are what they are

`Data/F4SE/Plugins/GunHeat.ini` was rewritten for players in 0.21.0. Its comments used to carry the
engineering reasoning behind each group, which a player has no use for but a maintainer does. That
reasoning is here. Nothing was lost: the 0.20.2 file is in git history and in
`Backups/before-0.21.0-end-user-release-20260911/`.

**No value changed in that rewrite.** The packager's `--baseline` check and a parse-and-compare
confirmed all 45 settings, and their order, are identical to 0.20.2.

## How the effect is delivered

The effect is an engine-owned art object, applied with `TESObjectREFR::ApplyArtObject` and attached
to the weapon's muzzle node. The engine owns positioning, cell and 3D swaps, save-load and teardown;
the DLL only drives refraction strength. That decision, and the disassembly it came from, is in
`docs/GhidraFindings_20260806_ApplyArtObject.md`.

- `sArtObjectPlugin` / `sArtObjectFormID` name the ARTO record in `GunHeatHaze.esp`, which points at
  `Meshes/GunHeatHaze/GunHeatBarrelRefractionCard.nif`.
- `bPreferFireNode=1` uses `EquippedWeaponData::fireNode`, the node the engine itself resolves for
  the equipped weapon including its attached mods. This is what makes the effect universal across
  vanilla and modded guns with no per-weapon patching. `0` falls back to a name-based muzzle search.
  Either way the chosen node is logged.

## The heat curve, and why the numbers are not obvious

`[Heat]` was retuned on 2026-08-06 because the earlier values could never reach `fMinHeatToShow` at
any realistic fire rate. Heat decays at `1/fadeOutSeconds`, and `fadeOutSeconds` scales with peak
heat, so a **cold barrel cooled fastest**. With `fHeatPerShot=0.035` and `fMinFadeOutSeconds=2.0` the
decay was about 0.46 heat per second against roughly 0.027 gained per shot, which needed about
1023 RPM just to break even: 1,030 logged shots never crossed the threshold.

So `fMinFadeOutSeconds` is not only the short-burst cool-down - it is the **cooling rate while heat
is still building**, and has to be long enough that sustained fire can out-pace it.

`fMaxFadeOutSeconds=20` is why a full barrel stops shimmering about 19 seconds after the last shot:
heat falls 1.0 to the 0.05 threshold in 19 s, which the 1.10.163 session measured at 19.6 s.

`fVisibilityCurve` below 1.0 keeps the shimmer readable further into the cool-down without raising
the peak: the cool-down always runs its configured length, but linear falloff makes the tail
imperceptible roughly two thirds of the way through.

## Card geometry

Offsets are in the muzzle node's own space: Y forward along the barrel, Z up. The card is about
20.6 units tall on screen, so `fArtOffsetUp=3` sits it just clear of the muzzle; the shipped default
is 1. `fSizeWidth` and `fSizeHeight` are multipliers in the billboarded plane, against an authored
size of roughly 10 x 20 units, and are live - no mesh rebuild.

## Pulse and puffs

`bPulseEnabled` was marked EXPERIMENTAL when added and has been on by default since. The bump is
scaled by current heat, so it does nothing cold and is strongest on a hot barrel, and it only fires
into a cycle that is already running - never on the shot that starts one.

Puffs sum rather than restarting a single bump, which is what makes sustained fire roll into a
continuous billow. `iPuffMaxOverlap` caps how many are alive; the 0.17.4 release exists because that
key shipped as `uPuffMaxOverlap` in 0.17.3 and MCM cannot register a `u` prefix.

`fPuffRise` moves the whole card; `fPuffScroll` moves the texture pattern within it.

## Scroll

`fScrollTilesPerSecond` is owned by the DLL rather than the NIF's own V-offset controller, so the
rate is configurable and puffs can add to it. `bDriveScroll=0` hands it back to the NIF. 0.6 matches
the vanilla Minigun; 0.21.0 ships 0.7, chosen in game over 0.6 and 0.8 - see
`docs/RELEASE_0.20.2.md`.

## Energy-weapon exclusion

Energy weapons are typed `WEAPON_TYPE::kGun` exactly like ballistics, so nothing on the weapon record
separates them. The loaded ammo does, and matching on ammo also covers modded weapons, which
overwhelmingly reuse the vanilla energy ammo. The built-in FormID list was read out of `Fallout4.esm`
with `tools/dump_ammo_records.py`.

`sEnergyAmmoFormIDs` **replaces** the built-in list rather than adding to it, so a load order with its
own energy ammo can be described exactly; an empty value disables the filter.

This does not exclude the Minigun, which fires `Ammo5mm` (`0001F66C`) and is ballistic. The allowlist
is opt-in only, so today the only way to exclude the Minigun is `bAllowAllWeapons=0`.

## The MCM overlay

MCM writes what the player changes to `Data/MCM/Settings/GunHeat.ini`, and the DLL overlays that file
on top of this one. A setting changed in MCM before it became ini-only still has its old value in
that overlay, and the overlay keeps winning. Deleting the line, or the file, hands control back.

Every default is written in five places and `tools/verify_0200_defaults.py` asserts they agree:
`GunHeat.ini`, the MCM control's `default`, the `Default:` in its help text,
`MCM/Config/GunHeat/settings.ini`, and the member initialiser in `Config.h`. `fHeatPerShot` has a
sixth, the Papyrus fallback in `GunHeatController.psc`, which is also asserted - it drifted once and
0.20.1 fixed it.
