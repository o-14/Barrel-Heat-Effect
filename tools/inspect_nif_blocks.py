from __future__ import annotations

import argparse
import struct
from pathlib import Path


def u8(data: bytes, offset: int) -> int:
    return data[offset]


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def f32(data: bytes, offset: int) -> float:
    return struct.unpack_from("<f", data, offset)[0]


def read_short_string(data: bytes, offset: int) -> tuple[str, int]:
    length = u8(data, offset)
    start = offset + 1
    end = start + length
    value = data[start:end].rstrip(b"\x00").decode("utf-8", errors="replace")
    return value, end


def read_sized_string(data: bytes, offset: int) -> tuple[str, int]:
    length = u32(data, offset)
    start = offset + 4
    end = start + length
    value = data[start:end].decode("utf-8", errors="replace")
    return value, end


def parse_header(data: bytes) -> dict:
    header_end = data.index(b"\n") + 1
    pos = header_end
    version = u32(data, pos)
    pos += 4
    endian = u8(data, pos)
    pos += 1
    user_version = u32(data, pos)
    pos += 4
    num_blocks = u32(data, pos)
    pos += 4
    user_version_2 = u32(data, pos)
    pos += 4

    export_author, pos = read_short_string(data, pos)
    export_process, pos = read_short_string(data, pos)
    export_script, pos = read_short_string(data, pos)
    max_filepath, pos = read_short_string(data, pos)

    num_block_types = u16(data, pos)
    pos += 2
    block_types: list[str] = []
    for _ in range(num_block_types):
        block_type, pos = read_sized_string(data, pos)
        block_types.append(block_type)

    block_type_indices = [u16(data, pos + i * 2) for i in range(num_blocks)]
    pos += num_blocks * 2
    block_sizes = [u32(data, pos + i * 4) for i in range(num_blocks)]
    pos += num_blocks * 4

    num_strings = u32(data, pos)
    pos += 4
    max_string_length = u32(data, pos)
    pos += 4
    strings: list[str] = []
    for _ in range(num_strings):
        value, pos = read_sized_string(data, pos)
        strings.append(value)

    num_groups = u32(data, pos)
    pos += 4 + (num_groups * 4)

    blocks = []
    block_pos = pos
    for index, (type_index, size) in enumerate(zip(block_type_indices, block_sizes)):
        blocks.append(
            {
                "index": index,
                "type": block_types[type_index],
                "offset": block_pos,
                "size": size,
            }
        )
        block_pos += size

    return {
        "version": version,
        "endian": endian,
        "user_version": user_version,
        "user_version_2": user_version_2,
        "export_author": export_author,
        "export_process": export_process,
        "export_script": export_script,
        "max_filepath": max_filepath,
        "num_blocks": num_blocks,
        "block_types": block_types,
        "num_strings": num_strings,
        "max_string_length": max_string_length,
        "strings": strings,
        "blocks": blocks,
        "data_end": block_pos,
    }


def describe_float_data(data: bytes, block: dict) -> str:
    start = block["offset"]
    end = start + block["size"]
    raw = data[start:end]
    if len(raw) < 8:
        return ""

    num_keys = u32(raw, 0)
    if num_keys == 0 or num_keys > 32:
        return f" numKeys?={num_keys}"
    interpolation = u32(raw, 4)
    cursor = 8
    keys = []
    stride = 8 if interpolation == 1 else 16 if interpolation == 2 else 20 if interpolation == 3 else 8
    for _ in range(num_keys):
        if cursor + 8 > len(raw):
            break
        time = f32(raw, cursor)
        value = f32(raw, cursor + 4)
        keys.append(f"{time:.3f}->{value:.3f}")
        cursor += stride
    return f" numKeys={num_keys} interpolation={interpolation} keys=[{', '.join(keys)}]"


def describe_float_interpolator(data: bytes, block: dict) -> str:
    raw = data[block["offset"] : block["offset"] + block["size"]]
    if len(raw) < 8:
        return ""
    return f" value={f32(raw, 0):.3f} dataRef={struct.unpack_from('<i', raw, 4)[0]}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("nif", type=Path)
    args = parser.parse_args()

    data = args.nif.read_bytes()
    parsed = parse_header(data)
    print(f"NIF: {args.nif}")
    print(
        f"blocks={parsed['num_blocks']} strings={parsed['num_strings']} "
        f"end=0x{parsed['data_end']:X}/{len(data)}"
    )
    print(f"export={parsed['export_author']!r} {parsed['export_script']!r}")
    for block in parsed["blocks"]:
        extra = ""
        if block["type"] == "NiFloatData":
            extra = describe_float_data(data, block)
        elif block["type"] == "NiFloatInterpolator":
            extra = describe_float_interpolator(data, block)
        print(
            f"{block['index']:02d} 0x{block['offset']:04X} "
            f"size={block['size']:5d} {block['type']}{extra}"
        )


if __name__ == "__main__":
    main()
