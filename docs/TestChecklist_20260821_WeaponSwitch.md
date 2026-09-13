# Weapon switch fix - 2026-08-21

Build: `dist\GunHeatHaze-0.11.1-weaponswitch-fix.zip`

## Found it in the logs

The log looks completely healthy - 5 attaches, 0 warnings, every one resolving
`ProjectileNode` via `EquippedWeaponData::fireNode`, art object 3D ready every time. That
is exactly why this was invisible from the mod's own diagnostics.

The tell is in which weapon was equipped for each cycle:

```text
294 shots  weapon 0000463F   -> all 5 attach cycles
 40 shots  weapon 00004822   -> ZERO attach cycles
```

The second weapon fired 40 times and never started a cycle. Tracing to its first shot at
line 10497:

```text
UpdateHeat: heat=0.845930, visible=0.845930
weaponFire: weapon=[Weapon < (00004822)>], heat=0.962119
SetHazeStrength: ... node=ProjectileNode (EquippedWeaponData::fireNode)
```

Heat was **already at 0.85 and a cycle was already open** - the last lifecycle event before
the switch was an attach at line 6835, with no detach after it.

## Why it never recovered

`OnAnimationEvent` only starts a cycle when `!hazeActive`. Because the cycle from the
previous weapon was still running, every shot from the new weapon took the `else` branch -
pulse and apply strength - and `SetHazeStrength` drove the art object that was **still
parented to the previous weapon's muzzle node**.

That node still exists (we hold a reference to it), but it is no longer part of the
rendered first-person weapon, so the effect is drawn nowhere. Everything downstream still
reports success.

The only escape was the cycle ending, which needs heat to reach zero. Across the entire
span the second weapon was in use, minimum heat was **0.846** - it never got close. And
because firing keeps topping heat up, continuing to shoot guarantees it never recovers.
Exactly the behaviour you described.

## Fix

`ApplyArtObject` binds its attach root once, at creation - there is no way to re-point a
live effect. So the DLL now re-resolves the fire node on each heat tick and, if it has
changed, ends the old effect and re-applies the art object to the new node:

```text
SetHazeStrength: muzzle node changed ('ProjectileNode' -> 'ProjectileNode'), art object re-applied
```

Notes on the implementation:

- Only runs when `bPreferFireNode=1`, because that path is a cheap walk of the equipped
  items array. The name-search fallback would be a full tree traversal and is far too
  expensive to repeat 20 times a second.
- Heat, puffs and the rest of the cycle carry over untouched; only the attachment moves.
- The smear sample is reset on re-attach, otherwise the switch itself registers as one
  enormous jump in muzzle velocity and flings the card.

This also covers weapon-mod changes and any other cause of the muzzle node being rebuilt,
not just switching weapons.

## Separate observation worth a decision

**Heat currently carries across a weapon switch.** In this log the new weapon inherited
0.85 heat from the previous one and was instantly at near-max. Physically that is wrong -
it is a different barrel - and it also means the first shot with a fresh weapon shows a
fully hot effect.

I have not changed this, because it is a behaviour change you have not asked for. Say the
word and I will reset heat on weapon change, either always or behind an MCM toggle.

## Test

1. Install. `GunHeat.dll` is **779264** bytes.
2. Heat up weapon A until the effect shows, then switch to weapon B **while it is still
   visible** and keep firing. The effect should appear on B.
3. The log should show `muzzle node changed ... art object re-applied` at the switch.
