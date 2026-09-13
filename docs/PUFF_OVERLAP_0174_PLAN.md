# 0.17.4 puff-overlap persistence fix - plan before implementation

The user reports Puff overlap returning to 1 after closing MCM. The latest
MCM.log gives the root cause: uPuffMaxOverlap:Haze has an unknown type and cannot
be registered. The saved MCM overlay contains no overlap key; GunHeat.log shows
the original six-puff limit still operating, not a new one-puff runtime setting.

MCM uses F4SE Setting::GetType: integer names start with i, while u is unknown.
Its missing integer getter returns -1, consistent with a slider returning to its
minimum. The previous defaults/coverage check missed this type-prefix constraint.

Back up 0.17.3 source/Data, GunHeat.log, MCM.log and the user's saved settings before
edits. Preserve the accepted mesh, texture, six tuned defaults and slider ranges.

1. Rename the MCM integer key to iPuffMaxOverlap:Haze, with matching generated
   settings.ini and plugin INI. Retain default 6 and slider 1-16, step 1.
2. Add a narrow Config.cpp compatibility alias: read the new integer key and the
   old uPuffMaxOverlap key. The new key wins over the legacy key within one file,
   regardless of line order; later files retain existing override priority.
   Keep the existing unsigned parser and 1-24 runtime clamp. Store both names in
   the generic lookup map so callers of the legacy key remain compatible.
3. Extend MCM audits to reject unsupported/mismatched sourceType/name prefixes
   for every control, and demonstrate that this check catches the old definition.
   Test the actual production key-reading branch and parser outside the engine:
   new/legacy keys, both orders, file precedence, invalid input and clamp limits.
4. Build in the isolated worktree with deployment disabled. Package the complete
   GunHeatHaze-0.17.4-puff-overlap-fix.zip. Only DLL and the three configuration
   files may differ from 0.17.3; assets, ESP and scripts must match byte-for-byte.

Do not fabricate the user's attempted overlap choice: it was never saved. Keep
their MCM overlay untouched. The fixed control will initialize from default 6
until they choose and save another value. Require a full game restart after
installing so MCM registers the renamed setting. Test selecting 8, closing and
reopening MCM, then restarting: the chosen value should remain and appear under
[Haze] iPuffMaxOverlap in the saved overlay. Check that the unknown-type warning
is gone. No in-game test can be performed here.

Commit plan, fix and release separately. No earlier source or archive is replaced.
Primary references:
https://github.com/reg2k/f4mcm/blob/master/src/SettingStore.cpp
https://github.com/ianpatt/f4se/blob/master/f4se/GameSettings.cpp
