r"""Compile the GunHeat Papyrus scripts with the game's own compiler.

The import path deliberately puts this workspace's Source\User FIRST, so the scripts being
compiled are this repository's and not a copy deployed in the game folder.

Output defaults to a directory you pass, so a build can be compared against the shipped .pex
before anything in Data\Scripts is replaced.

Usage:
    python -B tools/compile_papyrus.py <output dir> [GunHeat:GunHeatController ...]
"""

import subprocess
import sys
from pathlib import Path
from local_paths import required_path

ROOT = Path(__file__).resolve().parents[1]
GAME = Path(required_path('FALLOUT4_DIR'))
COMPILER = required_path("PAPYRUS_COMPILER")
SCRIPTS = ["GunHeat:GunHeatController", "GunHeat:GunHeatNative", "GunHeat:PlayerAlias"]

out = Path(sys.argv[1]).resolve()
targets = sys.argv[2:] or SCRIPTS
imports = ";".join(str(p) for p in (ROOT / "Data/Scripts/Source/User",
                                    GAME / "Data/Scripts/Source/Base",
                                    GAME / "Data/Scripts/Source/User"))
out.mkdir(parents=True, exist_ok=True)

failed = []
for script in targets:
    result = subprocess.run([str(COMPILER), script, "-f=Institute_Papyrus_Flags.flg",
                             f"-i={imports}", f"-o={out}"],
                            capture_output=True, text=True)
    log = (result.stdout + result.stderr).strip()
    ok = result.returncode == 0 and "compilation failed" not in log
    print(f"{'ok  ' if ok else 'FAIL'}  {script}")
    if not ok:
        failed.append(script)
        print("\n".join("        " + line for line in log.splitlines()))

for pex in sorted(out.rglob("*.pex")):
    print(f"  {pex.relative_to(out)}  {pex.stat().st_size} bytes")
sys.exit(1 if failed else 0)
