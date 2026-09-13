# Test checklist - 0.13.0 "reset heat on weapon switch"

Package: `dist/GunHeatHaze-0.13.0-heat-reset-on-switch.zip` (13 files, 493975 bytes)
DLL: 802816 bytes. Proven 0.11.4 sources at `_backup/0.11.4-proven/`.

Carries the 0.12.3 culling fix, which is confirmed working - see
`TestChecklist_20260827_CullWhenInvisible.md`.

## What this adds

`[Heat] bResetHeatOnWeaponSwitch`, default **on**, also exposed in MCM as
**"Reset heat on weapon switch"**. Heat belongs to the barrel you are holding, so carrying
it from a red-hot minigun onto a freshly drawn pistol was physically wrong.

### How the switch is detected

On the **weapon form ID**, not the muzzle node. The node pointer also changes on camera
transitions and reloads - the 0.12.2 session logged 7 `muzzle node changed` events across
730 shots - so keying the reset on the node would have reset heat spuriously. The weapon is
now passed from Papyrus into the `AddHeat` native, which compares it against the weapon the
current heat belongs to.

Two consequences worth knowing:

- The reset lands on the **first shot fired with the new weapon**, not at the instant of the
  switch. The DLL only learns which weapon you are holding when a shot is reported.
- `visible` is deliberately **not** zeroed. Any shimmer still up fades out on the normal
  ramp instead of vanishing on the frame of the switch; it simply now ramps toward the new
  weapon's much lower target. `heat`, `peakHeat` and any live puffs are cleared.

## RESULT - confirmed working (session 18:21-18:27, 1437 shots)

**The reset behaves exactly as designed:**

```
weapon changed (0000463F -> 00004822); resetting heat from 0.50195885
AddHeat: shot=0.11618951, heat=0.11618951, visible=0.50195885, peak=0.11618951
```

`heat` and `peakHeat` drop to just the new shot; `visible` is preserved at 0.502 so the
shimmer already on screen rides the normal ramp down instead of popping off.

**No spurious resets.** 2 resets across 1437 shots, against exactly 2 real weapon swaps
(`463F -> 4822`, then `4822 -> 463F`). `muzzle node changed` also fired twice, so the node
happened to be stable this session - but the weapon-ID key is what guarantees it.

Caliber scaling is visibly working alongside it: weapon `00004822` has `damageProxy=18,
multiplier=0.7746`, giving `shotHeat=0.116` rather than the `0.15` of `0000463F`.

| measurement | value |
| --- | --- |
| shots | 1437 |
| resets / real swaps | 2 / 2 |
| `AttachHaze: art object applied` | 1 |
| `DetachHaze: released` | 0 |
| `parking attachment` | 1 |
| cull transitions | 3 culled / 3 shown |
| warnings / errors | 0 / 0 |
| tick cost | ~600 us per second |

**Not exercised:** step 3 (toggle off). Both switches reset, so the setting was on
throughout. Worth a quick pass if the off state matters.

### One outlier

A single 105ms tick in 301 sampled seconds:

```
Tick rate: 104 ticks/sec, 106132 us total, 105631 us worst
```

Nothing in the surrounding window explains it structurally - no attach, re-attach or
first-3D-ready. The most likely cause is the logger: `flush_on(info)` forces a synchronous
disk write per line, this session wrote 1.2 MB, and a stall inside the timed region is
billed to the tick. It should disappear with `bDebugLogging=0`. Worth revisiting only if a
hitch is actually visible in play.

## Verify

1. **The reset.** Heat a weapon until the shimmer is strong, switch to a different gun, fire
   one shot. The shimmer should fall away to that single shot's level rather than continuing
   from the previous barrel's heat. Log:

   ```
   AddHeat: weapon changed (0000463F -> 0001F669); resetting heat from 0.87
   ```

   This line is logged unconditionally, so it appears with `bDebugLogging=0` too.

2. **No spurious resets.** Fire one weapon continuously through reloads, and toggle between
   first and third person mid-cycle. `weapon changed` must **not** appear - only genuine
   weapon swaps should trigger it.

3. **Toggle off.** Set the MCM switch off (or `bResetHeatOnWeaponSwitch=0`), repeat step 1,
   and confirm heat carries across the switch as it used to.

4. **Regression check on 0.12.3.** Performance still good, `card culled` / `card shown`
   still pairing, cycles still parking.

## Housekeeping

`bDebugLogging` is still on in your MCM settings - worth setting to 0 for normal play now
that the performance question is closed. The `weapon changed` line above survives that.
