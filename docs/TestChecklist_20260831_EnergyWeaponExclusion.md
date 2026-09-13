# Test checklist - 0.14.0 "energy weapon exclusion"

Package: `dist/GunHeatHaze-0.14.0-energy-weapon-exclusion.zip` (13 files, 497371 bytes)
DLL: 806912 bytes. Proven 0.11.4 sources at `_backup/0.11.4-proven/`.

## Why it is matched on ammo

Energy weapons are `WEAPON_TYPE::kGun` (9) - the same type as every ballistic firearm - so
nothing on the weapon record separates them. The previous filter was:

```cpp
return allowAllWeapons_ && a_weapon->IsGunWeapon();
```

which passes laser, plasma, gauss, cryo, gamma, alien blaster and the Gatling laser exactly
like a 10mm.

The loaded ammo does distinguish them, and matching there also covers modded weapons, which
overwhelmingly reuse the vanilla energy ammo rather than shipping their own.

## The FormIDs are extracted, not remembered

A wrong FormID in this list fails silently in both directions - an energy weapon still
heats, or a ballistic one stops. So they were read out of `Fallout4.esm` with the new
`tools/dump_ammo_records.py` (58 AMMO records scanned):

| FormID | EditorID | weapon |
| --- | --- | --- |
| `000C1897` | AmmoFusionCell | laser weapons |
| `000AB4FE` | AmmoFusionCellEyebot | |
| `001262F2` | AmmoFusionCellLtBlue | |
| `0001DBB7` | AmmoPlasmaCartridge | plasma weapons |
| `00075FE4` | AmmoFusionCore | Gatling laser |
| `001BBFCA` | AmmoFusionCoreNoSteal | |
| `00178D66` | AmmoFusionCoreMeltdown | |
| `000865EA` | AmmoFusionCoreKnightMeltdown | |
| `0018ABE2` | AmmoCryoCell | Cryolator |
| `000DF279` | AmmoGammaCell | Gamma gun |
| `001025AA` | AmmoAlienBlaster | Alien blaster |
| `0018ABDF` | Ammo2mmEC | Gauss rifle |

## The Minigun is NOT excluded

You named the Minigun as an energy weapon, but it fires `Ammo5mm` (`0001F66C`) and is
ballistic - the energy gatling weapon is the **Gatling Laser**, which takes a fusion core
and is excluded. The Minigun keeps its barrel heat, which is arguably right given it is the
weapon whose vanilla effect this mod is modelled on.

If you want it excluded too, say so - the allowlist is opt-in only, so there is currently no
way to block a specific ballistic weapon without setting `bAllowAllWeapons=0`. That would
need a blocklist, which is a small addition.

Judgement calls worth reviewing:

- **Gauss rifle (`Ammo2mmEC`) is excluded.** It is electromagnetic but fires a physical
  slug, so it is arguable either way. Drop `0018ABDF` from `sEnergyAmmoFormIDs` to keep it.
- **Flamer (`AmmoFlamerFuel`, `000CAC78`) is NOT excluded.** It is chemical rather than
  energy, and a flamer barrel plausibly does get hot. Add it if you disagree.
- **Missiles and mini nukes are NOT excluded** - launchers, not energy weapons.

## Settings

`[Weapons] bExcludeEnergyWeapons=1` (default on), also in MCM as **"Exclude energy
weapons"**. `sEnergyAmmoFormIDs` overrides the built-in list outright - setting it replaces
rather than appends, so a load order with its own energy ammo can be described exactly. An
empty value disables the filter.

## Verify

1. **Laser rifle / laser pistol** - fire a sustained burst. No shimmer. With
   `bDebugLogging=1`:

   ```
   IsWeaponAllowed: weapon 0009DBC3 excluded, energy ammo 000C1897
   ```

2. **Automatic laser** - same, since the filter runs per shot on the equipped ammo.
3. **Gatling laser** - no shimmer (fusion core).
4. **Alien blaster, gamma gun, cryolator, plasma** - no shimmer.
5. **Gauss rifle** - no shimmer by default; confirm that is what you want.
6. **Ballistic regression** - 10mm, assault rifle, combat rifle and **Minigun** must still
   build heat exactly as before.
7. **Toggle off** - set the MCM switch off and confirm energy weapons heat again.

## Note

Untested by me: no energy weapon has ever appeared in a session log - every logged shot so
far has been `Ammo10mm` or `Ammo556`. Step 1 is the one that matters most.
