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

LSCV_REFRACTION_STRENGTH = 0
LSCV_U_OFFSET = 20
LSCV_V_OFFSET = 22


def u16(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def i32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def f32(data: bytes | bytearray, offset: int) -> float:
    return struct.unpack_from("<f", data, offset)[0]


def h3(data: bytes | bytearray, offset: int) -> tuple[float, float, float]:
    return struct.unpack_from("<3e", data, offset)


def pack_f32(value: float) -> bytes:
    return struct.pack("<f", value)


def pack_u32(value: int) -> bytes:
    return struct.pack("<I", value)


def write_h3(data: bytearray, offset: int, value: tuple[float, float, float]) -> None:
    struct.pack_into("<3e", data, offset, *value)


def make_quadratic_float_data(keys: list[tuple[float, float]], block_size: int) -> bytes:
    payload = bytearray()
    payload += pack_u32(len(keys))
    payload += pack_u32(2)
    for time, value in keys:
        payload += pack_f32(time)
        payload += pack_f32(value)
        payload += pack_f32(0.0)
        payload += pack_f32(0.0)
    if len(payload) != block_size:
        raise RuntimeError(f"Float data payload is {len(payload)} bytes; expected {block_size}")
    return bytes(payload)


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


def rewrite_points(block: bytearray, mapper) -> None:
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


def inner_ribbon_mapper(index: int, nx: float, ny: float, nz: float) -> tuple[float, float, float]:
    height01 = (ny + 1.0) * 0.5
    taper = 1.0 - (height01 * 0.55)
    wave = math.sin((height01 * math.tau * 2.2) + (index * 0.17))
    x = (nx * (1.25 + taper * 2.0)) + (wave * 0.55)
    y = 1.0 + (height01 * 25.0)
    z = (nz * (2.0 + taper * 2.5)) + math.cos(height01 * math.tau * 1.7) * 0.6
    return (x, y, z)


def outer_mirage_mapper(index: int, nx: float, ny: float, nz: float) -> tuple[float, float, float]:
    height01 = (nz + 1.0) * 0.5
    flare = math.sin(height01 * math.pi)
    taper = 1.0 - (height01 * 0.40)
    shimmer = math.sin((height01 * math.tau * 2.8) + (ny * 1.4) + (index * 0.09))
    radius_x = 2.75 + (flare * 2.6) + (taper * 1.1)
    radius_z = 2.0 + (flare * 3.0) + (taper * 0.8)
    x = (nx * radius_x) + (shimmer * 0.9)
    y = 0.4 + (height01 * 31.0) + (ny * 1.1)
    z = (ny * radius_z) + (math.cos(height01 * math.tau * 2.1) * 0.75)
    return (x, y, z)


def find_float_controller(data: bytes | bytearray, blocks: list[dict], variable: int, float_size: int) -> tuple[dict, dict]:
    for block in blocks:
        if block["type"] != "BSLightingShaderPropertyFloatController":
            continue
        offset = block["offset"]
        interpolator_ref = i32(data, offset + 26)
        actual_variable = u32(data, offset + 30)
        if actual_variable != variable:
            continue
        interpolator_block = blocks[interpolator_ref]
        if interpolator_block["type"] != "NiFloatInterpolator":
            continue
        data_ref = i32(data, interpolator_block["offset"] + 4)
        data_block = blocks[data_ref]
        if data_block["type"] == "NiFloatData" and data_block["size"] == float_size:
            return block, data_block
    raise RuntimeError(f"Could not find float controller variable={variable} float_size={float_size}")


def patch_controller_curve(
    data: bytearray,
    blocks: list[dict],
    variable: int,
    float_size: int,
    keys: list[tuple[float, float]],
) -> tuple[int, int]:
    controller, float_data = find_float_controller(data, blocks, variable, float_size)
    controller_offset = controller["offset"]
    data[controller_offset + 14 : controller_offset + 18] = pack_f32(keys[0][0])
    data[controller_offset + 18 : controller_offset + 22] = pack_f32(keys[-1][0])
    float_data_offset = float_data["offset"]
    data[float_data_offset : float_data_offset + float_data["size"]] = make_quadratic_float_data(
        keys, float_data["size"]
    )
    return controller["index"], float_data["index"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(r"Data\Meshes\GunHeatHaze\SaugusSmokeMirage_VisiblePulse.nif"))
    parser.add_argument("--target", type=Path, default=Path(r"Data\Meshes\GunHeatHaze\GunHeatAuthoredHeatRefraction.nif"))
    args = parser.parse_args()

    data = bytearray(args.source.read_bytes())
    blocks = parse_header(bytes(data))["blocks"]

    for block_index, mapper in ((3, inner_ribbon_mapper), (15, outer_mirage_mapper)):
        block = blocks[block_index]
        if block["type"] != "BSTriShape":
            raise RuntimeError(f"Block {block_index} is {block['type']}, expected BSTriShape")
        start = block["offset"]
        end = start + block["size"]
        raw = bytearray(data[start:end])
        rewrite_points(raw, mapper)
        data[start:end] = raw

    curves = {
        "refraction": patch_controller_curve(
            data,
            blocks,
            LSCV_REFRACTION_STRENGTH,
            88,
            [
                (0.001, 0.030),
                (0.700, 0.055),
                (1.650, 0.095),
                (3.350, 0.070),
                (5.200, 0.030),
            ],
        ),
        "u_scroll": patch_controller_curve(
            data,
            blocks,
            LSCV_U_OFFSET,
            56,
            [
                (0.000, 0.000),
                (2.600, 0.380),
                (5.200, 0.820),
            ],
        ),
        "v_scroll": patch_controller_curve(
            data,
            blocks,
            LSCV_V_OFFSET,
            40,
            [
                (0.000, 0.000),
                (5.200, 0.420),
            ],
        ),
    }

    data = data.replace(b"SaugusSmokeMirage", b"GunHeatBarrelHaze")

    args.target.parent.mkdir(parents=True, exist_ok=True)
    if args.target.exists():
        backup = args.target.with_suffix(args.target.suffix + ".pre-authored-heat")
        shutil.copy2(args.target, backup)
    args.target.write_bytes(data)

    print(f"Wrote {args.target}")
    print(f"Source: {args.source}")
    print("Edited geometry: block 3 inner ribbon, block 15 outer mirage plume")
    for name, (controller_index, float_data_index) in curves.items():
        print(f"{name}: controller={controller_index} floatData={float_data_index}")


if __name__ == "__main__":
    main()
