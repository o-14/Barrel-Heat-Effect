Barrel Heat Effect 1.0.0
=======================
Adds subtle heat distortion at your weapon's muzzle after sustained fire.
This Nexus package has the same effect and settings as the 1.0.0 release.

INSTALL
1. Remove older versions, including Gun Heat Haze. Do not enable both.
2. Install this ZIP with Vortex and enable BarrelHeatEffect.esp.

REQUIREMENTS
Use the F4SE version matching your Fallout 4 version:
  Fallout 4 1.10.163: F4SE 0.6.23
  Fallout 4 1.10.984: F4SE 0.7.2 or 0.7.3
  Fallout 4 1.11.221: F4SE 0.7.8
  Fallout 4 1.11.240: F4SE 0.7.9
Also install the matching Address Library for F4SE Plugins.
Mod Configuration Menu (MCM) is optional.

SETTINGS
Use MCM or edit Data\F4SE\Plugins\BarrelHeatEffect.ini.
Heat intensity controls visibility; Heat per shot controls how quickly it builds.
Energy weapons are excluded by default.

Saved MCM settings override the main INI. If an INI edit has no effect, check
Data\MCM\Settings\BarrelHeatEffect.ini. Back it up before making changes.
To keep settings from Gun Heat Haze, rename its MCM settings file GunHeat.ini
to BarrelHeatEffect.ini. Preserve any existing destination file first.

HELP AND SOURCE
https://github.com/o-14/Barrel-Heat-Effect
For a bug report, enable bDebugLogging in the INI, reproduce the problem and
save BarrelHeatEffect.log from Documents\My Games\Fallout4\F4SE before restarting.
Turn debug logging off afterwards.

Source for this DLL: https://github.com/o-14/Barrel-Heat-Effect/tree/v1.0.0
Copyright and licence details are in COPYRIGHT.md and the Licenses folder.
