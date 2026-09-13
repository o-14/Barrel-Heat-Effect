"""Explicit machine-local inputs for developer tools."""
import os
from pathlib import Path

def required_path(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Set {name} to the required local path before running this tool.")
    return Path(value).expanduser()
