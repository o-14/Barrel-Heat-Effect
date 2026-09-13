from __future__ import annotations

import argparse
import shutil
import struct
from datetime import datetime
from pathlib import Path


RECORD_HEADER_SIZE = 24
GROUP_HEADER_SIZE = 24
ASSAULT_RIFLE_PROJECTILE_FORM_ID = 0x0000481F
PROJECTILE_MUZZLE_FLASH_FLAG = 0x00000008


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def iter_records_and_groups(data: bytes, start: int, end: int):
    pos = start
    while pos + RECORD_HEADER_SIZE <= end:
        sig = data[pos : pos + 4]
        if sig == b"GRUP":
            size = u32(data, pos + 4)
            yield pos, pos + size, sig
            yield from iter_records_and_groups(data, pos + GROUP_HEADER_SIZE, pos + size)
            pos += size
            continue

        size = u32(data, pos + 4)
        yield pos, pos + RECORD_HEADER_SIZE + size, sig
        pos += RECORD_HEADER_SIZE + size


def find_record(data: bytes, signature: bytes, form_id: int) -> tuple[int, int]:
    for start, end, sig in iter_records_and_groups(data, 0, len(data)):
        if sig == signature and u32(data, start + 12) == form_id:
            return start, end
    raise RuntimeError(f"Could not find {signature.decode()}:{form_id:08X}")


def patch_flag(esp: Path, enable: bool) -> None:
    data = bytearray(esp.read_bytes())
    start, end = find_record(data, b"PROJ", ASSAULT_RIFLE_PROJECTILE_FORM_ID)
    pos = start + RECORD_HEADER_SIZE

    while pos + 6 <= end:
        sig = bytes(data[pos : pos + 4])
        size = u16(data, pos + 4)
        value_start = pos + 6
        if sig == b"DNAM":
            flags = u32(data, value_start)
            next_flags = flags | PROJECTILE_MUZZLE_FLASH_FLAG if enable else flags & ~PROJECTILE_MUZZLE_FLASH_FLAG
            struct.pack_into("<I", data, value_start, next_flags)

            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = esp.with_suffix(esp.suffix + f".muzzle-flag-backup-{timestamp}")
            shutil.copy2(esp, backup)
            esp.write_bytes(data)
            print(f"Wrote {esp}")
            print(f"Backup: {backup}")
            print(f"Old flags: 0x{flags:08X}")
            print(f"New flags: 0x{next_flags:08X}")
            print(f"Muzzle Flash flag enabled: {bool(next_flags & PROJECTILE_MUZZLE_FLASH_FLAG)}")
            return
        pos = value_start + size

    raise RuntimeError("Projectile DNAM was not found")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--esp", required=True, type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--enable", action="store_true")
    group.add_argument("--disable", action="store_true")
    args = parser.parse_args()

    patch_flag(args.esp, enable=args.enable)


if __name__ == "__main__":
    main()
