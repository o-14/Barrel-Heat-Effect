# Gun Heat Haze - Audit and Roadmap (2026-08-06)

Read-only audit of the workspace plus a decode of what Fallout 4 actually does for the
Minigun barrel heat effect. Nothing in the existing project was modified to produce this;
the only file added alongside it is `tools/dump_fo4_lighting_shader.py`.

Target runtime remains Fallout 4 `1.10.163` / F4SE `0.6.23`.

---

## 1. What is currently built

| Layer | State |
| --- | --- |
| `Data/GunHeatHaze.esp` (526 bytes) | one `QUST` (`GunHeatControllerQuest`) + one `PROJ` (`01000801 GunHeatHeatPuffProjectile`) |
| Papyrus | `GunHeatController.psc` owns the heat curve; fires a 0.03 s timer; calls natives |
| F4SE DLL | `HazeManager` (runtime scene-graph attach, currently disabled) + `ProjectileEmitter` (active path) |
| Visual carrier | `PROJ` launched every 0.14-0.26 s carrying `GunHeatHaze\GunHeatRefractionOnlyStrong.nif` |
| Fade | `refractionPower` written on the launched projectile's material every heat tick |

`[Haze] bAttachEnabled=0`, `sAttachNode=Camera` - the scene-graph route is parked in
diagnostic mode after the crashes documented in `Method2_EngineManagedHeatHaze_Design.md`.

---

## 2. What Fallout 4 actually does for Minigun barrel heat

Decoded from the vanilla asset with `tools/dump_fo4_lighting_shader.py`. Field layout and
enum names verified against `nif.xml` shipped with NifSkope 2.0 dev7
(`<local-path>`),
`BSLightingShaderProperty` with `User Version 2 == 130`.

### `Meshes\Weapons\Minigun\MinigunBarrel.nif`

```text
NiNode "BarrelRoot"
├── NiBillboardNode "BaseRefractionMesh"          <- block 23
│   └── BSTriShape "BaseRefractionMesh:0"         <- block 24, 29 verts, bound r=27.6
│       └── BSLightingShaderProperty              <- block 25
│           └── BSShaderTextureSet                <- block 26
└── NiNode "Minigun_Barrel" -> BSTriShape 838 verts (the metal, uses MinigunBarrel.BGSM)
```

`BSLightingShaderProperty` (block 25) exact values:

```text
Shader Type          0 (Default)
Name                 ""            <- deliberately NO .BGSM; a material file would
                                      override the shader flags below
Shader Flags 1       0x80418001    Specular | Refraction | Fire_Refraction
                                   | Own_Emit | ZBuffer_Test
Shader Flags 2       0x00000020    Vertex_Colors          (ZBuffer_Write is OFF)
Alpha                1.0
Refraction Strength  0.0           <- authored as zero, driven entirely by controllers
Smoothness           1.0
UV Offset            (0.0, 0.0)
UV Scale             (1.0, 1.0)
Texture slot 0       textures\Effects\SmokeVapor01Tile_n.dds
Texture slot 1       textures\Effects\SmokeVapor01Tile_n.dds
```

The normal map is loaded into **both** slots. There is no diffuse, no glow map, no
`Glow_Map` flag, emissive colour is black - that is precisely why the vanilla effect
distorts without glowing.

Two chained `BSLightingShaderPropertyFloatController`s target that shader property
(freq 1.0, span 0-5 s):

| Controller | Variable | Meaning |
| --- | --- | --- |
| block 09 | `22` | **V Offset** |
| block 10 | `0` | **Refraction Strength** |

Enum confirmed from `nif.xml`, `LightingShaderControlledVariable`:
`0 = Refraction Strength`, `20 = U Offset`, `21 = U Scale`, `22 = V Offset`, `23 = V Scale`.

Two `NiControllerSequence`s drive them - `x_partA` and `x_partB`, 2 controlled blocks
each, 1.667 s long, played by the weapon's animation graph (barrel spin-up / spin-down).
Grouping the interpolators by block order:

```text
x_partA:  V Offset            0.000 ->  0.00 ,  1.667 -> -1.00   (linear, one full tile)
          Refraction Strength 0.000 -> -0.20 ,  1.667 -> -0.20   (constant)

x_partB:  V Offset            0.000 -> -0.02 ,  0.033 -> 0.00 ,  1.667 -> -1.00
          Refraction Strength 0.000 ->  0.18 ,  1.667 ->  0.18   (constant)
```

So the entire vanilla effect is: **a camera-facing card with a normal map, whose V offset
scrolls one tile per 1.667 s, with refraction strength held at roughly +/-0.2.** There is no
particle system, no light, no smoke, no glow, and no intensity ramp - it is simply on
while the spin animation plays.

### Cross-checks against other vanilla refraction assets

| Asset | Refraction Strength | Flags 1 | Controllers |
| --- | --- | --- | --- |
| `Weapons\Minigun\MinigunBarrel.nif` | 0.0 (driven +/-0.18-0.20) | `0x80418001` | V Offset, Refraction |
| `Effects\FlameJetMuzzleFlash.nif` | 0.2000 | `0x80418009` | V Offset (+ others) |
| `Effects\MoltenIronPlane01.nif` | 0.0500 | - | V Offset, U Offset (26.7 s) |
| `Effects\SaugusSmokeMirage.nif` | 0.0300 | `0x80408201` | V, U, Refraction (23-33 s) |
| `Effects\GlowingSeaMirageEffect01.nif` | 0.0749 | `0x80408201` | V, U, Refraction |

The ambient mirages omit `Fire_Refraction` and add `Double_Sided`; both minigun and flamer
set `Fire_Refraction`. **The whole vanilla range for this effect is 0.03 to 0.20.**

---

## 3. Audit findings

### 3.1 Refraction strength is 4x to 27x vanilla

`Data/Meshes/GunHeatHaze/GunHeatRefractionOnlyStrong.nif` block 99:

```text
Refraction Strength  0.8000
Shader Flags 1       0x80418201
Shader Flags 2       0x00000021   (ZBuffer_Write ON)
```

and `[ProjectileEmitter] fRefractionMaxStrength=0.80`. Against a vanilla ceiling of 0.20,
this reads as a warping glass blob rather than heat. This is the single cheapest thing to
change and worth testing on its own before any architectural work.

### 3.2 The carrier asset is a flamethrower projectile, behaviour graph included

Strings in `GunHeatRefractionOnlyStrong.nif`:

```text
FlameThrowerProjectileSprayShort01
BSBehaviorGraphExtraData -> GenericBehaviors\ProjectileSprayRange\ProjectileSprayRange.hkx
BSConnectPoint::Parents, LagBone, BillboardHelper, AddOnNode196, AddOnNode212
NiControllerManager: mSprayStart, mSprayShort, mSprayLong
```

Re-parenting a root that carries a Havok behaviour-graph binding, connect points and an
object palette into the live first-person weapon graph is a very plausible cause of the
crashes recorded on 2026-06-22. The engine tries to bind a behaviour graph for a node that
is no longer where it thinks it is.

### 3.3 Only one UV controller survives, and it is the wrong axis

The stripped asset retains a single `U Offset` controller (start 0.100, stop 3.333). Every
vanilla heat asset uses **V Offset** as the primary scroll, and the minigun scrolls one
full tile in 1.667 s. A lone U-axis scroll over 3.2 s reads as slow lateral sliding, not
as heat rising off a barrel.

### 3.4 No billboard on the heat card

Vanilla puts `BaseRefractionMesh` under a `NiBillboardNode` so the card always faces the
camera and the distortion stays coherent at any angle. The current asset inherits the
flamer's `BillboardHelper` / `LagBone` rig instead of a billboard root on the card itself.

### 3.5 Projectiles are the wrong primitive for a barrel-attached effect

`ProjectileEmitter::Emit` launches 4-7 projectiles/second. Consequences:

- They live in world space. They do not follow the muzzle when the player turns, walks or
  changes stance, so the shimmer visibly separates from the gun.
- Each has an independent birth and death, so the visual can never be genuinely smooth -
  which `SmoothFade_PersistentEffect_Route.md` already concluded.
- They are real engine objects with collision, ammo and weapon association, and cell
  persistence semantics you do not want for a decal-like visual.
- The heat exists only where the shot was fired from, not on the barrel.

### 3.6 Hand-rolled `AttachChild` into a graph the engine owns

`HazeManager::Attach` does `BSModelDB::Demand` then `attachNode->AttachChild(haze, true)`.
Three separate problems:

1. `BSModelDB::Demand` hands back a **cached, shared** model. `LoadHazeModel` then mutates
   it in place (`collisionObject = nullptr`, `SetAppCulled`, later `refractionPower`),
   which corrupts the cache for every subsequent load. `GunHeatHaze_Discovery_Report.md`
   already observed this as later loads reporting `kept 0 haze geometries`.
2. No `Update` / `UpdateDownwardPass` is issued after attach, so world transforms and
   bounds on the new subtree are stale on the first frames.
3. The first-person weapon graph is rebuilt by the engine on equip, unequip, view change,
   weapon-mod change, cell change and save load. `ActiveHaze` holds raw `NiPointer`s across
   all of those with no invalidation hook.

### 3.7 Live INI is in diagnostic mode

`sAttachNode=Camera` would place the shimmer in front of the player's face, not on the
barrel. The tree dump that motivated it only found `skeleton.nif / Root / COM / Camera /
Camera Control`, which means `Get3D(true)` was read before the first-person weapon subtree
existed - the weapon was never actually searched.

### 3.8 Runtime shader-flag writes are not the working lever

`ApplyRefractionStrength` sets `kRefraction` / `kRefractionFalloff` on `BSShaderProperty::flags`
every tick. Flags are consumed when the geometry's shader technique is selected, not per
draw, so toggling them at runtime is unreliable. What does work per frame is
`BSLightingShaderMaterialBase::refractionPower`, which is read into the constant buffer on
every draw - that part of the design is correct, keep it. One caveat: materials on a model
returned by `BSModelDB` can be shared between instances, so writing `refractionPower`
without a unique clone can bleed into other objects using the same asset.

### 3.9 Two independent smoothers fight each other

`GunHeatController.psc` computes `heat`, then smooths it into `visibleStrength`
(fade-in `1.40 s`, fade-out `2.0-8.0 s`). `ProjectileEmitter::UpdateActiveProjectiles` then
applies a *second* per-projectile envelope (`fRuntimeFadeInSeconds`, `fRuntimeFadeOutSeconds`,
`SmoothToward`, plus a 2.2 Hz shimmer). Two uncoordinated curves multiplied together, on
objects that are also being created and destroyed, is exactly the pulsing that was reported.

### 3.10 Papyrus timing

`fTimerInterval=0.03` asks the Papyrus VM for ~33 updates/second, each making a native
call. The VM does not deliver that reliably; it will drift and stutter under load, which
directly undermines the "smooth" goal. The heat curve should be evaluated natively per
frame, with Papyrus only reporting shot events.

### 3.11 Repository hygiene (minor)

Nothing is committed yet - `git status` shows the whole tree as untracked. There are 30+
`GunHeatHaze.esp.*-backup-*` files in `Data/` and eight `GunHeatPlugin/build-*` directories.
Worth an initial commit before further surgery so experiments become revertible instead of
generating more backup files.

---

## 4. Recommended route

### Route A (recommended): engine-owned art object on the weapon's fire node

Two pieces of the engine solve the two hard parts of this problem, and neither is currently
being used.

**Finding the muzzle without per-weapon patches.** `CommonLibF4` exposes, in
`RE/Bethesda/Actor.h`:

```cpp
struct EquippedWeaponData {
    TESAmmo*      ammo;          // 10
    std::uint32_t ammoCount;     // 18
    AimModel*     aimModel;      // 20
    MuzzleFlash*  muzzleFlash;   // 28
    NiAVObject*   fireNode;      // 30   <- the engine's resolved muzzle node
    ...
};
```

`fireNode` is the node the engine itself uses to spawn projectiles and muzzle flash for the
*currently equipped weapon with its currently attached mods*. Reading it removes the entire
`MuzPistolSmall01` / `MuzMachineGun01` / modded-weapon naming problem and works for vanilla
and modded guns alike. Reach it through the player's current process -> middle-high process
-> equipped weapon data.

**Attaching without hand-rolling scene-graph surgery.** `RE/Bethesda/TESObjectREFRs.h`:

```cpp
ModelReferenceEffect* ApplyArtObject(
    BGSArtObject*  a_art,
    float          a_time          = -1.0f,   // -1 = persist until removed
    TESObjectREFR* a_facingRef     = nullptr,
    bool           a_attachToCamera = false,
    bool           a_inheritRotation = false,
    NiAVObject*    a_3D            = nullptr, // explicit attach root
    bool           a_interfaceEffect = false);
```

This is the engine's own hit-effect-art system. It returns a `ModelReferenceEffect`
(`RE/Bethesda/BSTempEffect.h`), which is a `BSTempEffect` participating in save/load
(`SaveGame` / `LoadGame` / `FinishLoadGame`), cell unload (`GetClearWhenCellIsUnloaded`),
and 3D swap (`ReferenceEffect::Update3D`, `SwitchAttachedRoot`, `UpdateParentCell`).
Every lifecycle problem listed in 3.6 is handled by the engine rather than by the plugin.

`ModelReferenceEffect::artObject3D` gives back the live `NiAVObject`, which is what you walk
to drive `refractionPower` and UV offset per frame.

Shape of the implementation:

1. Author the minimal heat NIF (section 5).
2. Add one `ARTO` record to `GunHeatHaze.esp` pointing at it. One record, no per-weapon work.
3. On first heat, from a game-thread task:
   `player->ApplyArtObject(heatArt, -1.0f, nullptr, false, false, fireNode, false)`.
4. Cache the returned `ModelReferenceEffect*`; each frame set `refractionPower` and the
   shader's UV offset on `artObject3D` from the heat curve.
5. When heat reaches zero, end the effect (set `finished` / let `lifetime` expire) and drop
   the pointer. Also drop it on weapon change, view change and `kPostLoadGame`.
6. Delete the `ProjectileEmitter` path entirely.

Things to verify in-game, because they are not provable from headers alone:

- Whether `ApplyArtObject` honours `a_3D` as the attach root when that node lives in the
  first-person graph rather than under `Get3D()`.
- Whether the art object survives the first-person weapon graph being rebuilt, or needs to
  be re-applied on equip.
- `REL::ID 357908` is a 1.10.163 address - fine for the target runtime, but it pins the
  plugin to old-gen.

### Route B (fallback): drive the engine's existing muzzle flash object

`EquippedWeaponData::muzzleFlash` is an engine-created, engine-positioned, engine-destroyed
object that is already correct in both first and third person, and is already refreshed by
every shot. Raising the projectile's muzzle-flash duration and driving `refractionPower` on
that live object would give barrel-locked heat with zero attach code.

Cost: `MuzzleFlash` is only forward-declared in CommonLibF4 (`Actor.h:76`), so its layout
has to be reversed before use. It also re-couples the effect to the muzzle-flash event,
which the 2026-06-22 flag test showed is what brings the vanilla gunsmoke along.

### Route C (fallback): ESP-only, no F4SE

Bake the heat card into muzzle/barrel OMOD models, exactly as vanilla does for the minigun,
and let the weapon's own animation sequences drive it. Ships without F4SE and cannot crash
the scene graph. Cost: per-weapon patching, and buildup comes from effect overlap rather
than a real curve. Reasonable as a compatibility variant, not as the main mod.

### Route D: stop pursuing projectile puffs

Section 3.5. This path cannot produce a barrel-attached, smoothly-faded effect no matter
how the tuning parameters are set.

---

## 5. Asset recipe

A minimal, reparent-safe heat card. Everything vanilla carries that we do **not** need is
what has been causing the crashes.

```text
NiNode "GunHeatHaze"                       (BSXFlags: none, or 0x01 Animated only)
└── NiBillboardNode "HeatCard"             (Billboard Mode: always face camera)
    └── BSTriShape "HeatCard:0"            (small quad strip over/ahead of the barrel)
        ├── BSLightingShaderProperty
        │     Shader Type          Default (0)
        │     Name                 ""      <- no .BGSM; a material overrides these flags
        │     Shader Flags 1       0x80418001
        │                          Specular | Refraction | Fire_Refraction
        │                          | Own_Emit | ZBuffer_Test
        │     Shader Flags 2       0x00000020   Vertex_Colors  (ZBuffer_Write OFF)
        │     Alpha                1.0
        │     Emissive Color       0,0,0
        │     Refraction Strength  0.0     <- driven at runtime
        │     UV Scale             1.0, 1.0
        └── BSShaderTextureSet
              slot 0  textures\Effects\SmokeVapor01Tile_n.dds
              slot 1  textures\Effects\SmokeVapor01Tile_n.dds
```

Deliberately absent: `BSConnectPoint::Parents`, `BSBehaviorGraphExtraData`,
`bhkNPCollisionObject` / `bhkPhysicsSystem`, `NiControllerManager` and its sequences,
`NiAlphaProperty`, `NiParticleSystem` / `BSMasterParticleSystem`, any AddOnNodes.

Drive the scroll from the DLL by writing the shader's UV offset each frame rather than
shipping a controller - that keeps the NIF free of an object palette and lets scroll speed
track heat.

**No glow** comes from: emissive colour black, no glow map, no `Glow_Map` flag, no
`Effect_Lighting` flag, and only the normal map in the texture set. `Own_Emit` being set is
fine - vanilla sets it too and it does not glow.

**No smoke** comes from: no particle systems in the asset, and not routing through the
projectile muzzle-flash slot (that event is what carries the vanilla gunsmoke).

### Tuning targets, taken from vanilla

| Parameter | Vanilla range | Suggested mapping |
| --- | --- | --- |
| Refraction Strength | 0.03 (ambient mirage) to 0.20 (minigun / flamer) | heat 0 -> 1 maps to 0.02 -> 0.22 |
| V Offset scroll | 1 tile / 1.667 s (minigun); 1 tile / 23-33 s (ambient) | heat 0 -> 1 maps to ~0.3 -> 1.2 tiles/s |
| U Offset scroll | present on ambient mirages only | small constant, ~0.1 tiles/s, for asymmetry |
| Card size | minigun card bound radius ~27.6 units | start there, scale with heat if desired |

---

## 6. Tooling

| Tool | Where | Use |
| --- | --- | --- |
| NifSkope 2.0 dev7 | `<local-path>` | authoring the card; its `nif.xml` is the authority for FO4 field layouts and enums |
| FO4Edit / xEdit | - | adding the `ARTO` record, inspecting `PROJ` / `WEAP` / `OMOD` |
| Creation Kit | Steam | `ARTO` + `QUST` records, Papyrus compile |
| `Tools\Archive2\Archive2.exe` | game folder | BA2 packing for release |
| `Tools\MaterialEditor` | game folder | only if switching to `.BGSM`; note a material file **overrides** the NIF shader flags, which is why vanilla's heat card has an empty material name |
| Blender + FO4 NIF plugins / Outfit Studio | - | authoring the card geometry and UVs |
| Buffout 4 | - | crash logs when re-testing any attach path |
| `tools/dump_fo4_lighting_shader.py` | this repo (new) | exact decode of `BSLightingShaderProperty` and float controllers |
| `tools/inspect_nif_blocks.py`, `inspect_nif_refs.py`, `dump_nif_shader_values.py` | this repo | block/string/ref inspection |
| `$out/` | this repo | already-extracted vanilla mesh tree - use it as the reference corpus |

---

## 7. Suggested order of work

1. **Cheap look calibration first.** Drop `fRefractionMaxStrength` to `0.15` and re-patch the
   NIF's baked strength down from `0.80`. Test with the current projectile build. This tells
   you whether the *look* is right before you rebuild the *delivery*.
2. Author the minimal heat card NIF per section 5.
3. Add the `ARTO` record to `GunHeatHaze.esp`.
4. Rewrite `HazeManager` around `EquippedWeaponData::fireNode` + `ApplyArtObject`; retire
   `ProjectileEmitter`.
5. Move the heat curve from `GunHeatController.psc` into C++; leave Papyrus responsible only
   for reporting `weaponFire` and the equipped weapon.
6. Re-tune scroll rate and refraction against the vanilla ranges in section 5.

---

## 8. Open questions

- Does `ApplyArtObject` accept a first-person node as `a_3D`, or does it force the attach
  root back to `Get3D()`? Needs an in-game test with logging on the returned
  `ModelReferenceEffect`.
- Is `EquippedWeaponData::fireNode` valid in first person, or does it point at the
  third-person weapon instance? If the latter, the first-person equivalent has to be found
  through the same middle-high process data.
- Does the art object survive a first-person weapon graph rebuild (equip, weapon-mod change,
  view toggle), or must it be re-applied?
- Third person: should the effect appear there at all? Nothing in the current design
  addresses it.
