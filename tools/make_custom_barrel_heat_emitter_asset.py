from __future__ import annotations

import argparse
import math
import shutil
import struct
from pathlib import Path

from inspect_nif_blocks import parse_header


VERTEX_HEADER_OFFSET = 0x76
VERTEX_STRIDE = 24
BOUND_OFFSET = 0x48


def u16(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def h3(data: bytes | bytearray, offset: int) -> tuple[float, float, float]:
    return struct.unpack_from("<3e", data, offset)


def write_h3(data: bytearray, offset: int, value: tuple[float, float, float]) -> None:
    struct.pack_into("<3e", data, offset, *value)


def write_bound(block: bytearray, points: list[tuple[float, float, float]]) -> None:
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    min_z = min(point[2] for point in points)
    max_z = max(point[2] for point in points)
    center = ((min_x + max_x) * 0.5, (min_y + max_y) * 0.5, (min_z + max_z) * 0.5)
    radius = max(
        math.sqrt(
            ((point[0] - center[0]) ** 2)
            + ((point[1] - center[1]) ** 2)
            + ((point[2] - center[2]) ** 2)
        )
        for point in points
    )
    struct.pack_into("<4f", block, BOUND_OFFSET, center[0], center[1], center[2], radius)


def read_points(block: bytes | bytearray) -> list[tuple[float, float, float]]:
    num_vertices = u16(block, 0x70)
    return [h3(block, VERTEX_HEADER_OFFSET + index * VERTEX_STRIDE) for index in range(num_vertices)]


def rewrite_points(
    block: bytearray,
    mapper,
) -> None:
    points = read_points(block)
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    min_z = min(point[2] for point in points)
    max_z = max(point[2] for point in points)
    span_x = max(max_x - min_x, 0.001)
    span_y = max(max_y - min_y, 0.001)
    span_z = max(max_z - min_z, 0.001)

    new_points: list[tuple[float, float, float]] = []
    for index, point in enumerate(points):
        nx = ((point[0] - min_x) / span_x) * 2.0 - 1.0
        ny = ((point[1] - min_y) / span_y) * 2.0 - 1.0
        nz = ((point[2] - min_z) / span_z) * 2.0 - 1.0
        new_point = mapper(index, nx, ny, nz)
        write_h3(block, VERTEX_HEADER_OFFSET + index * VERTEX_STRIDE, new_point)
        new_points.append(new_point)

    write_bound(block, new_points)


def soft_sheet_mapper(_index: int, nx: float, ny: float, _nz: float) -> tuple[float, float, float]:
    height01 = (ny + 1.0) * 0.5
    pinch = 1.0 - (height01 * 0.35)
    x = nx * (8.0 * pinch)
    y = 2.0 + (height01 * 24.0)
    z = (ny * 8.0) + (math.sin(nx * math.pi) * 1.25)
    return (x, y, z)


def column_mapper(_index: int, nx: float, ny: float, nz: float) -> tuple[float, float, float]:
    height01 = (nz + 1.0) * 0.5
    swirl = math.sin((height01 * math.tau * 1.35) + (ny * 0.8))
    radius = 4.5 + (height01 * 3.5)
    x = (nx * radius) + (swirl * 1.2)
    y = 1.0 + (height01 * 30.0) + (ny * 2.0)
    z = (ny * 5.0) + (height01 * 6.0)
    return (x, y, z)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(r"Data\Meshes\GunHeatHaze\SaugusSmokeMirage_VisiblePulse.nif"))
    parser.add_argument("--target", type=Path, default=Path(r"Data\Meshes\GunHeatHaze\GunHeatBarrelHeatEmitter.nif"))
    args = parser.parse_args()

    data = bytearray(args.source.read_bytes())
    blocks = parse_header(bytes(data))["blocks"]

    edits = {
        3: soft_sheet_mapper,
        15: column_mapper,
    }
    for block_index, mapper in edits.items():
        block = blocks[block_index]
        if block["type"] != "BSTriShape":
            raise RuntimeError(f"Block {block_index} is {block['type']}, expected BSTriShape")
        start = block["offset"]
        end = start + block["size"]
        raw = bytearray(data[start:end])
        rewrite_points(raw, mapper)
        data[start:end] = raw

    data = data.replace(b"SaugusSmokeMirage", b"GunHeatBarrelHaze")

    args.target.parent.mkdir(parents=True, exist_ok=True)
    if args.target.exists():
        shutil.copy2(args.target, args.target.with_suffix(args.target.suffix + ".pre-custom-barrel-emitter"))
    args.target.write_bytes(data)

    print(f"Wrote {args.target}")
    print(f"Source: {args.source}")
    print("Edited BSTriShape blocks: 3 soft sheet, 15 barrel column")


if __name__ == "__main__":
    main()
