Scriptname GunHeat:GunHeatController extends Quest

; Reports shots to the DLL and nothing else.
;
; This script used to own the heat curve, driven from OnTimer. That never worked: across a
; 601-shot test session OnTimer fired 116 times and every fire landed after the cycle had
; already ended, so nothing decayed heat between shots and the effect froze at its last
; strength the moment the player stopped firing. StartTimer also does not restart a pending
; timer, and OnTimer returned without re-arming whenever its guard failed, which killed the
; chain permanently on the first bad fire.
;
; Since 0.12.0 the DLL owns the whole cycle - attach, decay, the visual ramp, puffs and the
; eventual detach - on its own game-thread tick. The heat model there is a line-for-line
; port of the UpdateHeat that used to live here, reading the same settings from the same
; ini and MCM overlay. Everything that supported the old design (StartHaze, StopHaze,
; UpdateHeat, ApplyHeat, GetHazeStrength, GetCurrentFadeOutSeconds, and the heat, peakHeat,
; visibleStrength, hazeActive and timerInterval state behind them) was unreachable dead code
; and was removed in the 2026-09-07 audit.

; Kept because the plugin's VMAD binds to them. ShotThreshold still backs the heat-per-shot
; fallback below; the rest are legacy tuning the DLL now supersedes.
Int Property ShotThreshold = 8 Auto
Float Property ResetWindow = 0.6 Auto
Float Property Duration = 3.0 Auto
Float Property MaxIntensity = 0.6 Auto
Bool Property DebugNotifications = False Auto

Actor PlayerRef
Float heatPerShot = 0.07 ; fallback only, see LoadIniConfig; keep equal to ini fHeatPerShot

Event OnQuestInit()
    PlayerRef = Game.GetPlayer()
    ClampConfig()
    LoadIniConfig()
    RegisterForAnimationEvent(PlayerRef, "weaponFire")
    Trace("initialized")
    DebugLog("OnQuestInit: registered for weaponFire on player")
EndEvent

; Reached only through GunHeat:PlayerAlias.OnPlayerLoadGame. The quest currently carries no
; filled alias - the QUST record decodes to EDID/VMAD/FULL/DNAM/NEXT with no ALST/ALLS - so
; in practice this never runs. It is kept, and kept cheap, so that adding an alias in the
; Creation Kit later is all that is needed. Nothing here has to restore cycle state: the DLL
; clears its own on kGameLoaded and no cycle state is stored in the save any more.
Function OnGameLoaded()
    PlayerRef = Game.GetPlayer()
    ClampConfig()
    LoadIniConfig()
    RegisterForAnimationEvent(PlayerRef, "weaponFire")
    Trace("loaded")
    DebugLog("OnGameLoaded: re-registered for weaponFire on player")
EndFunction

Event OnAnimationEvent(ObjectReference akSource, String asEventName)
    If akSource != PlayerRef || asEventName != "weaponFire"
        DebugLog("OnAnimationEvent: ignored source/event " + akSource + " / " + asEventName)
        Return
    EndIf

    Weapon equippedWeapon = PlayerRef.GetEquippedWeapon()
    If !IsSupportedGun(equippedWeapon)
        DebugLog("OnAnimationEvent: no supported equipped weapon")
        Return
    EndIf

    Float shotHeat = GunHeat:GunHeatNative.GetHeatPerShot(equippedWeapon)
    If shotHeat <= 0.0
        shotHeat = heatPerShot
    EndIf

    ; Report the shot and stop. The weapon is passed so the DLL can tell one barrel from
    ; another and start a freshly drawn weapon cold - see [Heat] bResetHeatOnWeaponSwitch.
    GunHeat:GunHeatNative.AddHeat(PlayerRef, shotHeat, equippedWeapon)
EndEvent

Bool Function IsSupportedGun(Weapon akWeap)
    If akWeap == None
        Return False
    EndIf

    Return GunHeat:GunHeatNative.IsWeaponAllowed(akWeap)
EndFunction

Event OnTimer(Int aiTimerID)
    ; Retained only to swallow timers left pending in existing saves. The heat cycle no
    ; longer uses timers at all; see the header.
    DebugLog("OnTimer: obsolete timer=" + aiTimerID + " ignored; the DLL owns the heat tick")
EndEvent

Function LoadIniConfig()
    ; Only the heat-per-shot fallback is still read here. Every other setting in the curve
    ; is consumed by the DLL directly, from the same ini and the same MCM overlay, so
    ; mirroring them into Papyrus variables would just be a second stale copy.
    ;
    ; GetHeatSetting reads the DLL's typed settings. The older GetIniFloat path went through
    ; a generic string map and was observed returning 0 for fHeatPerShot for an entire
    ; session, which silently pinned heat per shot to the 1.0/ShotThreshold fallback.
    Float iniHeatPerShot = GunHeat:GunHeatNative.GetHeatSetting("fHeatPerShot")
    If iniHeatPerShot > 0.0
        heatPerShot = iniHeatPerShot
    EndIf

    ClampHeatConfig()
    DebugLog("LoadIniConfig: heatPerShot=" + heatPerShot)
EndFunction

Function ClampHeatConfig()
    If heatPerShot <= 0.0
        heatPerShot = 1.0 / ShotThreshold
    ElseIf heatPerShot > 1.0
        heatPerShot = 1.0
    EndIf
EndFunction

Function ClampConfig()
    If ShotThreshold < 1
        ShotThreshold = 1
    EndIf
    If ResetWindow < 0.1
        ResetWindow = 0.1
    EndIf
    If Duration < 0.5
        Duration = 0.5
    EndIf
    If MaxIntensity < 0.0
        MaxIntensity = 0.0
    ElseIf MaxIntensity > 1.0
        MaxIntensity = 1.0
    EndIf
EndFunction

Function Trace(String asMessage)
    Debug.Trace("[GunHeat] " + asMessage)
    If DebugNotifications
        Debug.Notification("GunHeat: " + asMessage)
    EndIf
EndFunction

Function DebugLog(String asMessage)
    ; The GetIniFloat("Debug", "bDebugLogging") guard was returning 0 at runtime, so
    ; no Papyrus-side line ever reached GunHeat.log even with bDebugLogging=1 - which
    ; left the heat values invisible during diagnosis. Log() already applies the same
    ; check natively, using the flag the native side actually read, so call it directly.
    GunHeat:GunHeatNative.Log(asMessage)
EndFunction
