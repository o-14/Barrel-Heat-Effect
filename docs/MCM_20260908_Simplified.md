# Simplified MCM panel - 0.16.0

Package: `dist/GunHeatHaze-0.16.0-simplified-mcm.zip` (12 files, 347150 bytes)
Full 30-control panel preserved at
`_backup/0.14.0-pre-deadcode-removal/config.json.full-30-controls`.

Data-only change - no DLL or script rebuild. 0.15.0's audit fixes are unchanged and
confirmed working in-game (270 shots, 0 warnings, 0 errors, no hang from the new mutex,
tick steady at ~117/sec and ~650 us per second).

## What changed

| | before | after |
| --- | --- | --- |
| controls | 30 | **11** |
| sections | 7 | **4** |
| help text, average | 170 chars | **53 chars** |
| help text, longest | 325 chars | **68 chars** |
| config.json | 13938 bytes | 3856 bytes |

### The panel now

**Appearance** - Heat intensity, Fade curve, Effect width, Effect height,
Height above barrel
**Behaviour** - Heat per shot, Cool-down at full heat, Reset heat on weapon switch
**Weapons** - All firearms, Exclude energy weapons
**Troubleshooting** - Debug logging

Every label is now a plain noun phrase and every help string is one short sentence ending in
the default, e.g. *"How strong the distortion is. Vanilla Minigun is 0.20. Default: 0.01"*.

### Moved to ini-only (19)

`fArtOffsetForward`, `fMinHeatToShow`, `fFadeInSeconds`, `fFadeOutSeconds`,
`fEffectDurationSeconds`, `fMinFadeOutSeconds`, the smear group (`bSmearEnabled`,
`fSmearGain`, `fSmearMaxOffset`), the pulse and puff group (`bPulseEnabled`,
`fPulseStrength`, `fPulseDecaySeconds`, `fPuffScale`, `fPuffRise`, `fPuffScroll`,
`fPuffVariance`, `uPuffMaxOverlap`), `fScrollTilesPerSecond`, and
`[CaliberScaling] bEnabled`.

**All 19 were verified to still have a live entry in `GunHeat.ini`** - nothing lost its
only home. A signpost at the top of that file lists them and says where they went.

## The trap this had to avoid

MCM writes the settings it manages to `Data\MCM\Settings\GunHeat.ini`, which the DLL
overlays on top of `GunHeat.ini`. Two consequences had to be handled:

**1. MCM's own defaults file was trimmed to match.** `Data\MCM\Config\GunHeat\settings.ini`
listed all 30. If MCM had written defaults for keys no longer on the panel, they would land
in the overlay and permanently override `GunHeat.ini` for **new** users, with no UI to
change them. It now lists exactly the 11.

**2. Existing installs keep stale overlay lines.** A setting changed in MCM before it became
ini-only is still in that overlay and still wins over `GunHeat.ini`. It keeps working and
keeps its value - nothing breaks - but editing `GunHeat.ini` will appear to do nothing until
the line is removed. In the current test install that is 12 lines:

```
[Heat] fFadeInSeconds, fMinFadeOutSeconds, fMinHeatToShow, fFadeOutSeconds,
       fEffectDurationSeconds
[Haze] bPulseEnabled, fPulseStrength, fPulseDecaySeconds, fSmearGain,
       fPuffRise, fPuffScale, bSmearEnabled
```

Those are tuned values, so leaving them is reasonable. To hand control back to
`GunHeat.ini`, delete the individual line, or the whole overlay file to reset everything.

## Verified

Config-consistency audit re-run: no mismatches between `config.json`, `settings.ini`,
`GunHeat.ini` and the C++ defaults; no unparsed ini keys; no MCM id the DLL does not know.
