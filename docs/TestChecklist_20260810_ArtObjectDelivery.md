# Route A - Art Object Delivery - 2026-08-10

Build: `dist\GunHeatHaze-0.5.0-artobject-delivery.zip`

This is the delivery rewrite. The projectile carrier is gone.

## What changed

### 1. Geometry - the circle is now a plume

`tools\reshape_nif_shape.py` scales the card's vertex positions in place (counts,
triangles, block sizes and every reference unchanged) and recomputes the bounding sphere.

| | before | after |
| --- | --- | --- |
| local X extent | 236.9 | 40.3 |
| local Y extent | 216.9 | 104.1 |
| bound radius | 120.24 | 52.05 |
| on screen at node scale 0.25 | 30 x 30 circle | **10 x 26 vertical plume** |

Tunable without touching code:

```bash
python tools/reshape_nif_shape.py Data/Meshes/GunHeatHaze/GunHeatBarrelRefractionCard.nif --shape Cylinder026 --scale 0.17 0.48 1.0
```

### 2. ARTO record

`tools\add_arto_record.py` adds one ART Object to `GunHeatHaze.esp`, layout copied from
vanilla `ARTO` records (EDID / OBND / MODL / MODT / DNAM):

```text
ARTO 01000802  GunHeatBarrelHazeArt -> GunHeatHaze\GunHeatBarrelRefractionCard.nif
```

TES4 `HEDR` numRecords 2 -> 3, nextObjectID 0x802 -> 0x803. ESP is 705 bytes and walks
cleanly end to end. **One record covers every weapon** - the art attaches to whatever
node we pass, so there is no per-weapon patching.

### 3. Delivery - `ApplyArtObject` on the muzzle node

`HazeManager` was rewritten. It no longer loads a NIF, clones geometry, or calls
`AttachChild`. It now:

1. Resolves the attach node, preferring `EquippedWeaponData::fireNode` - the node the
   engine itself resolves for the equipped weapon **including its attached mods**, which
   is what makes this work on modded weapons. Falls back to a name search of the
   first-person graph, then third-person, then the first-person root. The chosen node
   and which strategy won are logged.
2. Calls `ApplyArtObject(art, -1.0f, nullptr, false, false, node, false)`.
   `-1.0f` goes straight into `BSTempEffect::lifetime`, making it persistent.
   `a_attachToCamera` stays **false** - the camera branch discards the node.
3. Holds the returned `ModelReferenceEffect` in an `NiPointer` (it derives from
   `NiObject`, so this keeps it alive if ProcessLists tries to reap it mid-cycle).
4. Drives `BSLightingShaderMaterialBase::refractionPower` on `artObject3D` every heat
   tick.
5. Ends a cycle by setting `finished = true` and `lifetime = 0`, letting the engine reap
   it, rather than hand-rolling a detach.

All of this is grounded in the decompilation in
`docs\GhidraFindings_20260806_ApplyArtObject.md` - `a_3D` is returned verbatim by
`OwnedController::GetAttachRoot` whenever it is non-null.

### 4. Settings

```ini
[Haze]
sArtObjectPlugin=GunHeatHaze.esp
sArtObjectFormID=01000802
bPreferFireNode=1
fRefractionMinStrength=0.0
fRefractionMaxStrength=0.20

[ProjectileEmitter]
bEnabled=0
```

Refraction driving is back on and owned by the heat curve, so `0.4.0`'s constant-strength
test mode is over. Papyrus is unchanged - the `.pex` files are identical to `0.3.2`.

## Test

1. Install. `GunHeat.dll` should be **758784** bytes and the ESP **705** bytes.
2. First person, well-lit detailed wall. Fire a burst of ~6-10.

Expected:

- Distortion appears **on the barrel and stays there** when you turn, walk and strafe.
  This is the headline change - it is what the projectile carrier could never do.
- It fades in and out smoothly with no per-puff popping, because there is now exactly
  one object being updated instead of many being born and killed.
- No flame, no glow, no smoke, no damage, no decals.

## Log lines that matter

```text
art object path: plugin=GunHeatHaze.esp, formID=01000802, preferFireNode=true, ...
AttachHaze: attaching to '<node>' via EquippedWeaponData::fireNode
AttachHaze: art object applied to form 00000014
SetHazeStrength: art object 3D ready, root=<...>
SetHazeStrength: form=00000014, strength=..., refraction=..., node=<...> (<source>)
```

Diagnosis if it does not appear:

- `art object ... not found` - the ESP did not load or the form ID is wrong.
- `no attach node available` - node resolution failed; the log contains a tree dump.
- `ApplyArtObject returned null (Init failed)` - the engine rejected the effect. Real
  failure, since registration deletes the effect when `Init()` returns false.
- `art object 3D not ready yet` appearing forever - `BGSArtObjectCloneTask` never
  completed, which would point at the mesh rather than the attach path.
- **`via EquippedWeaponData::fireNode` but the effect sits in the wrong place** - that
  answers the one open question from the Ghidra pass: `fireNode` is the third-person
  instance. Set `bPreferFireNode=0` to force the first-person name search and retest.

## Tuning, no rebuild needed

The INI is re-read on every save load:

- `fRefractionMaxStrength` - intensity (vanilla 0.03-0.20).
- `bPreferFireNode` - attach strategy.
- Heat curve under `[Heat]` is unchanged and already validated.

Size and shape need the reshape tool plus a repack, not just an INI edit.
