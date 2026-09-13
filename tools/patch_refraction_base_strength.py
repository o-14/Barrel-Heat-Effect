"""Set the static base Refraction Strength on BSLightingShaderProperty blocks.

Why: vanilla heat-refraction meshes (minigun BaseRefractionMesh, flamer vaporizer
m_Refraction) keep base refraction at ~0.0-0.125 and animate it up via
BSLightingShaderPropertyFloatController when the weapon's behavior graph plays.
Spawned standalone (projectile MODL or scene-graph attach), those animations never
run, so the mesh renders with the near-zero base value and is invisible. Patching
the base value makes the refraction render unconditionally.

Offsets (FO4 BSLightingShaderProperty, 140-byte block, verified against
MinigunBarrel.nif / SaugusSmokeMirage.nif / FlameThrowerProjectileSprayVaporizer01
derivatives): +0x44 alpha, +0x48 refraction strength.

Usage:
    python tools/patch_refraction_base_strength.py <nif> --strength 0.8
"""

from __future__ import annotations

import argparse
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from inspect_nif_blocks import parse_header

ALPHA_OFFSET = 0x44
REFRACTION_OFFSET = 0x48
LIGHTING_SHADER_BLOCK_SIZE = 140


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("nif", type=Path)
    parser.add_argument("--strength", type=float, default=0.8)
    args = parser.parse_args()

    data = bytearray(args.nif.read_bytes())
    blocks = parse_header(bytes(data))["blocks"]

    patched = 0
    for block in blocks:
        if block["type"] != "BSLightingShaderProperty":
            continue
        if block["size"] != LIGHTING_SHADER_BLOCK_SIZE:
            print(f"skip block {block['index']}: unexpected size {block['size']}")
            continue
        offset = block["offset"]
        alpha = struct.unpack_from("<f", data, offset + ALPHA_OFFSET)[0]
        old = struct.unpack_from("<f", data, offset + REFRACTION_OFFSET)[0]
        if not (0.999 <= alpha <= 1.001):
            print(f"skip block {block['index']}: alpha sanity check failed ({alpha})")
            continue
        struct.pack_into("<f", data, offset + REFRACTION_OFFSET, args.strength)
        patched += 1
        print(f"block {block['index']}: refraction {old} -> {args.strength}")

    if not patched:
        raise SystemExit("No BSLightingShaderProperty block patched")

    backup = args.nif.with_suffix(args.nif.suffix + ".pre-refraction-base")
    if not backup.exists():
        shutil.copy2(args.nif, backup)
    args.nif.write_bytes(bytes(data))
    print(f"Wrote {args.nif} (patched {patched} shader block(s))")


if __name__ == "__main__":
    main()
