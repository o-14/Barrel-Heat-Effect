"""Build GunHeat while normalizing the duplicate PATH/Path Codex environment.

MSBuild and Ninja cannot launch compiler children when both case variants are
present. This wrapper gets a clean Visual Studio developer environment, asks
Ninja for the dirty commands, and executes those commands sequentially.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from local_paths import required_path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "GunHeatPlugin" / "build-codex"
VSDEV = Path(required_path('VSDEVCMD'))
NINJA = Path(
    required_path('NINJA_EXE')
)


def clean_parent_environment() -> dict[str, str]:
    source_path = os.environ.get("PATH") or os.environ.get("Path", "")
    result = {key: value for key, value in os.environ.items() if key.lower() != "path"}
    result["Path"] = source_path
    return result


def developer_environment() -> dict[str, str]:
    command = f'call "{VSDEV}" -arch=x64 -host_arch=x64 >nul && set'
    result = subprocess.run(
        [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", command],
        cwd=BUILD,
        env=clean_parent_environment(),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        raise RuntimeError(f"VsDevCmd failed with exit code {result.returncode}")

    environment: dict[str, str] = {}
    path_value = ""
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.lower() == "path":
            path_value = value
            continue
        environment[key] = value
    environment["Path"] = path_value
    return environment


def dirty_commands(environment: dict[str, str]) -> list[str]:
    result = subprocess.run(
        [str(NINJA), "-n", "-v", "GunHeat.dll"],
        cwd=BUILD,
        env=environment,
        text=True,
        capture_output=True,
        check=True,
    )
    commands: list[str] = []
    for line in result.stdout.splitlines():
        match = re.match(r"^\[\d+/\d+\]\s+(.*)$", line)
        if match:
            commands.append(match.group(1))
    return commands


def main() -> int:
    environment = developer_environment()
    commands = dirty_commands(environment)
    if not commands:
        print("GunHeat.dll is up to date")
        return 0

    for index, command in enumerate(commands, start=1):
        print(f"[{index}/{len(commands)}] building")
        result = subprocess.run(command, cwd=BUILD, env=environment, shell=True)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
