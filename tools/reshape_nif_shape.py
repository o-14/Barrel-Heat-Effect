"""Reshape a BSTriShape by transforming its vertex positions in place.

The card inherited from SaugusSmokeMirage is a flat disc of radius ~120 in the XY plane.
Billboarded, that reads on screen as a circle - which is exactly what the playtest
reported. Scaling the local axes turns it into a narrow vertical plume without touching
vertex count, triangle indices, block sizes, or any block reference, so this stays the
same safe in-place surgery used elsewhere in this project.

The bounding sphere is recomputed afterwards, since the stored one describes the old
extents.

FO4 BSTriShape layout, verified against these files:
    +0x48  float center[3], float radius      (bounding sphere)
    +0x6C  uint32 numTriangles
    +0x70  uint16 numVertices
    +0x72  uint32 dataSize                    (vertex bytes + triangle bytes)
    +0x76  vertex data, then triangle data
    stride = (dataSize - numTriangles * 6) / numVertices
    position = first 3 half-floats of each vertex

Usage:
    python tools/reshape_nif_shape.py <nif> --shape Cylinder026 --scale 0.17 0.48 1.0
"""

from __future__ import annotations

import argparse
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from inspect_nif_blocks import parse_header

BOUND_OFFSET = 0x48
NUM_TRIANGLES_OFFSET = 0x6C
NUM_VERTICES_OFFSET = 0x70
DATA_SIZE_OFFSET = 0x72
VERTEX_DATA_OFFSET = 0x76


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("nif", type=Path)
    parser.add_argument("--shape", required=True, help="Substring match on the BSTriShape name")
    parser.add_argument("--scale", type=float, nargs=3, default=[0.17, 0.48, 1.0],
                        metavar=("X", "Y", "Z"))
    parser.add_argument("--offset", type=float, nargs=3, default=[0.0, 0.0, 0.0],
                        metavar=("X", "Y", "Z"))
    parser.add_argument("--backup-suffix", default=".pre-reshape")
    args = parser.parse_args()

    data = bytearray(args.nif.read_bytes())
    parsed = parse_header(bytes(data))
    strings = parsed["strings"]

    reshaped = 0
    for block in parsed["blocks"]:
        if block["type"] != "BSTriShape":
            continue

        base = block["offset"]
        name_index = struct.unpack_from("<i", data, base)[0]
        name = strings[name_index] if 0 <= name_index < len(strings) else ""
        if args.shape not in name:
            continue

        num_triangles = struct.unpack_from("<I", data, base + NUM_TRIANGLES_OFFSET)[0]
        num_vertices = struct.unpack_from("<H", data, base + NUM_VERTICES_OFFSET)[0]
        data_size = struct.unpack_from("<I", data, base + DATA_SIZE_OFFSET)[0]
        stride, remainder = divmod(data_size - (num_triangles * 6), num_vertices)
        if remainder:
            raise SystemExit(f"{name}: unexpected vertex stride")

        start = base + VERTEX_DATA_OFFSET
        points = []
        for index in range(num_vertices):
            offset = start + (index * stride)
            x, y, z = struct.unpack_from("<3e", data, offset)
            x = (x * args.scale[0]) + args.offset[0]
            y = (y * args.scale[1]) + args.offset[1]
            z = (z * args.scale[2]) + args.offset[2]
            struct.pack_into("<3e", data, offset, x, y, z)
            points.append((x, y, z))

        centre = [sum(axis) / len(points) for axis in zip(*points)]
        radius = max(
            ((px - centre[0]) ** 2 + (py - centre[1]) ** 2 + (pz - centre[2]) ** 2) ** 0.5
            for px, py, pz in points)
        old_centre = struct.unpack_from("<3f", data, base + BOUND_OFFSET)
        old_radius = struct.unpack_from("<f", data, base + BOUND_OFFSET + 12)[0]
        struct.pack_into("<4f", data, base + BOUND_OFFSET, *centre, radius)

        extents = [(min(a), max(a)) for a in zip(*points)]
        print(f"reshape {name}: {num_vertices} verts, scale {tuple(args.scale)}, offset {tuple(args.offset)}")
        for axis, (low, high) in zip("XYZ", extents):
            print(f"    {axis} {low:8.2f}..{high:8.2f}   (extent {high - low:7.2f})")
        print(f"    bound centre {tuple(round(v, 2) for v in old_centre)} r={old_radius:.2f}"
              f"  ->  {tuple(round(v, 2) for v in centre)} r={radius:.2f}")
        reshaped += 1

    if not reshaped:
        raise SystemExit("No shape reshaped; check --shape")

    backup = args.nif.with_suffix(args.nif.suffix + args.backup_suffix)
    if not backup.exists():
        shutil.copy2(args.nif, backup)
    args.nif.write_bytes(bytes(data))
    print(f"\nWrote {args.nif} ({reshaped} shape(s), size unchanged: {len(data)} bytes)")


if __name__ == "__main__":
    main()
