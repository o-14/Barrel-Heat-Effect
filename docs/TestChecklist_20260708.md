# Test Checklist — 2026-07-08 build (v0.2.1)

## v0.2.1 hotfix — invisible asset root cause

The first playtest showed the full pipeline working (quest start, heat 0→0.84, puffs
launching every ~0.22 s) but nothing visible. Cause: vanilla heat-refraction meshes keep
their **base Refraction Strength near zero** and animate it up through
`BSLightingShaderPropertyFloatController` only while the owning weapon's behavior graph
plays (minigun base = 0.0, animated to 1.0; our vaporizer-derived mesh sat at a static
0.125). Spawned as a bare projectile model, the animation never runs, so the mesh rendered
at near-zero distortion.

Fix (tools/patch_refraction_base_strength.py): base refraction on
`GunHeatRefractionOnlyStrong.nif` patched 0.125 → **0.8** (vanilla minigun peak is 1.0).
Runtime fade also made less suppressive: `fRuntimeFadeMinAlpha=0.3`,
`fRuntimeFadeInSeconds=0.5`. Heat intensity scaling still comes from puff size/cadence.
If the shimmer is now too strong/weak, re-run the patch tool with `--strength <value>`
(0.3–1.0 useful range) and redeploy the NIF.

## What changed in this build

1. **Controller quest restored to the esp.** `GunHeatHaze.esp` (526 bytes) now contains both
   records again: `GunHeatControllerQuest` (0x000800, Start Game Enabled, VMAD →
   `GunHeat:GunHeatController`) and `GunHeatHeatPuffProjectile` (0x000801). Until now the quest
   only existed inside the old test save; on a new game the mod would never have started.
   The DLL's `startquest` bootstrap on load should now resolve the quest instead of logging
   `controller quest lookup failed: resolved form ...`.
2. **All-firearms support.** `Config::IsWeaponAllowed` changed: the `sAllowedWeaponFormIDs`
   list is now an always-allow override, and with `[Weapons] bAllowAllWeapons=1` (now the
   shipped default) any weapon typed as a **gun** triggers heat — vanilla or modded. Melee,
   grenades, and mines are excluded by weapon type.
3. **Runtime fade enabled.** `[ProjectileEmitter] bRuntimeFadeEnabled=1` — every heat tick
   (0.03 s) the plugin now eases each live puff's alpha/scale toward the current strength
   (fade-in 1.2 s, fade-out 3.8 s time constants) instead of letting puffs pop in and out.
4. Rebuilt `GunHeat.dll` (2026-07-08) and redeployed everything loose into the game Data
   folder; re-added `*GunHeatHaze.esp` to `plugins.txt` (Vortex had removed the previous
   loose deployment to the Recycle Bin at 11:42 today).
5. New installable package: `dist\GunHeatHaze-0.2.0.zip` — install through Vortex
   ("Install From File") if you prefer it managed; delete the loose copies first so Vortex
   doesn't fight the same files.

## In-game verification steps

Launch via `f4se_loader.exe`, then watch `Documents\My Games\Fallout4\F4SE\GunHeat.log`.

1. **Main menu:** log shows `config loaded: ... allowAllWeapons=true ... projectileRuntimeFadeEnabled=true`.
2. **Load the test save** (or start a new game — this build should work there too).
   Expect `requesting controller quest start: startquest ...` and NO
   `controller quest lookup failed` warning.
3. **Fire a NON-assault-rifle gun** (e.g. 10mm pistol: `player.additem 4822 1`,
   `player.additem 1F276 200`, `player.equipitem 4822`). After ~2–3 quick shots expect
   `Papyrus: IsWeaponAllowed form=00004822, allowed=true` and `ProjectileEmitter: launched ...`.
4. **Melee/grenade negative test:** swing a melee weapon — no heat lines. (Throwing a
   grenade while a gun is equipped may still add one shot of heat; known minor issue.)
5. **Smooth fade:** dump a full magazine, then stop. Expect
   `ProjectileEmitter: runtime faded activeProjectiles=N ...` lines showing `alpha` easing
   down over several seconds; visually the shimmer should swell smoothly and dissipate
   without popping.
6. **Visual:** shimmer only — no glow, no smoke, no flame cards. If the distortion is too
   strong/weak, tune `[Heat] fMaxIntensity` and `[ProjectileEmitter] fMinScale/fMaxScale`.
7. **Save/reload mid-haze:** no stuck shimmer; firing again re-triggers.

## If the puff visual still pulses too much

The next step is the persistent-attach route (`SmoothFade_PersistentEffect_Route.md`): set
`[Haze] bAttachEnabled=1`, `bExtractGeometry=0`, `sHazeArtObject=GunHeatHaze\GunHeatRefractionOnlyStrong.nif`,
`[ProjectileEmitter] bEnabled=0`, and pick a first-person attach node (the FP tree dump in the
log lists candidates; `Camera` works as a placement sanity check). The HazeManager standalone
path (load → strip collision → attach → per-tick fadeAmount/refractionPower) is already in the
DLL and has not been crash-tested with the new NIF yet — test on a throwaway save.
