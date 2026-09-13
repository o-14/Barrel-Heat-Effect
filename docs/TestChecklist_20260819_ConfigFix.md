# Config path fix, fade-out slider, crash triage - 2026-08-19

Build: `dist\GunHeatHaze-0.9.1-fadeout-configfix.zip`

## 1. Were MCM changes applying?

**Partly. DLL-side yes, Papyrus-side no.** The log proves both halves.

**Applying correctly** (DLL reads these directly):

```text
41x  applying MCM overrides from Data/MCM/Settings/GunHeat.ini
     hazeRefractionRange=(0, 0.05) -> (0, 0.07) -> (0, 0.1)      as the slider moved
     caliber heat: heatPerShot=0.15 -> 0.1 -> 0.01               as the slider moved
```

**The cool-down sliders were applying.** `UpdateHeat` logged `fadeOut` values spanning
`8.120000` to `20.000000`, which is exactly `minFadeOut + (maxFadeOut - minFadeOut) *
peakHeat` for min=8 and max=20. Both ends of your configured range are represented.

**Not applying:** every single `LoadIniConfig` line in a 1.9 MB log read

```text
heatPerShot=0.125000 ... timer=0.100000
```

`0.125` is `1.0 / ShotThreshold` and `0.1` is the script's own default - both are
*fallbacks* taken when `GetIniFloat()` returns 0. So Papyrus was getting 0 for
`fHeatPerShot` and `fTimerInterval` for the whole session while the DLL, reading the same
keys, got the right values. `fMinHeatToShow` also stayed at the base-ini `0.05` rather
than your MCM `0.1`.

### Fix

The heat curve no longer goes through the generic `GetIniFloat` string map. Those settings
are typed members on `Config` now, exposed through a dedicated `GetHeatSetting()` native
that refreshes the MCM overlay on each call. Same source of truth as the DLL uses.

## 2. The heat-per-shot lock-up

Confirmed, and the mechanism is exact.

`LoadIniConfig()` was only called from `OnQuestInit`, `OnGameLoaded`, and **`StartHaze()`**.
`StartHaze()` only runs when heat crosses the visibility threshold. So dropping
`fHeatPerShot` to `0.01` (0.00775 after caliber scaling, against decay of 0.125/sec) made
heat unable to ever reach the threshold - which meant `StartHaze()` never ran - which meant
the config was never re-read. Raising the slider back up could not take effect, because the
only code that would have noticed was gated behind the very condition it needed to fix.

Reloading a save cleared it because that calls `OnGameLoaded` -> `LoadIniConfig`. Exactly
what you observed.

Fixed two ways, so it cannot recur:

- `LoadIniConfig()` now runs on **every shot**, before anything reads the curve.
- `GetHeatSetting()` refreshes the MCM overlay itself on every call.

## 3. New: Fade out slider

`[Heat] fFadeOutSeconds`, default **2.5**, MCM slider **Duration -> Fade out (seconds)**.

This is genuinely separate from the cool-down sliders:

- **Cool-down, short burst / fully hot** - how long the barrel stays *hot* (heat decay).
- **Fade out** - how fast the *shimmer* disappears once heat drops below the threshold.

Previously the visible ramp-down reused the heat-decay duration, so there was no way to
have a barrel that stays hot a long time but whose shimmer dies off quickly, or vice versa.

## 4. The crash

**Not attributable to this mod.**

```text
EXCEPTION_ACCESS_VIOLATION at Fallout4.exe+1DC55BD  (address library 365042+0x2D)
```

- The probable call stack is **14 frames, all `Fallout4.exe`**, then KERNEL32/ntdll. No
  `GunHeat.dll` frame anywhere. It appears only in the MODULES list, which lists every DLL
  in the process.
- Buffout's typed annotations put the crash squarely in character movement and physics:
  `RBX`/`RSI` are `bhkCharProxyController*` (the player's Havok capsule), `RDI` is
  `PlayerCharacter*`, and the stack holds `MovementControllerNPC*`,
  `MovementTweenerArbiter*`, `AttackBlockHandler*` and `BSAnimationGraphManager*`.
  `R14` is a `JobListManager::ServingThread*`, so it faulted on a worker thread.
- This mod touches none of that. It attaches an art object to a muzzle node and writes
  `refractionPower`, `local.translate` and `local.rotate` on that art object. It does not
  touch movement, the character proxy, the animation graph, or attack/block handling.

I verified the address-library IDs in the log resolve correctly (`365042` -> RVA
`0x01dc5590`, +0x2D = the faulting address), so the annotations are trustworthy. I could
not put function *names* to those frames - that needs Ghidra, which was closed.

Being straight about the limit: "GunHeat is absent from the stack and the crashing
subsystem is one we never touch" is strong evidence, not proof. If it recurs, the cleanest
test is whether it also happens with the mod disabled.

## Test

1. Install. `GunHeat.dll` is **773632** bytes.
2. Move **Heat per shot** to its minimum, fire, then move it back up - heat should return
   **without** reloading a save.
3. Check the log: `LoadIniConfig` should now report the values you actually set, and should
   change as you move sliders.
4. Try **Fade out** at 0.5 vs 8.0 with cool-downs unchanged - the shimmer should vanish
   quickly or linger, while total heat duration stays the same.
