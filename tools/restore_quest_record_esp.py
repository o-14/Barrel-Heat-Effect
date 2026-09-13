"""Merge the controller QUST record back into the PROJ-only GunHeatHaze.esp.

The quest record (GunHeatControllerQuest, local form 0x000800, VMAD attaching
GunHeat:GunHeatController, Start Game Enabled) is taken verbatim from the
known-working quest-only esp backup. The PROJ group of the current esp is kept
byte-for-byte. The TES4 HEDR record count and next-object-id are patched.

Usage:
    python tools/restore_quest_record_esp.py \
        --esp "Data/GunHeatHaze.esp" \
        --quest-source "Data/GunHeatHaze.esp.method1-backup-20260622-011046"
"""

from __future__ import annotations

import argparse
import shutil
import struct
from datetime import datetime
from pathlib import Path

RECORD_HEADER_SIZE = 24
GROUP_HEADER_SIZE = 24


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def read_tes4(data: bytes) -> bytes:
    if data[:4] != b"TES4":
        raise RuntimeError("File does not start with TES4")
    size = u32(data, 4)
    return data[: RECORD_HEADER_SIZE + size]


def top_groups(data: bytes) -> list[tuple[bytes, bytes]]:
    """Return [(label, group_bytes)] for each top-level GRUP."""
    tes4 = read_tes4(data)
    pos = len(tes4)
    groups: list[tuple[bytes, bytes]] = []
    while pos + GROUP_HEADER_SIZE <= len(data):
        if data[pos : pos + 4] != b"GRUP":
            raise RuntimeError(f"Expected GRUP at offset {pos}")
        size = u32(data, pos + 4)
        label = data[pos + 8 : pos + 12]
        groups.append((label, data[pos : pos + size]))
        pos += size
    return groups


def count_records(group: bytes) -> int:
    count = 0
    pos = GROUP_HEADER_SIZE
    while pos + RECORD_HEADER_SIZE <= len(group):
        sig = group[pos : pos + 4]
        if sig == b"GRUP":
            pos += u32(group, pos + 4)
            continue
        count += 1
        pos += RECORD_HEADER_SIZE + u32(group, pos + 4)
    return count


def max_local_form_id(group: bytes) -> int:
    result = 0
    pos = GROUP_HEADER_SIZE
    while pos + RECORD_HEADER_SIZE <= len(group):
        sig = group[pos : pos + 4]
        if sig == b"GRUP":
            pos += u32(group, pos + 4)
            continue
        result = max(result, u32(group, pos + 12) & 0x00FFFFFF)
        pos += RECORD_HEADER_SIZE + u32(group, pos + 4)
    return result


def patch_hedr(tes4: bytes, record_count: int, next_object_id: int) -> bytes:
    out = bytearray(tes4)
    pos = RECORD_HEADER_SIZE
    while pos + 6 <= len(out):
        sig = bytes(out[pos : pos + 4])
        size = u16(out, pos + 4)
        if sig == b"HEDR":
            struct.pack_into("<I", out, pos + 6 + 4, record_count)
            struct.pack_into("<I", out, pos + 6 + 8, next_object_id)
            return bytes(out)
        pos += 6 + size
    raise RuntimeError("TES4 did not contain HEDR")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--esp", required=True, type=Path)
    parser.add_argument("--quest-source", required=True, type=Path)
    args = parser.parse_args()

    esp_data = args.esp.read_bytes()
    quest_data = args.quest_source.read_bytes()

    esp_groups = dict(top_groups(esp_data))
    quest_groups = dict(top_groups(quest_data))

    if b"QUST" not in quest_groups:
        raise RuntimeError(f"{args.quest_source} has no QUST group")
    if b"QUST" in esp_groups:
        print("ESP already contains a QUST group; nothing to do.")
        return
    if b"PROJ" not in esp_groups:
        raise RuntimeError(f"{args.esp} has no PROJ group to preserve")

    merged_groups = [quest_groups[b"QUST"], esp_groups[b"PROJ"]]
    record_count = sum(count_records(group) for group in merged_groups)
    next_object_id = max(max_local_form_id(group) for group in merged_groups) + 1

    tes4 = patch_hedr(read_tes4(esp_data), record_count, next_object_id)
    merged = tes4 + b"".join(merged_groups)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = args.esp.with_suffix(args.esp.suffix + f".pre-quest-restore-{timestamp}")
    shutil.copy2(args.esp, backup)
    args.esp.write_bytes(merged)

    print(f"Wrote {args.esp} ({len(merged)} bytes)")
    print(f"Backup: {backup}")
    print(f"Records: {record_count}, next object id: {next_object_id:06X}")


if __name__ == "__main__":
    main()
