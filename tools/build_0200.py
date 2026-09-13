"""Build GunHeat 0.20.0+ with xmake against the pinned Dear-Modding CommonLibF4.

One DLL for Fallout 4 1.10.163, 1.10.984, 1.11.221 and 1.11.240. Output stays in
GunHeatPlugin/build-xmake/. Nothing is copied into the game or into Data/: copy the verified DLL
into Data/F4SE/Plugins deliberately before packaging, as with 0.17.x.

The build refuses to run if any library submodule has drifted from its pinned commit, because the
relocation IDs and struct layouts this release was verified against live in those commits.

Usage:
    python -B tools/build_0200.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from local_paths import required_path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "GunHeatPlugin"
BUILD = PLUGIN / "build-xmake"
XMAKE = Path(required_path('XMAKE_EXE'))

# The exact commits BPR 3.0.1 ships against, and that the 0.20.0 ID and layout checks used.
PINS = {
    "GunHeatPlugin/lib/commonlibf4": "2aaefd104754b59b16e435b2859b299bb68dd8a2",
    "GunHeatPlugin/lib/commonlibf4/lib/commonlib-shared": "e30b310a19621ff9f635cf2c456fe633559c1c24",
    "GunHeatPlugin/lib/commonlibf4/lib/dearmoddingui-api": "9ddb9a8dacef8c5a116fabd3fe3a453cc446f830",
}


def clean_environment() -> dict[str, str]:
    # Duplicate PATH/Path variants break compiler child processes on this machine; the 0.17.x
    # helper normalises them the same way.
    env = {key: value for key, value in os.environ.items() if key.lower() != "path"}
    env["PATH"] = os.environ.get("PATH") or os.environ.get("Path", "")
    # Either variable would redirect the plugin rule's automatic install into a game or mod
    # folder. This build must never deploy.
    env.pop("XSE_FO4_MODS_PATH", None)
    env.pop("XSE_FO4_GAME_PATH", None)
    return env


def check_pins() -> None:
    for relative, expected in PINS.items():
        actual = subprocess.check_output(
            ["git", "-C", str(ROOT / relative), "rev-parse", "HEAD"], text=True
        ).strip()
        if actual != expected:
            raise SystemExit(f"{relative} is at {actual}; expected pinned {expected}")


def xmake(*args: str, log) -> None:
    command = [str(XMAKE), *args]
    log.write(f"\n+ xmake {args[0]}\n")
    log.flush()
    result = subprocess.run(
        command, cwd=PLUGIN, env=clean_environment(), stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
    )
    safe_output = re.sub(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/][^\n\r]*", "[local build output]", result.stdout)
    log.write(safe_output)
    log.flush()
    if result.returncode != 0:
        tail = "\n".join(result.stdout.splitlines()[-80:])
        raise SystemExit(f"xmake {args[0]} failed ({result.returncode}):\n{tail}")


def main() -> None:
    if not XMAKE.is_file():
        raise SystemExit(f"xmake not found at {XMAKE}")
    check_pins()
    BUILD.mkdir(exist_ok=True)
    with (BUILD / "build-0200.log").open("w", encoding="utf-8") as log:
        xmake("f", "-y", "-p", "windows", "-a", "x64", "-m", "releasedbg", "-o", str(BUILD), log=log)
        # -w: xmake hides compiler warnings unless asked, which would make a clean log meaningless.
        xmake("build", "-y", "-w", "BarrelHeatEffect", log=log)

    dll = BUILD / "windows" / "x64" / "releasedbg" / "BarrelHeatEffect.dll"
    if not dll.is_file():
        raise SystemExit(f"build reported success but {dll} is missing")
    print(f"built {dll} ({dll.stat().st_size} bytes)")
    print(f"log: {BUILD / 'build-0200.log'}")


if __name__ == "__main__":
    sys.exit(main())
