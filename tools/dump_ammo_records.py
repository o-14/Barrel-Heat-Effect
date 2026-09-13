"""List AMMO records (FormID + EditorID + name) from a Fallout 4 plugin.

Written to derive the energy-ammo defaults for [Weapons] sEnergyAmmoFormIDs from the
game's own data rather than from memory - a wrong FormID there fails silently, either
letting an energy weapon through or excluding a ballistic one.
"""

from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path

RECORD_HEADER_SIZE = 24
GROUP_HEADER_SIZE = 24
COMPRESSED = 0x00040000


def u16(d: bytes, o: int) -> int:
    return struct.unpack_from("<H", d, o)[0]


def u32(d: bytes, o: int) -> int:
    return struct.unpack_from("<I", d, o)[0]


def zstr(v: bytes) -> str:
    return v.split(b"\x00")[0].decode("utf-8", "replace")


def iter_records(data: bytes, start: int, end: int):
    pos = start
    while pos + RECORD_HEADER_SIZE <= end:
        sig = data[pos : pos + 4]
        size = u32(data, pos + 4)
        if sig == b"GRUP":
            yield from iter_records(data, pos + GROUP_HEADER_SIZE, pos + size)
            pos += size
            continue
        yield data[pos : pos + RECORD_HEADER_SIZE + size]
        pos += RECORD_HEADER_SIZE + size


def iter_subrecords(record: bytes):
    flags = u32(record, 8)
    body = record[RECORD_HEADER_SIZE:]
    if flags & COMPRESSED:
        # Compressed records store the decompressed size in the first four bytes.
        body = zlib.decompress(body[4:])
    pos = 0
    while pos + 6 <= len(body):
        sig = body[pos : pos + 4]
        size = u16(body, pos + 4)
        start = pos + 6
        yield sig, body[start : start + size]
        pos = start + size


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("plugin", type=Path)
    parser.add_argument("--signature", default="AMMO")
    args = parser.parse_args()

    data = args.plugin.read_bytes()
    want = args.signature.encode()
    for record in iter_records(data, 0, len(data)):
        if record[:4] != want:
            continue
        edid = full = ""
        try:
            for sig, value in iter_subrecords(record):
                if sig == b"EDID":
                    edid = zstr(value)
                elif sig == b"FULL":
                    full = zstr(value)
        except Exception as exc:  # noqa: BLE001 - a bad record should not stop the scan
            edid = edid or f"<unreadable: {exc}>"
        print(f"{u32(record, 12):08X}  {edid:<40} {full}")


if __name__ == "__main__":
    main()
