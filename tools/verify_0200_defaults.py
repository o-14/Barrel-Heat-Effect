"""Assert every MCM control's default agrees in all five places a default is written.

verify_0174_mcm.py already holds config.json's slider defaults against both inis. This adds
the two that were never machine-checked:

- the "Default: x" the help text PROMISES the player, which is hand-written prose and so the
  one most likely to drift from the value beside it;
- the member initialiser in Config.h, which the DLL falls back on when a key is absent from
  BarrelHeatEffect.ini - a missing key then silently yields a different default from the panel's.

It reads the shipped archive rather than the working tree, so it checks what players install.

Usage:
    python -B tools/verify_0200_defaults.py [release zip]
"""

import argparse
import configparser
import json
import re
import sys
import zipfile
from pathlib import Path
from local_paths import required_path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = Path(required_path('BHE_PROJECT_ROOT'))


def newest_release() -> Path:
    """Default to the most recent release. The pre-rename GunHeatHaze-*.zip are not candidates:
    their paths are the old ones, and 0.20.0 is a deliberate failing fixture."""
    candidates = [p for p in (PROJECT / "dist").glob("BarrelHeatEffect-*.zip")
                  if "-source" not in p.name]
    if not candidates:
        raise SystemExit("no release archive found in dist/; pass one as an argument")
    return max(candidates, key=lambda p: p.stat().st_mtime)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("archive", nargs="?", type=Path)
parser.add_argument("--papyrus-source", type=Path,
                    help="Corresponding GunHeatController.psc when omitted from the install archive")
args = parser.parse_args()
ARCHIVE = args.archive if args.archive is not None else newest_release()


def ini(text: str) -> dict[tuple[str, str], str]:
    parser = configparser.ConfigParser(strict=False, inline_comment_prefixes=(";",))
    parser.optionxform = str
    parser.read_string(text)
    return {(s, k): v.strip() for s in parser.sections() for k, v in parser.items(s)}


def number(value) -> float | None:
    """Every default as a float, so 0.30 == 0.3, and on/true/1 are one value."""
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "on"):
            return 1.0
        if lowered in ("false", "off"):
            return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# Config.h: refractionMaxStrength_{ 0.04F } -> the DLL's fallback when the ini key is absent.
MEMBERS = dict(re.findall(r"(\w+)_\{\s*([^}]+?)\s*\}", (ROOT / "GunHeatPlugin/src/Config.h").read_text()))
# The one member whose name does not follow from the ini key, which is [CaliberScaling] bEnabled.
MEMBER_ALIASES = {"enabled": "caliberScalingEnabled"}


def compiled_default(key: str) -> str | None:
    name = key[1:] if key[0] in "fbisu" else key
    name = name[0].lower() + name[1:]
    return MEMBERS.get(MEMBER_ALIASES.get(name, name))


with zipfile.ZipFile(ARCHIVE) as archive:
    read = lambda name: archive.read(name).decode("utf-8-sig")
    panel = json.loads(read("MCM/Config/BarrelHeatEffect/config.json"))
    plugin_ini = ini(read("F4SE/Plugins/BarrelHeatEffect.ini"))
    mcm_defaults = ini(read("MCM/Config/BarrelHeatEffect/settings.ini"))
    papyrus_entry = "Scripts/Source/User/GunHeat/GunHeatController.psc"
    if papyrus_entry in archive.namelist():
        controller = read(papyrus_entry)
    elif args.papyrus_source:
        controller = args.papyrus_source.read_text(encoding="utf-8-sig")
    else:
        parser.error("Archive omits source scripts; pass --papyrus-source with its corresponding source.")

# fHeatPerShot has a sixth home: the Papyrus fallback for a native that answers 0 or less. It held
# the pre-0.17.3 value of 0.15 until 0.20.1, which is why it is asserted here.
PAPYRUS_FALLBACKS = {"fHeatPerShot": re.search(r"^Float heatPerShot = ([\d.]+)", controller, re.M)}

rows = []
for page in panel["pages"]:
    for control in page["content"]:
        if "id" not in control:
            continue
        key, section = control["id"].split(":")
        promised = re.search(r"Default:\s*([\w.]+)", control.get("help", ""))
        sources = {
            "config.json": control["valueOptions"]["default"],
            "help text": promised.group(1) if promised else None,
            "BarrelHeatEffect.ini": plugin_ini.get((section, key)),
            "settings.ini": mcm_defaults.get((section, key)),
            "Config.h": (compiled_default(key) or "").rstrip("F") or None,
        }
        fallback = PAPYRUS_FALLBACKS.get(key)
        if fallback is not None:
            assert fallback, f"{key}: the Papyrus fallback could not be found in GunHeatController.psc"
            sources["GunHeatController.psc"] = fallback.group(1)
        values = {name: number(v) for name, v in sources.items()}
        assert None not in values.values(), f"{control['id']}: no default in {[n for n, v in values.items() if v is None]}"
        spread = max(values.values()) - min(values.values())
        assert spread < 1e-6, f"{control['id']} disagrees: {sources}"
        rows.append(dict(page=page["pageDisplayName"], label=control["text"], setting=control["id"],
                         default=sources["config.json"], sources_checked=len(sources)))

report = dict(archive=ARCHIVE.name, controls=len(rows),
              sources=["config.json default", "config.json help text", "Data/F4SE/Plugins/BarrelHeatEffect.ini",
                       "Data/MCM/Config/BarrelHeatEffect/settings.ini", "GunHeatPlugin/src/Config.h initialiser",
                       "GunHeatController.psc fallback (fHeatPerShot only)"],
              controls_checked=rows,
              result=f"All {len(rows)} controls state the same default everywhere it is written.")
version = re.search(r"\d+\.\d+\.\d+", ARCHIVE.name)
out = ROOT / f"docs/release-{version.group(0) if version else 'unversioned'}"
out.mkdir(parents=True, exist_ok=True)
(out / "defaults-validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(report["result"])
for row in rows:
    print(f"  {row['page']:8}  {row['label']:28}  {row['setting']:32}  {row['default']}")
