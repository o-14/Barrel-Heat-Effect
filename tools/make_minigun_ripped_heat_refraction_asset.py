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


def f32(data: bytes | bytearray, offset: int) -> float:
    return struct.unpack_from("<f", data, offset)[0]


def h3(data: bytes | bytearray, offset: int) -> tuple[float, float, float]:
    return struct.unpack_from("<3e", data, offset)


def write_h3(data: bytearray, offset: int, value: tuple[float, float, float]) -> None:
    struct.pack_into("<3e", data, offset, *value)


def pack_f32(value: float) -> bytes:
    return struct.pack("<f", value)


def pack_i32(value: int) -> bytes:
    return struct.pack("<i", value)


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


def reshape_base_refraction_mesh(block: bytearray) -> None:
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
        ny = ((point[1] - min_y) / span_y)
        nz = ((point[2] - min_z) / span_z) * 2.0 - 1.0

        flare = math.sin(ny * math.pi)
        taper = 1.0 - ny * 0.50
        ripple = math.sin((ny * math.tau * 2.4) + (index * 0.71))
        twist = math.cos((ny * math.tau * 1.7) + (index * 0.37))

        radius_x = 2.2 + flare * 3.2 + taper * 0.95
        radius_z = 1.8 + flare * 3.4 + taper * 0.85
        x = (nx * radius_x) + (ripple * 0.70)
        y = 1.0 + ny * 39.0
        z = (nz * radius_z) + (twist * 0.55) + ny * 3.1

        new_point = (x, y, z)
        write_h3(block, VERTEX_HEADER_OFFSET + index * VERTEX_STRIDE, new_point)
        new_points.append(new_point)

    write_bound(block, new_points)


def patch_float_data_keys(block: bytearray, keys: list[tuple[float, float]]) -> None:
    count = struct.unpack_from("<I", block, 0)[0]
    interpolation = struct.unpack_from("<I", block, 4)[0]
    if count != len(keys):
        raise RuntimeError(f"FloatData key count {count} does not match {len(keys)} replacement keys")
    stride = 8 if interpolation == 1 else 16 if interpolation == 2 else 20 if interpolation == 3 else 8
    cursor = 8
    for time, value in keys:
        struct.pack_into("<f", block, cursor, time)
        struct.pack_into("<f", block, cursor + 4, value)
        cursor += stride


def patch_curve(data: bytearray, block: dict, keys: list[tuple[float, float]]) -> None:
    start = block["offset"]
    end = start + block["size"]
    raw = bytearray(data[start:end])
    patch_float_data_keys(raw, keys)
    data[start:end] = raw


def patch_controller_times(data: bytearray, blocks: list[dict], duration: float) -> None:
    for block in blocks:
        if block["type"] != "BSLightingShaderPropertyFloatController":
            continue
        start = block["offset"]
        data[start + 14 : start + 18] = pack_f32(0.0)
        data[start + 18 : start + 22] = pack_f32(duration)


def patch_controller_interpolator(data: bytearray, blocks: list[dict], controller_index: int, interpolator_index: int) -> None:
    block = blocks[controller_index]
    if block["type"] != "BSLightingShaderPropertyFloatController":
        raise RuntimeError(f"Block {controller_index} is {block['type']}, expected BSLightingShaderPropertyFloatController")
    data[block["offset"] + 26 : block["offset"] + 30] = pack_i32(interpolator_index)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(r"Data\Meshes\GunHeatHaze\MinigunBarrelRefractionOnly.nif"))
    parser.add_argument("--target", type=Path, default=Path(r"Data\Meshes\GunHeatHaze\GunHeatMinigunRippedHeatRefractionLarge.nif"))
    parser.add_argument("--duration", type=float, default=5.4)
    parser.add_argument(
        "--direct-controllers",
        action="store_true",
        help="Experimental: bypass the minigun sequence blend interpolators with direct shader curves.",
    )
    args = parser.parse_args()

    data = bytearray(args.source.read_bytes())
    blocks = parse_header(bytes(data))["blocks"]

    block_24 = blocks[24]
    if block_24["type"] != "BSTriShape":
        raise RuntimeError(f"Expected block 24 to be BSTriShape, found {block_24['type']}")
    raw_shape = bytearray(data[block_24["offset"] : block_24["offset"] + block_24["size"]])
    reshape_base_refraction_mesh(raw_shape)
    data[block_24["offset"] : block_24["offset"] + block_24["size"]] = raw_shape

    # Compatibility mode keeps the minigun branch's original blend-controller
    # wiring. That path is known to render in-game, even though it does not
    # animate as a standalone projectile. Direct controller mode is kept behind
    # a flag because it caused the effect to disappear in testing.
    if args.direct_controllers:
        patch_controller_interpolator(data, blocks, controller_index=9, interpolator_index=13)
        patch_controller_interpolator(data, blocks, controller_index=10, interpolator_index=17)
        patch_curve(data, blocks[8], [(0.0, 0.0), (args.duration, -1.0)])
        patch_curve(data, blocks[14], [(0.0, 0.000), (args.duration, 1.180)])
        patch_curve(data, blocks[18], [(0.0, 0.030), (0.95, 0.115), (args.duration, 0.035)])
        patch_curve(data, blocks[20], [(0.0, 0.000), (args.duration, 0.720)])
    else:
        patch_curve(data, blocks[8], [(0.0, 0.0), (args.duration, -1.0)])
        patch_curve(data, blocks[14], [(0.0, 0.080), (args.duration, 0.080)])
        patch_curve(data, blocks[18], [(0.0, -0.02), (0.65, 0.0), (args.duration, -1.0)])
        patch_curve(data, blocks[20], [(0.0, 0.140), (args.duration, 0.140)])
    patch_controller_times(data, blocks, args.duration)

    args.target.parent.mkdir(parents=True, exist_ok=True)
    if args.target.exists():
        backup = args.target.with_suffix(args.target.suffix + ".pre-minigun-rip")
        shutil.copy2(args.target, backup)
    args.target.write_bytes(data)

    print(f"Wrote {args.target}")
    print(f"Source: {args.source}")
    print("Preserved minigun BaseRefractionMesh material/controller branch")
    print(f"Reshaped block 24 into a narrow muzzle plume, duration={args.duration:.2f}s")


if __name__ == "__main__":
    main()
