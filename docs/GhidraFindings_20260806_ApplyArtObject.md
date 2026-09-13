# Ghidra findings - ApplyArtObject and the attach path (2026-08-06)

Source: `Fallout4.exe.unpacked.exe` 1.10.163 OG, base `0x140000000`, in the
BethesdaGhidraScripts project, read over the GhidraMCP bridge. Read-only - nothing in the
Ghidra database was modified.

Addresses resolved from `Data\F4SE\Plugins\version-1-10-163-0.bin` with the new
`tools\addresslib_lookup.py`.

| REL::ID | RVA | Address | What |
| --- | --- | --- | --- |
| 357908 | `0x00514e50` | `0x140514e50` | `TESObjectREFR::ApplyArtObject` |
| 652173 | `0x00422180` | `0x140422180` | `TESObjectREFR::ApplyEffectShader` |
| 663107 | `0x00e044d0` | `0x140e044d0` | `Actor::GetCurrentFireLocation` |
| 1452334 | `0x00fca260` | `0x140fca260` | projectile launch (used by `ProjectileEmitter`) |

Note: Fallout 4's address library is **not** the delta-encoded SKSE v2 format. It is a
flat table - `uint64 count`, then `count x { uint64 id; uint64 rva; }`. For
1.10.163: 1,582,975 entries, `8 + 1582975*16 == 25327608` bytes exactly.

---

## 1. `a_3D` is honoured. This is the answer we needed.

`ApplyArtObject` (`0x140514e50`) decompiles to:

```c
if (a_attachToCamera == 0) {
    controller = Allocate(0x28);
    OwnedController_ctor(controller, this, a_art, a_facingRef, a_3D);   // a_3D passed through
} else {
    controller = Allocate(0x30);
    CameraController_ctor(controller, a_art, a_inheritRotation);        // a_3D ignored
}
effect = Allocate(0xD8);          // sizeof(ModelReferenceEffect) == 0xD8, matches CommonLibF4
ModelReferenceEffect_ctor(effect, controller);
Register(effect, a_time, a_interfaceEffect);
return effect;
```

`OwnedController_ctor` (`0x1401c7580`) stores it and **takes a reference**:

```c
*controller      = &VTABLE_OwnedController;
controller[2]    = a_art;            // +0x10
controller[3]    = a_3D;             // +0x18
if (a_3D) atomic_increment(*(int*)(a_3D + 8));   // NiRefObject::refCount
```

`OwnedController::GetAttachRoot` is vtable slot `+0x78` (index `0x0F`) at
`VTABLE_OwnedController = 0x142c5d9b8`, giving `0x140c7d270`:

```asm
MOV  RAX, [RCX + 0x18]   ; this->attach3D
TEST RAX, RAX
JNZ  epilogue            ; non-null -> return it, untouched
MOV  RAX, [RCX]
CALL [RAX + 0x58]        ; GetTargetReference()      (vtable index 0x0B)
TEST RAX, RAX
JZ   epilogue
MOV  RAX, [RAX]
JMP  [RAX + 0x460]       ; tail-call ref->Get3D()    <- third-person fallback
epilogue:
ADD  RSP, 0x28
RET                      ; RAX = attach3D
```

**Conclusion:** pass a non-null `a_3D` and the engine attaches there and nowhere else.
`GetTargetReference()->Get3D()` is only reached when `a_3D` is null. Nothing in this path
inspects whether the node belongs to the first-person or third-person graph, so a
first-person node is acceptable to the engine. The refcount increment means the engine
holds the node alive for the effect's lifetime.

This removes the single biggest unknown in Route A. The intended call is:

```cpp
player->ApplyArtObject(heatArt, -1.0f, nullptr, false, false, muzzleNode, false);
```

`a_attachToCamera` **must stay false** - the camera path discards `a_3D` entirely.

---

## 2. Lifetime and teardown

The registration tail (`0x140c7be70`) is:

```c
effect->lifetime = a_time;               // BSTempEffect + 0x10   (matches CommonLibF4)
effect->ownController = true;            // ReferenceEffect + 0x41 (matches CommonLibF4)
effect->SetInterfaceEffect(a_interfaceEffect);
if (effect->Init())
    ProcessLists::AddTempEffect(g_processLists, effect);
else
    effect->~dtor(deleting);             // Init failure deletes it immediately
```

So:

- `a_time` is written straight into `BSTempEffect::lifetime`. Passing `-1.0f` gives a
  persistent effect, which is what a heat cycle wants.
- `Init()` gates registration. If it returns false the effect is destroyed before we ever
  see it - so a null return from `ApplyArtObject` is a real failure signal worth logging.
- Ending it early means touching `ReferenceEffect::finished` (`+0x40`) or shortening
  `lifetime` (`+0x10`), not calling a detach function.

---

## 3. `GetCurrentFireLocation` does not use `fireNode`

`Actor::GetCurrentFireLocation` (`0x140e044d0` -> `0x140e045e0`) interpolates a position
out of the `fireLocations` stance/aim grid on `EquippedWeaponData` (`+0x40`), then adds
the actor's world position. It never reads `fireNode` (`+0x30`).

It does contain a player-and-first-person-specific branch - `param_1 == <player
singleton>` combined with a camera vfunc at `+0x470` - which is why the existing
projectile origin lands roughly at the first-person muzzle.

**Implication:** `fireNode` still needs its own confirmation, but it is no longer
blocking. Because `a_3D` is honoured unconditionally, the attach node can be resolved by
whatever means works and simply handed to `ApplyArtObject`. That is now a runtime
question answerable with one logged tree dump, not an architectural risk.

### RESOLVED in-game, 2026-08-10 (build 0.5.0)

`EquippedWeaponData::fireNode` **is correct in first person.** Across 28 heat cycles it
resolved every single time, to a node named **`ProjectileNode`**, and the effect stayed
locked to the barrel through turning, walking and strafing:

```text
28x  AttachHaze: attaching to 'ProjectileNode' via EquippedWeaponData::fireNode
 0x  any fallback strategy (name search / first-person root / third-person)
```

That makes the universal-attachment problem solved: `fireNode` is the node the engine
itself resolves for the equipped weapon **including its attached mods**, so vanilla and
modded guns are handled identically with no per-weapon patching and no name matching.
The name-search fallbacks in `HazeManager::ResolveAttachNode` are now dead paths kept
only as insurance.

---

## 4. What this means for the build

Route A is confirmed viable as designed:

1. Author the heat card - **done**, and proven to render (`0.4.0`).
2. Add one `ARTO` record pointing at it.
3. Resolve the muzzle node - try `EquippedWeaponData::fireNode` first, fall back to a
   named search of the first-person graph, and log which one won.
4. `ApplyArtObject(art, -1.0f, nullptr, false, false, node, false)`, keep the returned
   `ModelReferenceEffect*`, and drive `refractionPower` on `artObject3D` each frame from
   the existing heat curve.
5. End the cycle by setting `finished` / `lifetime` rather than hand-rolling a detach.
6. Retire `ProjectileEmitter` and the `PROJ` carrier.

Still worth pulling from Ghidra when needed: the `MuzzleFlash` layout (Route B fallback),
and confirming which node `fireNode` actually holds.
