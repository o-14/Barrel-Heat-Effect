from __future__ import annotations

import argparse
import shutil
import struct
from pathlib import Path

from inspect_nif_blocks import parse_header


LSCV_ALPHA = 12
CLAMP_ACTIVE_FLAGS = 0x004C


def i32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def f32(data: bytes, offset: int) -> float:
    return struct.unpack_from("<f", data, offset)[0]


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
    parser.add_argument("--target", type=Path, default=Path(r"Data\Meshes\GunHeatHaze\SaugusSmokeMirage_NIFFade.nif"))
    parser.add_argument("--fade-in", type=float, default=0.8)
    parser.add_argument("--hold", type=float, default=3.2)
    parser.add_argument("--fade-out-end", type=float, default=4.8)
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
        if variable != 20:
            continue
        interpolator_block = blocks[interpolator_ref]
        if interpolator_block["type"] != "NiFloatInterpolator":
            continue
        data_ref = i32(data, interpolator_block["offset"] + 4)
        data_block = blocks[data_ref]
        if data_block["type"] != "NiFloatData" or data_block["size"] != 56:
            continue
        if u32(data, data_block["offset"]) == 3 and f32(data, data_block["offset"] + 12) == 0.0:
            candidate = (block, interpolator_block, data_block)
            break

    if candidate is None:
        raise RuntimeError("Could not find the zeroed U Offset float controller to repurpose as alpha")

    controller, _interpolator, float_data = candidate
    controller_offset = controller["offset"]
    float_data_offset = float_data["offset"]

    data[controller_offset + 4 : controller_offset + 6] = pack_u16(CLAMP_ACTIVE_FLAGS)
    data[controller_offset + 14 : controller_offset + 18] = pack_f32(0.0)
    data[controller_offset + 18 : controller_offset + 22] = pack_f32(args.fade_out_end)
    data[controller_offset + 30 : controller_offset + 34] = pack_u32(LSCV_ALPHA)

    keys = [
        (0.0, 0.0),
        (args.fade_in * 0.45, 0.25),
        (args.fade_in, 1.0),
        (args.hold, 1.0),
        (args.hold + (args.fade_out_end - args.hold) * 0.55, 0.35),
        (args.fade_out_end, 0.0),
    ]
    data[float_data_offset : float_data_offset + float_data["size"]] = make_linear_float_data(keys, float_data["size"])

    args.target.parent.mkdir(parents=True, exist_ok=True)
    if args.target.exists():
        backup = args.target.with_suffix(args.target.suffix + ".pre-nif-fade")
        shutil.copy2(args.target, backup)
    args.target.write_bytes(data)

    print(f"Wrote {args.target}")
    print(f"Source: {args.source}")
    print(f"Controller block: {controller['index']}")
    print(f"FloatData block: {float_data['index']}")
    print(f"Alpha keys: {keys}")


if __name__ == "__main__":
    main()
