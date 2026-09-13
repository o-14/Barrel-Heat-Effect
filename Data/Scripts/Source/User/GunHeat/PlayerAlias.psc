Scriptname GunHeat:PlayerAlias extends ReferenceAlias

GunHeat:GunHeatController Property Controller Auto Const

Event OnPlayerLoadGame()
    If Controller != None
        Controller.OnGameLoaded()
    EndIf
EndEvent

