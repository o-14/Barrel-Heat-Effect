# 0.17.0 - advanced page, new size defaults, duration verification

Package: `dist/GunHeatHaze-0.17.0-advanced-page.zip` (12 files, 348407 bytes)
DLL 773120 bytes.

## Duration verified against settings

Measured from the 0.16.0 session (650 shots, 5 complete cycles) by pairing `card shown` /
`card culled` / `parking attachment` against shot timestamps.

| state | measured | what governs it |
| --- | --- | --- |
| build-up (first shot to visible) | 0.10 - 0.22s | `fFadeInSeconds`, and heat crossing `fMinHeatToShow` |
| visible | as long as you keep firing | - |
| **fade-out (last shot to invisible)** | **19.07 / 19.09 / 19.12s** | `(1.0 - fMinHeatToShow) x fMaxFadeOutSeconds` |
| invisible to parked | 0.88 - 0.92s | heat finishing its decay after the visual hits zero |
| parked | indefinite, zero cost | culled, next shot reuses it |

With the live settings (`fMaxFadeOutSeconds=20`, `fMinHeatToShow=0.05`) the prediction is
`0.95 x 20 = 19.00s`. **Three cycles measured 19.07, 19.09 and 19.12** - within 0.12s.

Two outliers, both explained and both correct:

- **13.42s** on the first cycle. That ran before `fMaxFadeOutSeconds` was raised from 14 to
  20 mid-session; `0.95 x 14 = 13.3s`.
- **51.58s** on the fourth. That window contains menu time. The DLL clamps per-tick elapsed
  to 0.25s and ticks only run on the game thread, so heat does not decay while the game is
  paused - wall-clock time inflates but simulated cool-down does not. Correct behaviour.

A third apparent anomaly was mine, not the mod's: an early version of the analysis paired a
mid-cycle cull (refraction dipping below the 0.0001 cull threshold between bursts, then
returning 0.255s later) with the end of the cycle.

Scaling at other peaks, for reference: peak 1.0 -> 19.0s, peak 0.5 -> 6.3s, one shot at
0.15 -> ~1.0s.

## New defaults

`fSizeWidth` 1.0 -> **0.8**, `fSizeHeight` 1.0 -> **0.5**, changed in all four sources of
truth (`Config.h`, `GunHeat.ini`, MCM `settings.ini`, `config.json`) so the consistency
audit stays clean. Existing installs are unaffected: the MCM overlay already holds the
player's own 0.8 / 0.5.

## Advanced page

`config.json` now carries **two pages** - "Settings" (the 11 core controls) and "Advanced"
(the 19 that had moved to ini-only), grouped as Timing, Placement, Movement, Puffing and
Weapons. All 30 use the short one-line help style: average 46 characters, longest 68.

**This could not be verified locally.** Every other MCM mod in this install is Vortex-
managed, so no other `config.json` is on disk to confirm the schema, and MCM's own
`MCM.psc` is only 57 lines of native API - the schema lives inside `MCM.swf`.

So the file is written to degrade safely: it carries **both** `pages` and a top-level
`content` holding exactly the core page. Outcomes:

- **Two page tabs, "Settings" and "Advanced"** - `pages` is supported; this is the goal.
- **A single 11-control panel, as in 0.16.0** - `pages` was ignored and `content` was used.
  Nothing is broken, and the 19 stay editable in `GunHeat.ini`.
- **An empty or broken panel** - neither key was understood. Revert by deleting the `pages`
  key; `content` alone is the known-good 0.16.0 layout.

Please say which of the three you see.

`settings.ini` was deliberately **not** expanded back to 30. It is MCM's defaults file, and
listing keys there that the panel might not manage is what could write a stale value into
the overlay and permanently override `GunHeat.ini`. The advanced controls take their
defaults from `config.json`, and untouched controls write nothing at all.

## Verified

All 30 controls across both pages cross-checked: defaults agree between `config.json`,
`GunHeat.ini` and the C++ members, every default sits inside its slider range, and every one
has a live `GunHeat.ini` entry. Build clean, dead-accessor scan clean.

## Note

While changing the size defaults I truncated `Config.h` to zero bytes with a bad
read-and-write one-liner (`open(p,'w')` truncates before the read argument is evaluated).
It was restored from `_backup/0.14.0-pre-deadcode-removal/Config.h` and the three
intervening changes re-applied; the rebuilt DLL is byte-identical in size and both audit
scans pass. This is the second time this session that the absence of version control turned
a one-character slip into a recovery exercise - `git init` remains worth doing.
