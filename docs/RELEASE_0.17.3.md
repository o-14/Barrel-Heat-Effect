# GunHeatHaze 0.17.3 - tuned defaults

The user accepted the 0.17.2 effect in game. This release preserves its mesh and
texture byte-for-byte and adopts the requested defaults and MCM slider ranges.

| Setting | Default | Slider range | Step |
| --- | ---: | --- | ---: |
| Heat intensity | 0.04 | unchanged | unchanged |
| Height above barrel | 1 | unchanged | unchanged |
| Heat per shot | 0.07 | unchanged | unchanged |
| Pulse strength | 0.01 | 0.005-0.050 | 0.005 |
| Puff expansion | 0.1 | unchanged | unchanged |
| Puff rise | 0.5 | 0-1 | 0.1 |

All four default sources agree: compiled Config.h defaults, plugin INI, MCM
config.json and generated MCM settings.ini. Both duplicate fallback controls and
help text were updated. All 30 MCM settings have valid defaults; the 41 control
occurrences agree. Both changed sliders can reach their endpoints and defaults.

The DLL was rebuilt only to update six compiled fallback constants. Runtime
logic, clamps, heat/cooling behavior, Papyrus and attachment handling are unchanged.
The source list's stale reference to nonexistent ProjectileEmitter.h was removed
to allow a clean build; no source file was deleted. The package version is 0.17.3;
the embedded project version stays 0.1.0 under the existing convention.

## Test-session review

Reviewed the 2026-09-09 session from 10:48:09 to 11:26:15. The installed mesh,
normal map and DLL matched 0.17.2. F4SE reported GunHeat loaded correctly.

- 20,346 GunHeat log lines; no warning/error/critical entries.
- 2,354 AddHeat shots, 40 completed cooling/parking events, 58 cull messages and
  7 weapon-change heat resets. These show the expected lifecycle operating.
- 1,473 tick samples: median 118 Hz, median 471 microseconds of recorded tick
  work per second, 95th percentile 531 microseconds, worst individual tick 244
  microseconds. These are plugin CPU timings, not frame-rate/GPU measurements.
- MCM overrides loaded 414 times. Late-session refraction range is (0, 0.04).
  Heat per shot 0.054221768 with a 0.7745967 caliber multiplier confirms the
  requested base 0.07. Puff scale capped at 0.3 is consistent with saved 0.1.
- Height 1 and puff rise 0.5 were saved in the MCM overlay and handled by its
  loader. Their resulting transforms are not directly printed in this log.
- Pulse strength was saved as 0.02, with the observed 0.06 puff cap consistent
  with that value. After backup, that one saved key was corrected to requested
  0.01. Every other saved preference was preserved. All six requested saved values
  now match; the corrected pulse value awaits the next game session for runtime
  confirmation.

The final session ends while cooling, so it does not establish completion of that
last cycle. Earlier cycles do show culling and parking. Debug logging was enabled
by the user and remains so in their saved overlay; shipped debug defaults remain off.

## Build, package and preservation

MSVC Release build succeeded in the isolated worktree with COPY_BUILD=OFF. The
only compiler warnings were existing /Ob2-to-/Ob3 option overrides. No Fallout 4
run of the rebuilt DLL or new slider UI was performed here.

`GunHeatHaze-0.17.3-tuned-defaults.zip` is the complete 13-file Vortex mod,
677,124 bytes. SHA256:
`5cbd4d788943d9c069df96e88563a0f186b39694498f434602e79e104cd0303b`.

Compared with 0.17.2, only these four files differ: F4SE/Plugins/GunHeat.dll,
F4SE/Plugins/GunHeat.ini, MCM/Config/GunHeat/config.json and
MCM/Config/GunHeat/settings.ini. The other nine files match exactly. Neither
the saved MCM overlay nor debug logs are packaged.

Before edits, 238 accepted source/Data files were archived and read back with
hash verification. Separate accepted mesh/texture copies, the test log and the
pre-change saved MCM file are preserved in the original project's
`Backups/before-0.17.3-tuned-defaults-20260909`. Older versions remain untouched;
0.18.0/0.19.0 stay archived.

Install 0.17.3 through Vortex to receive the new defaults and sliders. Check that
pulse reaches 0.005 and 0.050, and puff rise moves by 0.1 between 0 and 1. Existing
user settings normally override defaults; the six local saved values have already
been verified/corrected as described above. No blanket reset is needed.

To restore the earlier package, re-enable 0.17.2 in Vortex. The separate MCM
backup is available if the saved pulse correction also needs undoing.

Detailed measurements: `defaults-0.17.3/test-session-review.json`,
`config-verification.json`, `saved-override-correction.json` and
`release-verification.json`.
