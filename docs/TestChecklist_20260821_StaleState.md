# Stale hazeActive fix - 2026-08-21

Build: `dist\GunHeatHaze-0.11.2-stale-state-fix.zip`

## Not the re-attach change

This is a pre-existing latent bug that the previous session finally triggered. The
re-attach code from 0.11.1 never even ran.

## What the log showed

247 shots registered, and every one reached the natives:

```text
247  Papyrus: IsWeaponAllowed ... allowed=true
247  Papyrus: LoadIniConfig: heatPerShot=0.15 ...
247  Papyrus: running queued PulseHeat
249  Papyrus: SetHazeStrength ...
  0  AttachHaze / art object applied / muzzle node changed / warnings
```

`PulseHeat` is only reached from the `Else` branch, which requires `hazeActive` to be
true. So `hazeActive` was true for all 247 shots while **no haze had ever been attached**.

`StartHaze` is gated on `!hazeActive`, so it could never run, so nothing was ever attached
and nothing rendered - for every weapon, exactly as reported. Meanwhile `SetHazeStrength`
found no entry and returned silently, so nothing looked wrong.

## Root cause

Three things line up:

1. `hazeActive` is a script variable, so it is **stored in the save**. The previous session
   ended mid-cycle - 5 attaches, 4 detaches - so it was saved as `true`.
2. The DLL clears every active haze on `kPostLoadGame`, so after loading, `active_` is
   empty while `hazeActive` is still `true`. Nothing reconciled the two.
3. The intended cleanup, `OnGameLoaded()` (which calls `StopHaze()` when `hazeActive` is
   set), is invoked from `PlayerAlias.OnPlayerLoadGame()` - and **that event can never
   fire**, because the quest record carries no alias at all:

```text
QUST subrecords: EDID, VMAD, FULL, DNAM, NEXT
alias subrecords (ALST/ALID/ALLS): NONE
```

The log confirms it: zero `OnGameLoaded` and zero `OnQuestInit` lines all session.

So the save/load cleanup path has never worked. It only became visible now because a
session finally ended with a cycle open.

## Fix

New native `HasActiveHaze(akRef)` reports whether the DLL actually holds a live haze. The
controller now reconciles against it on every shot, before deciding anything:

```papyrus
If hazeActive && !GunHeat:GunHeatNative.HasActiveHaze(PlayerRef)
    hazeActive = False
    heat = 0.0
    ...
EndIf
```

This is deliberately not a fix to the alias. Reconciling against the native side is more
robust than depending on a Papyrus load event firing: it also recovers from an
`AttachHaze` that failed and left the flag set, and from any future case where the two
sides drift apart. Adding a filled alias to the quest in the Creation Kit is still worth
doing eventually, but it is no longer load-bearing.

## Test

1. Install. `GunHeat.dll` is **780800** bytes.
2. Fire - the effect should work immediately, without needing a clean save.
3. To confirm the recovery path, look for this once on the first shot after loading a save
   that was made mid-cycle:

```text
Papyrus: stale hazeActive with no native haze; resetting cycle state
```

4. Then re-test the 0.11.1 weapon-switch fix, which never got a chance to run: heat up
   weapon A, switch to B while the effect is still visible, keep firing. Expect
   `muzzle node changed ... art object re-applied`.
