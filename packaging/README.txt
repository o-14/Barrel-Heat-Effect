Barrel Heat Effect 1.0.0
========================

A weapon's muzzle distorts the air after sustained fire, the way hot metal does.
Refraction only: no glowing barrel, no smoke, no particles, no colour.

It works on every gun, vanilla or modded, with no patching, because it asks the
game itself where the equipped weapon's muzzle is - including whatever barrel mod
you have fitted.


Requirements
------------
- Fallout 4, one of:
    1.10.163  with F4SE 0.6.23
    1.10.984  with F4SE 0.7.2 or 0.7.3
    1.11.221  with F4SE 0.7.8
    1.11.240  with F4SE 0.7.9
- Address Library for F4SE Plugins, the file matching your game version
- Mod Configuration Menu - optional, only for the settings panel

One BarrelHeatEffect.dll covers all four game versions. F4SE will refuse it on
any other
version on purpose, because those have not been tested.


Installing
----------
Install with a mod manager. Remove any older version first - including Gun Heat
Haze, which this mod used to be called - and never run two at once.

Manual install: extract the archive contents into your Fallout 4 Data folder and enable
BarrelHeatEffect.esp.

To uninstall, remove it with your mod manager. The effect stops and no setting or
world change is left behind. Like any mod with a script, a save that has already
run it keeps a reference to that script; it does nothing and harms nothing, but if
you keep strict clean saves, uninstall between playthroughs rather than mid-one.


Checking it works
-----------------
Fire ten or more shots in quick succession and watch just past the muzzle. The
distortion builds while you fire and fades over roughly twenty seconds. It is
meant to be subtle - if you cannot see it at all, fire a longer burst against a
bright background, or raise Heat intensity.

Energy weapons are skipped by default: lasers, plasma, gamma, cryo, gauss and the
alien blaster. The Minigun is ballistic, so it does get the effect.


Settings
--------
Everything can be set in:
  Data\F4SE\Plugins\BarrelHeatEffect.ini
That file explains each setting, and none of it needs MCM.

With Mod Configuration Menu installed, the panel puts the settings most worth
changing mid-game on its first page and the rest on an Advanced page.

If you change something in MCM, that value is saved to
Data\MCM\Settings\BarrelHeatEffect.ini and applied on top of the ini above - so
editing the
ini afterwards can look like it does nothing. Delete the line from the MCM file,
or the whole file, to hand the setting back to the ini.

The four worth knowing:
  Heat intensity        how strong the distortion is (0.04)
  Heat per shot         how quickly a barrel heats up (0.07)
  Height above barrel   how far off the barrel it sits (1)
  Cool-down at full     how long a fully hot barrel takes to cool (20 s)


Compatibility
-------------
- Works with weapon mods, including ones that add their own barrels, because the
  muzzle position comes from the game rather than from a list of known weapons.
- The shimmer is the game's own refraction effect, the same kind the Minigun uses,
  so it goes through whatever your ENB or reshade does with vanilla heat shimmer.
- The plugin adds two records of its own and edits nothing that already exists,
  so it cannot conflict with weapon, ammo or balance mods.
- Adding it mid-playthrough is safe.
- Costs about half a millisecond of CPU per second while a barrel is hot, measured
  on 1.10.163, and idles the rest of the time.


Reporting a problem
-------------------
Set bDebugLogging=1 in Data\F4SE\Plugins\BarrelHeatEffect.ini, play until you
see the
problem, then send:
  Documents\My Games\Fallout4\F4SE\BarrelHeatEffect.log
  Documents\My Games\Fallout4\F4SE\f4se.log
and a crash log if the game crashed. Both files are rewritten each time the game
starts, so grab them before your next session. Turn logging back off afterwards;
it writes about a megabyte per session.


Version history
---------------
1.0.0 cleanup - Removed build-machine metadata; no gameplay change.
1.0.0   - First public release, numbered 1.0.0 from the private 1.1.0 build.
          Version metadata and release documentation only; the effect is unchanged.
Private 1.1.0 - Renamed from Gun Heat Haze to Barrel Heat Effect. THIS NEEDS A CLEAN
          REINSTALL: the plugin, the settings file and the MCM panel all have new
          names, so remove the old version before installing this one, and enable
          BarrelHeatEffect.esp in your load order.
          To keep settings you changed in MCM, rename
          Data\MCM\Settings\GunHeat.ini to BarrelHeatEffect.ini; otherwise the
          panel starts from the defaults again. Nothing about the effect changed.
Private Gun Heat Haze 1.0.0 - First stable release. Removed an unused record left over from an
          abandoned experiment; the plugin now adds two records instead of three.
          Existing saves are unaffected - nothing referenced it.
0.21.0  - Settings file rewritten in plain language, with every value unchanged.
          f4se.log now names the build on Fallout 4 1.10.163 as well.
0.20.2  - Pattern drift default raised to 0.7 tiles per second, from 0.6.
          Confirmed in game on 1.10.163 and on 1.11.240.
0.20.1  - Fixed a heat-per-shot fallback that still held an old default. It only
          applied with caliber scaling off and heat per shot hand-edited to 0.
0.20.0  - One DLL for all four supported game versions, rebuilt on Dear Modding
          FO4's multi-runtime CommonLibF4. The log now records the game version
          and runtime at startup.


Credits and license
-------------------
Barrel Heat Effect - Copyright (C) 2026 o14

Licensed under the GNU General Public License version 3 or later, with additional
permissions. See COPYRIGHT.md, THIRD_PARTY_NOTICES.md and the Licenses folder.
Corresponding source (including pinned dependencies):
https://github.com/o-14/Barrel-Heat-Effect/tree/v1.0.0

The distortion texture and mesh are derived from Fallout 4's own assets and remain
Bethesda's; they are not covered by the GPL. COPYRIGHT.md says which files.

Built on CommonLibF4 (Dear Modding FO4's fork) and spdlog. F4SE and Address
Library are required but not included.
