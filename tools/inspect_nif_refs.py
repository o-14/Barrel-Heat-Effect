from __future__ import annotations

import argparse
import struct
from pathlib import Path

from inspect_nif_blocks import parse_header


def i32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def f32(data: bytes, offset: int) -> float:
    return struct.unpack_from("<f", data, offset)[0]


def candidate_refs(raw: bytes, block_count: int) -> list[tuple[int, int]]:
    refs: list[tuple[int, int]] = []
    for offset in range(0, max(0, len(raw) - 3)):
        value = i32(raw, offset)
        if -1 <= value < block_count:
            refs.append((offset, value))
    return refs


def controller_summary(data: bytes, blocks: list[dict], block: dict) -> str:
    raw = data[block["offset"] : block["offset"] + block["size"]]
    if len(raw) < 34:
        return ""
    return (
        f" target={i32(raw, 0)} flags=0x{u16(raw, 8):04X}"
        f" freq={f32(raw, 10):.3f} start={f32(raw, 14):.3f} stop={f32(raw, 18):.3f}"
        f" next={i32(raw, 22)} interp={i32(raw, 26)} variable={u32(raw, 30)}"
    )


def trishape_summary(data: bytes, block: dict) -> str:
    raw = data[block["offset"] : block["offset"] + block["size"]]
    if len(raw) < 0x72:
        return ""
    return f" vertices={u16(raw, 0x70)} shaderRef={i32(raw, 0x34)} alphaRef={i32(raw, 0x38)}"


def texture_set_summary(data: bytes, block: dict) -> str:
    raw = data[block["offset"] : block["offset"] + block["size"]]
    text = raw.decode("utf-8", errors="ignore").replace("\x00", "|")
    return f" {text}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("nif", type=Path)
    parser.add_argument("--refs", action="store_true")
    args = parser.parse_args()

    data = args.nif.read_bytes()
    parsed = parse_header(data)
    blocks = parsed["blocks"]

    print(f"NIF: {args.nif}")
    print(f"strings={parsed['strings']}")
    for block in blocks:
        raw = data[block["offset"] : block["offset"] + block["size"]]
        extra = ""
        if block["type"].endswith("FloatController"):
            extra += controller_summary(data, blocks, block)
        if block["type"] == "BSTriShape":
            extra += trishape_summary(data, block)
        if block["type"] == "BSShaderTextureSet":
            extra += texture_set_summary(data, block)
        print(f"{block['index']:02d} {block['type']} size={block['size']}{extra}")
        if args.refs:
            refs = candidate_refs(raw, parsed["num_blocks"])
            if refs:
                print("   refs? " + ", ".join(f"0x{offset:X}->{value}" for offset, value in refs[:40]))


if __name__ == "__main__":
    main()
