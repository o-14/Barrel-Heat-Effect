# Gun Heat Haze Test Checklist - 2026-07-13

## Test Setup

1. Run Fallout 4 `1.10.163` through F4SE `0.6.23`.
2. Enable `GunHeatHaze.esp`.
3. Test in first person with the vanilla Assault Rifle first. The Minigun already has a native heat effect and is not a clean comparison.
4. Use a well-lit area with a detailed wall or object behind the muzzle so refraction is easy to see.

## Expected Behavior

- A few isolated shots should produce little or no visible haze.
- Sustained fire should build a narrow distortion around and forward of the muzzle.
- The distortion texture should move rather than remain frozen.
- Releasing the trigger should produce a smooth intensity falloff.
- A longer burst should linger longer than a short burst.
- No flame, smoke, custom muzzle flash, light, damage, or impact should be added by Gun Heat Haze.
- Vanilla and modded firearms should work without weapon-specific patches when `[Weapons] bAllowAllWeapons=1`.

## Log Checks

After testing, inspect `Documents\My Games\Fallout4\F4SE\GunHeat.log`.

Look for:

```text
caliber heat: weapon=..., ammo=..., projectile=..., multiplier=..., heatPerShot=...
ProjectileEmitter: controller sequence mSprayStart activated=true
ProjectileEmitter: launched copy=... handle=<nonzero>
ProjectileEmitter: runtime faded ... lifetimeEnvelope=... refraction=... controllerStarted=true
```

If the effect is visible but static, capture the controller line. If it appears or disappears abruptly, capture several consecutive `runtime faded` lines. If nothing appears, capture the first `launched copy` line and any controller warning.
