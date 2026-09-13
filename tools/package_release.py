r"""Package a complete Vortex-installable archive, and its GPL corresponding source, under dist/.

The install archive keeps the Data-level layout of every earlier release: everything sits at
archive root so a mod manager installs it straight into Data/. The manifest is explicit rather than
a glob over Data/ because Data/Meshes/GunHeatHaze holds dead experiment assets and backup sidecars
(that folder keeps its old name: the path is stored inside the esp and inside the NIF)
that must not ship.

From 0.20.0 the DLL links Dear Modding FO4's CommonLibF4 (GPL-3.0-or-later with exceptions), so:

- the license and notice files from packaging/ go at archive root beside the mod, as in BPR;
- a second archive, BarrelHeatEffect-<label>-source.zip, carries the corresponding source: this
  repository at HEAD plus every pinned CommonLibF4 submodule. It is refused while the working tree
  is dirty, so it always matches a commit.

--baseline compares every shipped file except the DLL against a previous release. Files that differ
only in line endings - git auto-CRLF rewrites checked-out scripts on this machine - are packaged
with the baseline's exact bytes. Any real content difference stops the build, because a change that
was not intended for this release should not slip into it.

A release that does intend to change one of those files declares it: --changed <manifest entry>,
repeated per entry. The entry is then packaged from the working tree and reported as changed, while
every other file is still held to the baseline. Anything not declared still stops the build.

Both archives use exclusive creation and will not overwrite an existing package.

Usage:
    python -B tools/package_release.py 1.1.0 --baseline <previous release zip>
    python -B tools/package_release.py 1.1.0 --baseline <zip> --changed F4SE/Plugins/BarrelHeatEffect.ini
"""

from __future__ import annotations

import argparse
import io
import subprocess
import zipfile
from pathlib import Path
from pex_metadata import neutralize
from privacy_checks import check

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"
PACKAGING = ROOT / "packaging"
# Releases live directly under the project's dist/; worktrees sit inside that folder.
DIST = ROOT.parent if ROOT.parent.name == "dist" else ROOT / "dist"

DLL = "F4SE/Plugins/BarrelHeatEffect.dll"

# Only the current reduced-strength normal copy ships; older unused textures stay in source.
MANIFEST = [
    DLL,
    "F4SE/Plugins/BarrelHeatEffect.ini",
    "BarrelHeatEffect.esp",
    "MCM/Config/BarrelHeatEffect/config.json",
    "MCM/Config/BarrelHeatEffect/settings.ini",
    "Meshes/GunHeatHaze/GunHeatBarrelRefractionCard.nif",
    "Textures/GunHeatHaze/Soft0172_n.dds",
    "Scripts/GunHeat/GunHeatController.pex",
    "Scripts/GunHeat/GunHeatNative.pex",
    "Scripts/GunHeat/PlayerAlias.pex",
    "Scripts/Source/User/GunHeat/GunHeatController.psc",
    "Scripts/Source/User/GunHeat/GunHeatNative.psc",
    "Scripts/Source/User/GunHeat/PlayerAlias.psc",
]

# Archive-root license and notice files, sourced from packaging/.
EXTRAS = [
    "COPYRIGHT.md",
    "README.txt",
    "THIRD_PARTY_NOTICES.md",
    "Licenses/GPL-3.0.txt",
    "Licenses/GPL-3.0-EXCEPTIONS.txt",
    "Licenses/CommonLibF4-MIT.txt",
    "Licenses/spdlog-MIT.txt",
]


def git(*args: str, cwd: Path = ROOT) -> bytes:
    return subprocess.check_output(["git", *args], cwd=cwd)


def submodules() -> list[str]:
    listing = git("submodule", "status", "--recursive").decode()
    return [line.split()[1] for line in listing.splitlines() if line.strip()]


def shipped_bytes(entry: str, baseline: zipfile.ZipFile | None, changed: set[str]) -> tuple[bytes, str]:
    current = (DATA / entry).read_bytes()
    if entry.lower().endswith('.pex'):
        current = neutralize(current)
    check(current, text=entry.lower().endswith(('.ini', '.json', '.psc')))
    if baseline is None or entry == DLL or entry not in baseline.namelist():
        return current, "new" if baseline is not None and entry != DLL else ""
    previous = baseline.read(entry)
    if current == previous:
        return current, "identical to baseline"
    if current.replace(b"\r\n", b"\n") == previous.replace(b"\r\n", b"\n"):
        return previous, "line endings differed; baseline bytes used"
    if entry in changed:
        return current, "CHANGED in this release, declared with --changed"
    raise SystemExit(f"{entry} differs in content from the baseline release; not packaging it silently.\n"
                     f"If the change is intended, declare it: --changed {entry}")


def build_install_archive(label: str, baseline_path: Path | None, changed: set[str]) -> Path:
    missing = [e for e in MANIFEST if not (DATA / e).is_file()]
    missing += [f"packaging/{e}" for e in EXTRAS if not (PACKAGING / e).is_file()]
    if missing:
        raise SystemExit("missing package inputs:\n  " + "\n  ".join(missing))

    unknown = changed - set(MANIFEST)
    if unknown:
        raise SystemExit("--changed names entries that are not in the manifest:\n  " + "\n  ".join(sorted(unknown)))

    target = DIST / f"BarrelHeatEffect-{label}.zip"
    baseline = zipfile.ZipFile(baseline_path) if baseline_path else None
    try:
        with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED) as archive:
            for entry in MANIFEST:
                data, note = shipped_bytes(entry, baseline, changed)
                archive.writestr(entry, data)
                print(f"  + {entry} ({len(data)} bytes){'  - ' + note if note else ''}")
            for entry in EXTRAS:
                data = (PACKAGING / entry).read_bytes()
                check(data, text=True)
                archive.writestr(entry, data)
                print(f"  + {entry} ({len(data)} bytes)")
    finally:
        if baseline:
            baseline.close()
    count = len(MANIFEST) + len(EXTRAS)
    print(f"\nWrote {target} ({target.stat().st_size} bytes, {count} files)")
    return target


def build_source_archive(label: str) -> Path:
    if git("status", "--porcelain", "--ignore-submodules=none").strip():
        raise SystemExit("working tree is dirty; commit first so the source archive matches a commit")

    prefix = f"BarrelHeatEffect-{label}-source/"
    target = DIST / f"BarrelHeatEffect-{label}-source.zip"
    trees = [(ROOT, "")] + [(ROOT / path, path.replace("\\", "/") + "/") for path in submodules()]
    count = 0
    with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED) as archive:
        for tree, subpath in trees:
            blob = git("archive", "--format=zip", "HEAD", cwd=tree)
            with zipfile.ZipFile(io.BytesIO(blob)) as part:
                for info in part.infolist():
                    if info.is_dir():
                        continue
                    archive.writestr(prefix + subpath + info.filename, part.read(info))
                    count += 1
            head = git("rev-parse", "HEAD", cwd=tree).decode().strip()
            print(f"  + {subpath or './'} at {head}")
    print(f"\nWrote {target} ({target.stat().st_size} bytes, {count} files)")
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("label")
    parser.add_argument("--baseline", type=Path, help="previous release zip to hold unchanged files to")
    parser.add_argument("--changed", action="append", default=[], metavar="ENTRY",
                        help="manifest entry this release intentionally changes; repeat per entry. "
                             "Without it, any content difference from the baseline stops the build.")
    args = parser.parse_args()

    DIST.mkdir(exist_ok=True)
    build_install_archive(args.label, args.baseline, set(args.changed))
    build_source_archive(args.label)


if __name__ == "__main__":
    main()
