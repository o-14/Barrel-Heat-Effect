# 0.17.1 - Advanced page settings now persist

Package: `dist/GunHeatHaze-0.17.1-mcm-defaults-fix.zip` (12 files, 348785 bytes)
Data-only; DLL and scripts unchanged from 0.17.0.

## The two-page layout works

Confirmed by use - the Advanced page rendered and its sliders were reachable. That answers
the open question from 0.17.0: this MCM build supports `pages`.

## Why Advanced settings reverted

The overlay MCM wrote tells the whole story. Of the nineteen Advanced controls, the ones
that persisted were **exactly** those that already had a value in
`Data\MCM\Settings\GunHeat.ini` from the old 30-control panel. The seven that reverted -
`fArtOffsetForward`, `fPuffScroll`, `fPuffVariance`, `fScrollTilesPerSecond`,
`fSmearMaxOffset`, `uPuffMaxOverlap` and `[CaliberScaling] bEnabled` - were in **neither**
the overlay nor `Data\MCM\Config\GunHeat\settings.ini`.

MCM needs a default in `settings.ini` to initialise a control. With none it has nothing to
show (hence the `-1` on the placement slider) and nothing to persist into.

This was a regression I introduced. 0.16.0 trimmed `settings.ini` to the eleven core
controls to stop MCM writing stale defaults into the overlay - correct while only eleven
were on the panel. When 0.17.0 put the other nineteen back on an Advanced page, that trim
became the bug, and the 0.17.0 notes recorded it as a deliberate choice instead of
rechecking it.

## Fix

`settings.ini` is now **generated from `config.json`**, so the defaults file cannot drift
from the panel again. All 30 controls, five sections. The file header states the rule that
was violated.

Verified: all 30 panel controls exist in both `settings.ini` and `GunHeat.ini`, with
defaults matching the panel in all three places.

## Weapon transfer - working

```
18:00:13.979  muzzle node changed ('ProjectileNode' -> 'ProjectileNode'), art object re-applied
18:00:17.970  weapon changed (0000463F -> 00004822); resetting heat from 0.68559825
18:00:34.646  muzzle node changed ('ProjectileNode' -> 'ProjectileNode'), art object re-applied
18:00:36.552  weapon changed (00004822 -> 000DC8E7); resetting heat from 0.5420969
```

Two switches across three weapons, two resets, two re-applies, one attach for the whole
373-shot session, 0 warnings, 0 errors. The node name is identical each time because every
weapon calls its muzzle `ProjectileNode` - the pointer differs, which is what the re-apply
keys on, and is exactly why the heat reset keys on the **weapon form id** instead.

## After installing

Your overlay still lacks the seven keys until you touch those sliders; `GunHeat.ini`
supplies their values in the meantime. Open the Advanced page, change one, leave the menu
and come back - it should now hold.
