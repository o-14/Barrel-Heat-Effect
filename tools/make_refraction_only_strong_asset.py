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

FLAME_SHAPES = (94, 103, 107, 111)
REFRACTION_SHAPE = 98

VANILLA_NORMAL = b"textures\\Effects\\SmokeVapor01Tile_n.dds"
HEAT_NORMAL = b"textures\\Effects\\HeatHazeFlowTile_n.dds"


def make_dds_header(width: int, height: int) -> bytes:
    header = bytearray(128)
    header[0:4] = b"DDS "
    struct.pack_into("<I", header, 4, 124)
    struct.pack_into("<I", header, 8, 0x0002100F)
    struct.pack_into("<I", header, 12, height)
    struct.pack_into("<I", header, 16, width)
    struct.pack_into("<I", header, 20, width * 4)
    struct.pack_into("<I", header, 24, 0)
    struct.pack_into("<I", header, 28, 1)
    struct.pack_into("<I", header, 76, 32)
    struct.pack_into("<I", header, 80, 0x00000041)
    struct.pack_into("<I", header, 84, 0)
    struct.pack_into("<I", header, 88, 32)
    struct.pack_into("<I", header, 92, 0x00FF0000)
    struct.pack_into("<I", header, 96, 0x0000FF00)
    struct.pack_into("<I", header, 100, 0x000000FF)
    struct.pack_into("<I", header, 104, 0xFF000000)
    struct.pack_into("<I", header, 108, 0x00001000)
    return bytes(header)


def clamp_byte(value: float) -> int:
    return max(0, min(255, round(value)))


def fract(value: float) -> float:
    return value - math.floor(value)


def hash2(x: int, y: int) -> float:
    return fract(math.sin(x * 127.1 + y * 311.7) * 43758.5453123)


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    t = max(0.0, min(1.0, (value - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def value_noise(u: float, v: float, cells: int) -> float:
    x = u * cells
    y = v * cells
    x0 = math.floor(x)
    y0 = math.floor(y)
    tx = smoothstep(0.0, 1.0, fract(x))
    ty = smoothstep(0.0, 1.0, fract(y))
    a = hash2(x0, y0)
    b = hash2(x0 + 1, y0)
    c = hash2(x0, y0 + 1)
    d = hash2(x0 + 1, y0 + 1)
    ab = a + (b - a) * tx
    cd = c + (d - c) * tx
    return ab + (cd - ab) * ty


def write_heat_normal(path: Path, width: int = 256, height: int = 256) -> None:
    pixels = bytearray(width * height * 4)
    for y in range(height):
        for x in range(width):
            u = (x + 0.5) / width
            v = (y + 0.5) / height
            column = max(0.0, 1.0 - abs(u - 0.5) * 2.2)
            vertical = smoothstep(0.03, 0.22, v) * (1.0 - smoothstep(0.78, 1.0, v))
            mask = math.pow(column, 1.4) * vertical

            wave_x = math.sin((u * 8.0 + v * 3.5) * math.tau)
            wave_y = math.cos((u * 4.5 - v * 9.0) * math.tau)
            noise_a = value_noise(u + math.sin(v * math.tau) * 0.07, v, 12)
            noise_b = value_noise(u * 2.1, v * 2.4, 26)
            dx = (wave_x * 0.45 + (noise_a - 0.5) * 1.1 + (noise_b - 0.5) * 0.45) * mask
            dy = (wave_y * 0.40 + (noise_b - 0.5) * 1.0) * mask

            r = clamp_byte(128 + dx * 92)
            g = clamp_byte(128 + dy * 92)
            b = 255
            a = clamp_byte(72 + mask * 183)
            offset = (y * width + x) * 4
            pixels[offset : offset + 4] = bytes((b, g, r, a))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(make_dds_header(width, height) + bytes(pixels))


def u16(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def h3(data: bytes | bytearray, offset: int) -> tuple[float, float, float]:
    return struct.unpack_from("<3e", data, offset)


def write_h3(data: bytearray, offset: int, value: tuple[float, float, float]) -> None:
    struct.pack_into("<3e", data, offset, *value)


def read_points(block: bytes | bytearray) -> list[tuple[float, float, float]]:
    count = u16(block, 0x70)
    return [h3(block, VERTEX_HEADER_OFFSET + index * VERTEX_STRIDE) for index in range(count)]


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


def collapse_shape(block: bytearray) -> None:
    count = u16(block, 0x70)
    points = [(0.0, 0.0, 0.0)] * count
    for index, point in enumerate(points):
        write_h3(block, VERTEX_HEADER_OFFSET + index * VERTEX_STRIDE, point)
    write_bound(block, points)


def reshape_refraction_plume(block: bytearray) -> None:
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
        ny = (point[1] - min_y) / span_y
        nz = ((point[2] - min_z) / span_z) * 2.0 - 1.0

        lift = max(0.0, min(1.0, ny))
        flare = math.sin(lift * math.pi)
        taper = 1.0 - lift * 0.55
        swirl = math.sin(lift * math.tau * 2.15 + index * 0.37)
        twist = math.cos(lift * math.tau * 1.65 + index * 0.29)
        radius_x = 2.0 + flare * 3.6 + taper * 1.0
        radius_z = 1.5 + flare * 2.8 + taper * 0.8

        new_point = (
            nx * radius_x + swirl * 0.45,
            1.0 + lift * 30.0,
            nz * radius_z + twist * 0.35,
        )
        write_h3(block, VERTEX_HEADER_OFFSET + index * VERTEX_STRIDE, new_point)
        new_points.append(new_point)

    write_bound(block, new_points)


def edit_shape(data: bytearray, blocks: list[dict], index: int, editor) -> None:
    block = blocks[index]
    if block["type"] != "BSTriShape":
        raise RuntimeError(f"Block {index} is {block['type']}; expected BSTriShape")
    start = block["offset"]
    end = start + block["size"]
    raw = bytearray(data[start:end])
    editor(raw)
    data[start:end] = raw


def replace_all_same_length(data: bytearray, source: bytes, target: bytes) -> int:
    if len(source) != len(target):
        raise RuntimeError(f"Path replacement length mismatch: {len(source)} != {len(target)}")
    count = 0
    index = data.find(source)
    while index != -1:
        data[index : index + len(target)] = target
        count += 1
        index = data.find(source, index + len(target))
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(r"$out\Meshes\Effects\FlameThrowerProjectileSprayVaporizer01.nif"),
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=Path(r"Data\Meshes\GunHeatHaze\GunHeatRefractionOnlyStrong.nif"),
    )
    parser.add_argument(
        "--normal",
        type=Path,
        default=Path(r"Data\Textures\Effects\HeatHazeFlowTile_n.dds"),
    )
    args = parser.parse_args()

    data = bytearray(args.source.read_bytes())
    blocks = parse_header(bytes(data))["blocks"]

    for shape_index in FLAME_SHAPES:
        edit_shape(data, blocks, shape_index, collapse_shape)
    edit_shape(data, blocks, REFRACTION_SHAPE, reshape_refraction_plume)

    normal_replacements = replace_all_same_length(data, VANILLA_NORMAL, HEAT_NORMAL)
    if normal_replacements == 0:
        raise RuntimeError("Could not find vanilla refraction normal texture path")

    write_heat_normal(args.normal)

    args.target.parent.mkdir(parents=True, exist_ok=True)
    if args.target.exists():
        backup = args.target.with_suffix(args.target.suffix + ".pre-refraction-only-strong")
        shutil.copy2(args.target, backup)
    args.target.write_bytes(data)

    print(f"Wrote {args.target}")
    print(f"Wrote {args.normal}")
    print(f"Collapsed visible flame/smoke shapes: {FLAME_SHAPES}")
    print(f"Reshaped refraction shape: {REFRACTION_SHAPE}")
    print(f"Normal map replacements: {normal_replacements}")


if __name__ == "__main__":
    main()
