# GunHeat 1.0.0

The first stable release. Two changes on top of 0.21.0: the unused `PROJ` record is gone from the
esp, and the version is 1.0.0. **Nothing about the effect changed** — no default, no value, no mesh,
no texture, no script.

Alongside it, the public source repository now exists, built from a fresh history that has never
contained Fallout 4-derived art. It is committed locally and **not pushed**; see below.

## Packages

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `dist/GunHeatHaze-1.0.0.zip` | 655146 | `77ff08003dda029ef49617383de625c4616f3027f702dfbe94fd6b6b75f390a8` |
| `dist/GunHeatHaze-1.0.0-source.zip` | 3528250 | `4b7d16f16786abe8216abcdf4e0562fff5d39be023f8a20e29b402b59a844c74` |
| `Data/F4SE/Plugins/GunHeat.dll` | 695808 | `4c367507c8a212bc56f5f49e7cf65e88086e68b6b58af88c2f9be953eb20da38` |
| `Data/GunHeatHaze.esp` | 442 | `3a5ed81f4b8fd7d914f125de085e38dd2235a4f6c9c7364844730b59102cac34` |

**17 of the 20 packaged entries are byte-identical to 0.21.0** — the DLL, the esp and `README.txt`
changed. Full hashes in `docs/release-1.0.0/release-validation.json`.

## The esp

`PROJ 01000801 GunHeatHeatPuffProjectile` was 263 bytes left from the abandoned projectile
experiment. `tools/strip_esp_record.py` removes it and refuses to act on anything it cannot prove
safe first:

- the group must hold exactly the one record, and its FormID must be the one named on the command
  line;
- **the FormID must occur exactly once in the whole file** — in the record's own header. A referenced
  record would leave a dangling pointer that the game resolves to whatever else holds that ID.

Both guards were exercised by pointing the tool at the wrong record and at the wrong FormID.

What the removal actually did:

| | Before | After |
| --- | --- | --- |
| esp size | 705 bytes | 442 bytes |
| Records | QUST, PROJ, ARTO | QUST, ARTO |
| `HEDR` numRecords | 3 | 2 |
| `nextObjectID` | `00000803` | `00000803`, unchanged, so `01000801` is never reused |

`QUST 01000800` and `ARTO 01000802` come through **byte-identical**, and TES4 differs at exactly one
place, offset 34, the record count. FormIDs are stored rather than positional, so a save that already
knows the quest or the art object is unaffected.

## The DLL

Only the version changed. Against 0.21.0 it differs in 304 bytes, which sounds worse than it is —
`1.0.0` is one character shorter than `0.21.0`, so the whole version resource shifts. Diffed section
by section:

| Section | Differing bytes | What |
| --- | ---: | --- |
| `.text` | 89 | 87 are the link non-determinism region documented since 0.20.0; **2 are the Query immediate**, `0x00150000` to `0x01000000` |
| `.rsrc` | 195 | the version resource, shifted by the shorter string |
| `.rdata`, `.data` | 20 | the version string, `pluginVersion`, PDB age, timestamps |
| `.pdata`, `.reloc` | 0 | identical |

`F4SEPlugin_Version.pluginVersion` and `F4SEPlugin_Query` both report `0x01000000`, and
`compatibleVersions` still lists 1.10.984, 1.11.221 and 1.11.240.

## The public repository

Built at `<local-path>`, branch `main`, commit `ba59c7d`, **157
files**, one commit, no remote.

Kept out, and each checked rather than assumed:

| Excluded | Why |
| --- | --- |
| 29 Fallout 4-derived `.nif` and `.dds` | Bethesda's, and a public repo is redistribution — in the history for good |
| another mod's files under `analysis/` | not ours to publish |
| the built DLL and the three `.pex` | build output, and every `.pex` header embeds the compiling **account name, machine name and source path** |
| agent handoffs and session prompts | local paths and working process |
| `__pycache__` | build output |

Verified on a clean clone:

- `git ls-files` and `git log --all --name-only` find no `.nif` or `.dds` — never present, not merely
  deleted.
- None of the 157 files contains the account name or the machine name.
- The submodule gitlink records the pin `2aaefd1`. **This was wrong once and caught here**: `git add
  -A` before an amend silently dropped the gitlink, because the submodule directory does not exist on
  disk. The fix is to re-add it with `git update-index --add --cacheinfo 160000,<sha>,<path>` after
  any `git add`, and to check `git ls-files -s | grep 160000` in a fresh clone rather than trusting
  the working tree.
- A fresh clone fetches all three submodules at exactly the pinned commits.
- **A fresh clone builds**: 36 seconds, 695,808 bytes, `pluginVersion 0x01000000`, all three exports
  present.

Two things learned while proving that, now in the repo's README:

- The DLL lands in `GunHeatPlugin/build/...`, not `build-xmake/...`; only `tools/build_0200.py` uses
  the latter.
- Building from Git Bash fails with `cannot get program for cc` while installing spdlog, because both
  `PATH` and `Path` are set there. PowerShell is fine, and `build_0200.py` normalises the environment.

`LICENSE` and `packaging/Licenses/GPL-3.0.txt` are the same text with different line endings — the
`.gitattributes` checks `.txt` out as CRLF for Windows players and `LICENSE` as LF. That is
deliberate, not drift.

### What is left to do, which is yours

Nothing has been pushed; creating a public repository is not something to do on your behalf. When
you are ready:

```
gh repo create GunHeatHaze --public --source <local-path>
```

or, with the repository already created on GitHub:

```
cd <local-path>
git remote add origin https://github.com/<you>/GunHeatHaze.git
git push -u origin main
git tag -a v1.0.0 -m "Gun Heat Haze 1.0.0" && git push origin v1.0.0
```

Then attach `GunHeatHaze-1.0.0.zip` to a GitHub Release on that tag, publish its SHA256 from the
table above, and link the Release from the Nexus page — that link is what satisfies the GPL's
corresponding-source duty. `docs/GITHUB_HANDOFF.md` has the rest, including the release routine and
the traps.

Do **not** attach `GunHeatHaze-1.0.0-source.zip` to a GitHub Release: it is a `git archive` of the
private repository and contains the art. On Nexus it is fine, because the art ships there anyway.

## Test checklist

Short pass — the effect code is 0.20.2's, already played on 1.10.163 and 1.11.240.

1. Install `GunHeatHaze-1.0.0.zip` with no other version active, deploy, restart the game.
2. `f4se.log` should read `plugin GunHeat.dll (00000001 GunHeat 01000000) loaded correctly`, on every
   runtime including 1.10.163.
3. `GunHeat.log` should open with `GunHeat v1.0.0 on Fallout 4 <version> (<family> runtime)`.
4. **Load an existing save that has the mod.** The esp lost a record; the two that remain kept their
   FormIDs, so it should load with no warning and the effect should behave exactly as before.
5. Fire a sustained burst. Any visible difference from 0.20.2 is a regression.
6. Still outstanding since 0.20.0: in-game passes on **1.10.984** and **1.11.221**.

**Send back:** `GunHeat.log` and `f4se.log`, plus the crash log if the game crashes.

## Rollback

`dist/GunHeatHaze-0.21.0.zip` and every earlier release are untouched. The pre-1.0.0 snapshot is
`Backups/before-1.0.0-release-20260911`, which keeps the three-record esp, the 0.21.0 DLL, the README
and the build file.
