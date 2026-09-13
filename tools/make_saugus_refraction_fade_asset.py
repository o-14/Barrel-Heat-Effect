from __future__ import annotations

import argparse
import shutil
import struct
from pathlib import Path

from inspect_nif_blocks import parse_header


LSCV_REFRACTION_STRENGTH = 0
CLAMP_ACTIVE_FLAGS = 0x004C


def i32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def pack_u16(value: int) -> bytes:
    return struct.pack("<H", value)


def pack_u32(value: int) -> bytes:
    return struct.pack("<I", value)


def pack_f32(value: float) -> bytes:
    return struct.pack("<f", value)


def make_linear_float_data(keys: list[tuple[float, float]], block_size: int) -> bytes:
    payload = bytearray()
    payload += pack_u32(len(keys))
    payload += pack_u32(1)
    for time, value in keys:
        payload += pack_f32(time)
        payload += pack_f32(value)
    if len(payload) != block_size:
        raise RuntimeError(f"Float data payload is {len(payload)} bytes; expected {block_size}")
    return bytes(payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(r"Data\Meshes\GunHeatHaze\SaugusSmokeMirage_Tall.nif"))
    parser.add_argument("--target", type=Path, default=Path(r"Data\Meshes\GunHeatHaze\SaugusSmokeMirage_RefractionFade.nif"))
    args = parser.parse_args()

    data = bytearray(args.source.read_bytes())
    parsed = parse_header(bytes(data))
    blocks = parsed["blocks"]

    candidate = None
    for block in blocks:
        if block["type"] != "BSLightingShaderPropertyFloatController":
            continue
        offset = block["offset"]
        interpolator_ref = i32(data, offset + 26)
        variable = u32(data, offset + 30)
        if variable != LSCV_REFRACTION_STRENGTH:
            continue
        interpolator_block = blocks[interpolator_ref]
        if interpolator_block["type"] != "NiFloatInterpolator":
            continue
        data_ref = i32(data, interpolator_block["offset"] + 4)
        data_block = blocks[data_ref]
        if data_block["type"] == "NiFloatData" and data_block["size"] == 88:
            candidate = (block, interpolator_block, data_block)
            break

    if candidate is None:
        raise RuntimeError("Could not find the refraction strength float controller")

    controller, _interpolator, float_data = candidate
    controller_offset = controller["offset"]
    float_data_offset = float_data["offset"]

    data[controller_offset + 4 : controller_offset + 6] = pack_u16(CLAMP_ACTIVE_FLAGS)
    data[controller_offset + 14 : controller_offset + 18] = pack_f32(0.0)
    data[controller_offset + 18 : controller_offset + 22] = pack_f32(4.8)
    data[controller_offset + 30 : controller_offset + 34] = pack_u32(LSCV_REFRACTION_STRENGTH)

    keys = [
        (0.0, 0.0),
        (0.15, 0.010),
        (0.36, 0.025),
        (0.80, 0.060),
        (1.40, 0.075),
        (3.20, 0.075),
        (3.70, 0.055),
        (4.10, 0.035),
        (4.50, 0.015),
        (4.80, 0.0),
    ]
    data[float_data_offset : float_data_offset + float_data["size"]] = make_linear_float_data(keys, float_data["size"])

    args.target.parent.mkdir(parents=True, exist_ok=True)
    if args.target.exists():
        backup = args.target.with_suffix(args.target.suffix + ".pre-refraction-fade")
        shutil.copy2(args.target, backup)
    args.target.write_bytes(data)

    print(f"Wrote {args.target}")
    print(f"Source: {args.source}")
    print(f"Controller block: {controller['index']}")
    print(f"FloatData block: {float_data['index']}")
    print(f"Refraction keys: {keys}")


if __name__ == "__main__":
    main()
