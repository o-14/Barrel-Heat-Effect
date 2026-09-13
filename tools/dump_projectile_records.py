from __future__ import annotations

import argparse
import struct
from pathlib import Path


RECORD_HEADER_SIZE = 24
GROUP_HEADER_SIZE = 24

DNAM_FLAGS_OFFSET = 0
DNAM_TYPE_OFFSET = 4
DNAM_SPEED_OFFSET = 8
DNAM_RANGE_OFFSET = 12
DNAM_LIGHT_OFFSET = 16
DNAM_MUZZLE_FLASH_LIGHT_OFFSET = 20
DNAM_MUZZLE_FLASH_DURATION_OFFSET = 40
DNAM_FADE_DURATION_OFFSET = 44
DNAM_LIFETIME_OFFSET = 72


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def f32(data: bytes, offset: int) -> float:
    return struct.unpack_from("<f", data, offset)[0]


def zstr(value: bytes) -> str:
    return value.rstrip(b"\x00").decode("ascii", errors="replace")


def iter_records_and_groups(data: bytes, start: int, end: int):
    pos = start
    while pos + RECORD_HEADER_SIZE <= end:
        sig = data[pos : pos + 4]
        if sig == b"GRUP":
            size = u32(data, pos + 4)
            yield from iter_records_and_groups(data, pos + GROUP_HEADER_SIZE, pos + size)
            pos += size
            continue

        size = u32(data, pos + 4)
        yield data[pos : pos + RECORD_HEADER_SIZE + size]
        pos += RECORD_HEADER_SIZE + size


def iter_subrecords(record: bytes):
    data = record[RECORD_HEADER_SIZE:]
    pos = 0
    while pos + 6 <= len(data):
        sig = data[pos : pos + 4]
        size = u16(data, pos + 4)
        start = pos + 6
        end = start + size
        yield sig, data[start:end]
        pos = end


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("esp", type=Path)
    args = parser.parse_args()

    data = args.esp.read_bytes()
    print(args.esp)
    for record in iter_records_and_groups(data, 0, len(data)):
        if record[:4] != b"PROJ":
            continue

        form_id = u32(record, 12)
        print(f"PROJ {form_id:08X} size={u32(record, 4)}")
        for sig, value in iter_subrecords(record):
            if sig == b"EDID":
                print(f"  EDID: {zstr(value)}")
            elif sig == b"MODL":
                print(f"  MODL: {zstr(value)}")
            elif sig == b"NAM1":
                print(f"  NAM1: {zstr(value)}")
            elif sig == b"DNAM":
                print(
                    "  DNAM: "
                    f"len={len(value)} "
                    f"flags=0x{u32(value, DNAM_FLAGS_OFFSET):08X} "
                    f"type={u16(value, DNAM_TYPE_OFFSET)} "
                    f"speed={f32(value, DNAM_SPEED_OFFSET):.3f} "
                    f"range={f32(value, DNAM_RANGE_OFFSET):.3f} "
                    f"light={u32(value, DNAM_LIGHT_OFFSET):08X} "
                    f"mflashLight={u32(value, DNAM_MUZZLE_FLASH_LIGHT_OFFSET):08X} "
                    f"mflashDur={f32(value, DNAM_MUZZLE_FLASH_DURATION_OFFSET):.3f} "
                    f"fade={f32(value, DNAM_FADE_DURATION_OFFSET):.3f} "
                    f"lifetime={f32(value, DNAM_LIFETIME_OFFSET):.3f}"
                )
        print()


if __name__ == "__main__":
    main()
