# Full integrity audit - 2026-09-07

Audited at 0.14.0 (DLL 806912 bytes). Method: mechanical cross-checks rather than reading
alone - a config-consistency differ across all four sources of truth, a dead-accessor
scanner, a Papyrus call-graph reachability pass, ESP/NIF binary decode, and a numeric sweep
of the heat curve across every MCM slider's full range. Scripts in the scratchpad.

## Verified sound

- **DLL and all three .pex are current** with their sources.
- **No ini key goes unparsed, and no MCM slider id is unknown to the DLL.** Every id in
  `config.json` maps to a real parser branch; every key in `GunHeat.ini` is read.
- **The player's live MCM settings are all within their slider ranges.**
- **`fMinFadeOutSeconds > fMaxFadeOutSeconds` is handled** - `Finalize()` swaps them, and
  the sweep confirms the swapped case behaves identically to the ordered one.
- **Every division is guarded.** `fadeOutSeconds` and `rampSeconds` both floor at `0.01`,
  and `std::pow` only ever sees a non-negative base.
- **The heat curve is well behaved across the slider extremes** - 0.95s for a single shot
  at defaults, 13.4s at full heat, 2.2s at minimum cool-downs, 38.1s at maximum.

## Critical

### 1. `Config` is shared across two threads with no synchronisation

Writers and readers are on different threads and there is no mutex anywhere in `Config`:

| | thread | frequency |
| --- | --- | --- |
| `AddHeat` -> `ReloadOverrides()` | game | <=1/sec (throttled) |
| `GetHeatSetting` -> `ReloadOverrides()` | **Papyrus VM** | on quest init / game load |
| `Load()` | game | on each game load |
| `IsWeaponAllowed`, `GetHeatPerShot`, `GetIniFloat` | **Papyrus VM** | every shot |
| `Tick` / `SetStrengthLocked` | game | ~125/sec, ~20 reads each |

`ParseKey` writes `floats_` (a `std::unordered_map`, 72 insertion sites) plus the
`energyAmmo_` and `allowedWeapons_` sets. A concurrent insert-and-rehash while another
thread traverses those containers is undefined behaviour, not a benign data race.

This is the one finding with genuine crash potential. Probability is low per-shot - the
write side is throttled to once a second - but it accumulates over a long session and would
present as a rare, unattributable crash.

Fix: a `std::shared_mutex` in `Config`, exclusive around `ParseFile`/`Finalize`, shared
around the accessors. Roughly a 30-line change.

## Functional defects

### 2. The quest still has no alias - confirmed from the ESP binary

`QUST 01000800` decodes to exactly `EDID`, `VMAD`, `FULL`, `DNAM`, `NEXT`. No `ALST`/`ALLS`
alias records at all. So `PlayerAlias.psc` can never attach, `OnPlayerLoadGame` never fires,
and `GunHeatController.OnGameLoaded()` has zero call sites.

This is worked around - the DLL clears state on `kGameLoaded` and the cycle no longer keeps
persistent state in the save - so nothing is currently broken by it. But `PlayerAlias.pex`
ships as a guaranteed no-op, which is misleading to anyone reading the mod.

### 3. MCM permits a silently non-functional configuration

`fHeatPerShot` goes down to `0.01` and `fMinHeatToShow` up to `0.6`. At that combination
heat can never reach the threshold at any fire rate, because decay outruns accumulation -
the sweep confirms zero visible time and zero peak refraction. The mod appears broken with
no error anywhere. Either clamp the threshold against heat-per-shot in `Finalize()`, or
narrow `fMinHeatToShow`'s range.

## Dead surface

### 4. Nine settings are documented and logged but read by nothing

`bAttachEnabled`, `sAttachNode`, `bExtractGeometry`, `sHazeArt`, `fScrollScale`,
`fTimerInterval`, `bStartController`, `sAnimationSequence`, `fAnimationMinSpeed` /
`fAnimationMaxSpeed`.

`bAttachEnabled` is the harmful one: **the shipped `GunHeat.ini` sets it to `0`**, which
reads as "attachment is disabled" while `AddHeat` attaches unconditionally. `fTimerInterval`
became dead when the Papyrus timer was removed in 0.12.0, and the ini still describes it as
the heat tick rate.

All ten still appear in the giant `config loaded:` log line, which makes that line actively
misleading during diagnosis.

### 5. `ProjectileEmitter` is unreachable - 521 lines plus ~20 settings

`Emit()` is called only from the `SetHazeStrength` native, which is called only from
Papyrus `ApplyHeat()`, which is called only from `StartHaze()` and `UpdateHeat()` - both
dead since 0.12.0. It is disabled by config *and* unreachable by call graph.

### 6. Dead Papyrus cluster

`StartHaze`, `UpdateHeat`, `GetCurrentFadeOutSeconds`, `ApplyHeat`, `GetHazeStrength`,
`StopHaze`, `OnGameLoaded` - all unreachable. They still compile into the shipped `.pex`
and still reference `timerInterval`, `visualFadeOutSeconds` and friends, which makes the
script read as if Papyrus still owns the heat curve. It does not; the DLL does.

## Packaging

### 7. The shipped texture is never referenced by the shipped mesh

`Textures/Effects/HeatHazeFlowTile_n.dds` is **262272 bytes - 53% of the 497 KB package** -
and `GunHeatBarrelRefractionCard.nif` does not use it. Its texture set points at vanilla
`textures\Effects\SmokeVapor01Tile_n.dds` for both slots. The only files referencing our
texture are `GunHeatRefractionOnlyStrong.nif` and its backups, none of which ship.

Either repoint the card's texture set at it or drop it from the manifest. As shipped it is
pure dead weight.

### 8. The ESP carries the retired PROJ record

`PROJ 01000801` is 215 of the ESP's 705 bytes and belongs to the abandoned projectile
carrier. Harmless, but it is a live form id in a shipped plugin for a system that no longer
exists.

## Process

### 9. The repository has zero commits

`git rev-list --all --count` is 0 and no files are tracked. Every source file, the ESP, the
authored NIF and all the tooling exist only as working-tree files. The sole recovery path is
`_backup/0.11.4-proven/` and the `dist/` zips - neither of which covers the tools, the ESP,
or the NIF's authoring history.

This is the largest practical risk in the project. A single bad `python - <<PY` overwrite
loses work with no way back.

## Lower severity

### 10. The pacer thread never exits

`StartPacer` launches a detached `for (;;)` thread with no stop condition. It keeps polling
at 10 Hz at the main menu with no game loaded, and at process teardown it can touch
`HazeManager::Get()`'s function-local static and the F4SE task interface after static
destruction has begun. Fallout 4 usually terminates hard enough that this never surfaces,
but it is a real lifetime bug.

### 11. Papyrus-thread natives read game state off the game thread

`IsWeaponAllowed` and `GetHeatPerShot` call `PlayerCharacter::GetCurrentAmmo` directly from
the VM thread. This predates the current design and has run for thousands of shots without
incident, so it is noted rather than urged.

## Suggested order

1. The `Config` mutex (#1) - the only crash risk.
2. Drop the unreferenced texture (#7) - halves the download, one manifest line.
3. Fix or remove the nine dead settings (#4), starting with `bAttachEnabled=0`.
4. `git init` a first commit (#9).
5. Delete the dead Papyrus and `ProjectileEmitter` (#5, #6) - large, purely subtractive.
6. Guard the unreachable-threshold combination (#3).

---

# Remediation - 0.15.0

Package: `dist/GunHeatHaze-0.15.0-audit-fixes.zip` (12 files, 349562 bytes - down from
497371). DLL 773120 bytes. Pre-removal sources at `_backup/0.14.0-pre-deadcode-removal/`.

Fixed in the order agreed; `git init` (#9) deferred at the user's request.

## #1 Config thread safety - FIXED

Added `mutable std::shared_mutex mutex_` to `Config`:

- **Exclusive** around `Load()` and the whole of `ReloadOverrides()`, throttle stamp
  included - `lastOverrideLoad_` is a plain `time_point` that both threads reach.
- **Shared** in `GetFloat()` (reads `floats_`) and `IsWeaponAllowed()` (reads both FormID
  sets).
- The five `const std::string&` accessors now **return by value under a shared lock**.
  Returning a reference was the sharpest edge here: a caller could hold the buffer while a
  reload reassigned the string and freed it.
- Verified no self-deadlock: `ParseFile` and `Finalize` touch members only and call no
  locking accessor. `shared_mutex` is not recursive, so this mattered.

Scalar float/bool accessors stay lock-free by design, documented in the header: they are
aligned POD loads that cannot tear on x86-64, so the worst case is one frame reading the
previous value, and locking ~20 of them per tick at 125 Hz would cost more than it buys.

Two accessors were deleted rather than locked - `ExcludeEnergyWeapons()` and
`IsEnergyAmmo()` were both unused, and `IsEnergyAmmo` read `energyAmmo_` with **no lock**,
so it was a hazard waiting for its first caller. `IsWeaponAllowed` uses the members directly
under its own shared lock, which is correct; calling the accessors from there would have
re-locked a `shared_mutex` on one thread, which is undefined.

## #7 Unreferenced texture - FIXED

`Textures/Effects/HeatHazeFlowTile_n.dds` dropped from the manifest with a note explaining
why. **The package went from 497 KB to 349 KB, a 30% reduction**, for a file the shipped
mesh never referenced.

## #4 Dead settings - FIXED

Removed `bAttachEnabled`, `sAttachNode`, `sHazeArtObject`, `fScrollScale`,
`bExtractGeometry` and `fTimerInterval` from the header, the parser, the ini and the
`config loaded:` log line. `bAttachEnabled=0` was the harmful one - it read as "attachment
disabled" while `AddHeat` attached unconditionally.

Removing five fields from a 39-placeholder, 42-argument log line was done positionally
rather than by hand. That verification incidentally **proved the original line was correct**
- an early version of the checker reported an off-by-one from index 9, which turned out to
be the checker's regex missing the `{:08X}` placeholder, not a bug in the code.

## #5 / #6 Dead code - REMOVED

- `ProjectileEmitter.h` deleted (521 lines), with its 29 parse branches, 27 exclusive
  accessors, ~50 members, 67 ini lines and 6 call sites. It was disabled by config *and*
  unreachable by call graph.
- `GunHeatController.psc` went from **338 to 145 lines**: `StartHaze`, `StopHaze`,
  `UpdateHeat`, `ApplyHeat`, `GetHazeStrength`, `GetCurrentFadeOutSeconds` and fourteen
  now-orphaned state variables. `GunHeatController.pex` shrank from 8773 to 3637 bytes.
- `OnGameLoaded()` was **kept deliberately** and simplified. It still has no call path -
  the quest has no alias - but it is now cheap and dependency-free, so adding an alias in
  the Creation Kit is all that would be needed. This is the one intentional zero-call-site
  function left.
- Total C++ and Papyrus: 3181 -> 2277 lines.

`SetHazeStrength` and `PulseHeat` natives were left in place. They now have no callers, but
they are a declared script interface rather than dead code, and removing them would break
any save whose `.pex` predates the change.

## #3 Unreachable threshold - GUARDED

`Finalize()` now caps `fMinHeatToShow` at what ten shots can produce
(`min(fHeatPerShot * 10, 1.0)`) and **logs a warning naming both values and the clamp**,
rather than silently overriding the player:

```
fMinHeatToShow 0.6 is unreachable with fHeatPerShot 0.01 - clamping to 0.1.
Raise fHeatPerShot or lower the visibility threshold.
```

## Verification

Both audit scripts were re-run against the fixed tree:

- **Config consistency: no issues.** Every mismatch in section A is gone - they were all
  ProjectileEmitter drift plus the six dead settings.
- **No unparsed ini keys, no unknown MCM slider ids**, in either direction.
- **No dead Config accessors and no unread parsed members.**
- **Papyrus: no unused variables**, and the only zero-call-site function is the deliberate
  `OnGameLoaded`.
- **All 39 logger format strings balance** their placeholders against their arguments -
  checked mechanically after editing the big one twice.
- DLL builds clean with no compiler diagnostics; all three `.pex` compile.

## Not done

- **#9 git init** - deferred by request. Still the largest practical risk: zero commits,
  zero tracked files, and the tools, ESP and NIF are covered by no backup.
- **#2 quest alias** - needs the Creation Kit, not code. Worked around and no longer
  load-bearing.
- **#10 pacer thread lifetime** and **#11 off-thread game-state reads** - both noted as
  lower severity and left alone.

## Untested

None of this has been run in-game. The changes are heavily subtractive, but the mutex is new
behaviour on a hot path and the Papyrus rewrite touches the only live code path there. A
normal firing session is worth one pass before this is considered good.
