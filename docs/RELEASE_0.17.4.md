# GunHeatHaze 0.17.4 - puff overlap persistence

Puff overlap returned to 1 after leaving MCM because the setting never registered.
The current session's MCM.log explicitly reports:

> WARNING: ModSetting uPuffMaxOverlap:Haze from mod GunHeat has an unknown type and cannot be registered.

The saved MCM file has no overlap entry. GunHeat.log contains no warning/error
entries and still shows active puff counts up to six; the engine had not adopted
a one-puff limit. This is a settings-registration failure rather than an asset or
heat-cycle regression. The previous defaults audit missed the prefix requirement;
the expanded audit now tests it.

## Cause and fix

[F4SE's Setting::GetType](https://github.com/ianpatt/f4se/blob/master/f4se/GameSettings.cpp)
recognizes i-prefixed integer names and classifies u-prefixed names as unknown.
[MCM's setting store](https://github.com/reg2k/f4mcm/blob/master/src/SettingStore.cpp)
rejects unknown types and returns -1 when an integer setting is missing, consistent
with the slider falling back to its minimum.

The MCM control, default INI and plugin INI now use `iPuffMaxOverlap`.
Default 6, slider range 1-16 and step 1 are unchanged. A narrow Config.cpp change
accepts both the new name and legacy `uPuffMaxOverlap` for hand-written INIs.
The new name wins within one file regardless of line order, while later files
retain their normal override priority. Both names remain available in the DLL's
generic setting lookup. The existing integer parser and 1-24 runtime clamp remain.

All six tuned defaults, pulse/rise slider ranges, mesh, texture, ESP and scripts
are unchanged. The DLL is rebuilt for the compatible key reader only.

## Validation

- Every one of 30 MCM settings (41 control occurrences) has a supported type prefix
  and matching defaults. The new audit explicitly detects the invalid old key in
  the preserved 0.17.3 package, then passes the corrected definition.
- Focused compiled tests execute Trim, ParseUInt and the actual overlap branch
  extracted from production Config.cpp. New/old names, both key orders, repeated
  keys, multiple-file overrides, aliases, bounds, whitespace, invalid values and
  unrelated sections pass. This is not an in-game MCM round trip.
- Isolated MSVC Release build succeeds with game deployment disabled. Only the
  pre-existing /Ob2-to-/Ob3 compiler option warnings remain.
- Full archive comparison requires exactly four changed files: DLL and the three
  configuration files. Configuration content differs only by the key rename.
  The other nine entries, including the accepted asset, match 0.17.3 byte-for-byte.

Reports are in `overlap-0.17.4/mcm-validation.json`, `parser-validation.json` and
`release-validation.json`. Original source/Data, both logs and the saved MCM file
were backed up before edits under `Backups/before-0.17.4-puff-overlap-20260909`.
Earlier versions remain unchanged. The user's live saved settings were not edited:
the attempted overlap selection was never saved and cannot be recovered from it.

## Install and confirm

1. Exit Fallout 4 completely. Install the full
   `GunHeatHaze-0.17.4-puff-overlap-fix.zip` through Vortex, replacing 0.17.3, and
   restart the game so MCM registers the corrected setting name.
2. Set Puff overlap to a distinct value such as 8. Close MCM, reopen it, and check
   that 8 remains. Restart once more and confirm it still remains.
3. The saved `Data/MCM/Settings/GunHeat.ini` should contain `[Haze]`
   `iPuffMaxOverlap=8`. MCM.log should no longer contain the GunHeat unknown-type
   warning. Send the new logs if either check fails.

Until a new selection is saved, the corrected control uses default 6. Your other
saved settings are retained. Unrelated MCM keybind warnings from other mods are
outside this fix. No in-game test was possible here.
