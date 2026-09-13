"""Collapse named BSTriShape geometry to a degenerate point so it cannot rasterize.

Why: GunHeatRefractionOnlyStrong.nif is derived from Bethesda's flamethrower spray and
still contains four m_Flames:0 shapes alongside the m_Refraction:0 card we actually
want. A previous pass zeroed only their bounding-sphere radius, which does not stop
them rendering - in-game they still drew the full fireball.

This zeroes each vertex POSITION instead. Every triangle becomes zero-area and is
discarded by the rasterizer, while numVertices / numTriangles / dataSize and the block
size all stay byte-identical, so no block references need renumbering.

FO4 BSTriShape layout, verified against this file:
    +0x6C uint32  numTriangles
    +0x70 uint16  numVertices
    +0x72 uint32  dataSize          (vertex bytes + triangle bytes)
    +0x76         vertex data, then triangle data
    vertex stride = (dataSize - numTriangles * 6) / numVertices
    position = first 3 half-floats of each vertex

Usage:
    python tools/collapse_nif_shape_geometry.py <nif> --shapes m_Flames
"""

from __future__ import annotations

import argparse
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from inspect_nif_blocks import parse_header

NUM_TRIANGLES_OFFSET = 0x6C
NUM_VERTICES_OFFSET = 0x70
DATA_SIZE_OFFSET = 0x72
VERTEX_DATA_OFFSET = 0x76
POSITION_BYTES = 6  # 3 half-floats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("nif", type=Path)
    parser.add_argument(
        "--shapes",
        nargs="+",
        required=True,
        help="Substring match against BSTriShape names, e.g. m_Flames",
    )
    parser.add_argument("--backup-suffix", default=".pre-flame-collapse")
    args = parser.parse_args()

    data = bytearray(args.nif.read_bytes())
    parsed = parse_header(bytes(data))
    strings = parsed["strings"]

    collapsed = 0
    for block in parsed["blocks"]:
        if block["type"] != "BSTriShape":
            continue

        base = block["offset"]
        name_index = struct.unpack_from("<i", data, base)[0]
        name = strings[name_index] if 0 <= name_index < len(strings) else ""
        if not any(pattern in name for pattern in args.shapes):
            print(f"keep     {name}")
            continue

        num_triangles = struct.unpack_from("<I", data, base + NUM_TRIANGLES_OFFSET)[0]
        num_vertices = struct.unpack_from("<H", data, base + NUM_VERTICES_OFFSET)[0]
        data_size = struct.unpack_from("<I", data, base + DATA_SIZE_OFFSET)[0]
        if not num_vertices or not data_size:
            print(f"skip     {name}: no vertex data")
            continue

        vertex_bytes = data_size - (num_triangles * 6)
        stride, remainder = divmod(vertex_bytes, num_vertices)
        if remainder or stride < POSITION_BYTES:
            print(f"skip     {name}: unexpected stride ({vertex_bytes}/{num_vertices})")
            continue

        start = base + VERTEX_DATA_OFFSET
        for index in range(num_vertices):
            offset = start + (index * stride)
            data[offset : offset + POSITION_BYTES] = b"\x00" * POSITION_BYTES

        collapsed += 1
        print(f"collapse {name}: {num_vertices} verts x {stride}B, {num_triangles} tris -> degenerate")

    if not collapsed:
        raise SystemExit("No shape collapsed; check --shapes")

    backup = args.nif.with_suffix(args.nif.suffix + args.backup_suffix)
    if not backup.exists():
        shutil.copy2(args.nif, backup)
    args.nif.write_bytes(bytes(data))
    print(f"\nWrote {args.nif} ({collapsed} shape(s) collapsed, size unchanged: {len(data)} bytes)")


if __name__ == "__main__":
    main()
