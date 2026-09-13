"""Add the heat-card ART Object (ARTO) record to GunHeatHaze.esp.

Route A needs a BGSArtObject to hand to TESObjectREFR::ApplyArtObject. One ARTO record
covers every weapon - the art is attached to whatever node we pass, so no per-weapon
patching is involved.

Layout copied from vanilla ARTO records in Fallout4.esm (e.g. 0024A3E2), minus the
optional PTRN/KSIZ/KWDA preset and keyword fields:

    EDID  zstring   editor id
    OBND  12 bytes  int16 min[3], int16 max[3]
    MODL  zstring   model path
    MODT  20 bytes  04000000 then zeroes
    DNAM  4 bytes   flags

Also bumps TES4/HEDR numRecords and nextObjectID.

Usage:
    python tools/add_arto_record.py Data/GunHeatHaze.esp
"""

from __future__ import annotations

import argparse
import shutil
import struct
from datetime import datetime
from pathlib import Path

EDITOR_ID = b"GunHeatBarrelHazeArt\x00"
MODEL_PATH = b"GunHeatHaze\\GunHeatBarrelRefractionCard.nif\x00"
OBND = struct.pack("<6h", -16, -16, -16, 16, 16, 16)
MODT = struct.pack("<I", 4) + (b"\x00" * 16)
DNAM = struct.pack("<I", 0)
RECORD_TAIL = bytes.fromhex("0000000083000000")
GROUP_TAIL = bytes.fromhex("0000000000000000")


def subrecord(signature: bytes, payload: bytes) -> bytes:
    return signature + struct.pack("<H", len(payload)) + payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("esp", type=Path)
    parser.add_argument("--form-id", type=lambda v: int(v, 16), default=0x01000802)
    args = parser.parse_args()

    data = bytearray(args.esp.read_bytes())
    if b"ARTO" in data:
        raise SystemExit("ESP already contains an ARTO group; refusing to add a second")

    body = b"".join([
        subrecord(b"EDID", EDITOR_ID),
        subrecord(b"OBND", OBND),
        subrecord(b"MODL", MODEL_PATH),
        subrecord(b"MODT", MODT),
        subrecord(b"DNAM", DNAM),
    ])

    record = (b"ARTO" + struct.pack("<III", len(body), 0, args.form_id)
              + RECORD_TAIL + body)
    group = (b"GRUP" + struct.pack("<I", 24 + len(record)) + b"ARTO"
             + struct.pack("<I", 0) + GROUP_TAIL + record)

    # TES4 header: bump record count and next free object id.
    tes4_size = struct.unpack_from("<I", data, 4)[0]
    cursor = 24
    end = 24 + tes4_size
    patched_header = False
    while cursor + 6 <= end:
        signature = bytes(data[cursor:cursor + 4])
        size = struct.unpack_from("<H", data, cursor + 4)[0]
        if signature == b"HEDR":
            payload = cursor + 6
            count = struct.unpack_from("<i", data, payload + 4)[0]
            next_id = struct.unpack_from("<I", data, payload + 8)[0]
            struct.pack_into("<i", data, payload + 4, count + 1)
            struct.pack_into("<I", data, payload + 8, max(next_id, (args.form_id & 0xFFFFFF) + 1))
            print(f"HEDR numRecords {count} -> {count + 1}, "
                  f"nextObjectID 0x{next_id:X} -> 0x{max(next_id, (args.form_id & 0xFFFFFF) + 1):X}")
            patched_header = True
            break
        cursor += 6 + size
    if not patched_header:
        raise SystemExit("HEDR not found in TES4 header")

    backup = args.esp.with_suffix(args.esp.suffix + f".pre-arto-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(args.esp, backup)

    args.esp.write_bytes(bytes(data) + group)
    print(f"ARTO {args.form_id:08X} '{EDITOR_ID[:-1].decode()}' -> {MODEL_PATH[:-1].decode()}")
    print(f"appended {len(group)} bytes; {args.esp} is now {args.esp.stat().st_size} bytes")
    print(f"backup: {backup.name}")


if __name__ == "__main__":
    main()
