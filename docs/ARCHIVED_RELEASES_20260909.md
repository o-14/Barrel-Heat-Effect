# Archived visual trials: 0.18.0 and 0.19.0

The user rejected these visual designs in game and requested archival on
2026-09-09. Both complete install archives now reside under the original project:

- `dist/Archived/0.18.0/GunHeatHaze-0.18.0-barrel-heat-flow.zip`
  SHA256 `2bf7b9ad3f1a8ad49cb5343428e357b48e5a22a89efa16207f1bbbd11dacbef6`.
- `dist/Archived/0.19.0/GunHeatHaze-0.19.0-barrel-plume.zip`
  SHA256 `bc4c102d3c2f85ddbdf56176d15ebb23a1a4c636bcd5aab68b89dcb18bec36f3`.
- The 259-file 0.19.0 editable source snapshot is now at
  `dist/Archived/0.19.0/source-0.19.0-barrel-plume`.

All moved files were hashed before and after; contents are unchanged. The archive
manifest is `dist/Archived/ARCHIVE_MANIFEST_20260909.json`. Later-version Git
branches and isolated worktrees are retained for history, not active development.
No original releases or backups were deleted.

The original 0.17.1 archive remains at `dist/GunHeatHaze-0.17.1-mcm-defaults-fix.zip`.
All 12 files match the original checkout's Data files byte-for-byte. Refinement
starts independently from b073124 on `codex/refine-0171`.

This source/package rollback does not operate Vortex. To restore the installed
game, disable the later version, enable the original 0.17.1 release and deploy.
