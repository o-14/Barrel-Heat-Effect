# Creation Kit Setup

Create `GunHeatHaze.esp` with these records:

1. Quest: `GunHeatControllerQuest`
   - Start Game Enabled: yes
   - Run Once: no
   - Script: `GunHeat:GunHeatController`

The first FO4Edit-generated prototype contains this quest only. It has no keyword properties to bind; `GunHeat:GunHeatController` currently accepts any equipped weapon so the first runtime test can focus on first-person attachment and mesh placement.

Optional follow-up once the prototype is working:

2. Player ReferenceAlias on that quest
   - Fill Type: Specific Reference
   - Reference: PlayerRef
   - Script: `GunHeat:PlayerAlias`
   - `Controller` property: point to the quest script instance.

First implementation target is first-person only. The native plugin looks for `WeaponMuzzle` under `PlayerRef.Get3D(true)`.
