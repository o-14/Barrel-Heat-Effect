Scriptname GunHeat:GunHeatNative Native Hidden

Bool Function AttachHaze(ObjectReference akRef) Global Native
Function DetachHaze(ObjectReference akRef) Global Native
Function SetHazeStrength(ObjectReference akRef, Float afStrength) Global Native
; Reports one shot. The DLL owns the cycle from there: it attaches on the first shot,
; decays the heat on its own game-thread tick and detaches itself when the barrel is cool.
; Nothing else needs to be called between shots.
Function AddHeat(ObjectReference akRef, Float afAmount, Weapon akWeapon) Global Native
; Experimental: nudges the already-visible haze so a shot reads as disturbing the plume.
; No-op unless [Haze] bPulseEnabled=1 and a heat cycle is currently active.
Function PulseHeat(ObjectReference akRef) Global Native
; True while the native side actually holds a live haze for this reference.
Bool Function HasActiveHaze(ObjectReference akRef) Global Native
Bool Function IsWeaponAllowed(Weapon akWeapon) Global Native
Float Function GetHeatPerShot(Weapon akWeapon) Global Native
Float Function GetIniFloat(String asSection, String asKey) Global Native
; Typed [Heat] settings, refreshed from the MCM overlay on every call. Use this rather
; than GetIniFloat for the heat curve.
Float Function GetHeatSetting(String asKey) Global Native
Function Log(String asMessage) Global Native
