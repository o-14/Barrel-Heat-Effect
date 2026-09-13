r"""Remove one top-level record, and its group, from a small esp - then prove the result.

Written to drop the unused PROJ GunHeatHeatPuffProjectile left over from the abandoned
projectile experiment. It is deliberately narrow: this plugin holds one record per top-level
group, so removing a record means removing its whole GRUP, and nothing here handles a group
with siblings, nested groups, compressed records, or ONAM in the header.

It refuses to run unless the record is genuinely unreferenced: the FormID must appear exactly
once in the file, in the record's own header. Removing a referenced record would leave a
dangling pointer that the game resolves to whatever else holds that ID.

FormIDs of the surviving records do not move - they are stored, not positional - so a save that
already knows GunHeatControllerQuest (01000800) or the art object (01000802) is unaffected.
HEDR's record count is decremented; nextObjectID is left alone, so the removed ID is not reused.

Usage:
    python -B tools/strip_esp_record.py Data/GunHeatHaze.esp PROJ --expect-formid 01000801
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path


def walk(data: bytes):
    """Yield (kind, signature, offset, total_length) for every top-level group and record."""
    pos = 0
    while pos < len(data):
        sig = data[pos:pos + 4].decode("latin1")
        size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        if sig == "GRUP":
            yield "GRUP", data[pos + 8:pos + 12].decode("latin1"), pos, size
            pos += 24  # descend: a group's size covers its records, which follow it
        else:
            yield "record", sig, pos, 24 + size
            pos += 24 + size


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("esp", type=Path)
    parser.add_argument("signature", help="top-level record type to remove, e.g. PROJ")
    parser.add_argument("--expect-formid", required=True, help="the record's FormID, as 8 hex digits")
    parser.add_argument("--out", type=Path, help="defaults to editing the file in place")
    args = parser.parse_args()

    data = args.esp.read_bytes()
    formid = int(args.expect_formid, 16)

    entries = list(walk(data))
    groups = [e for e in entries if e[0] == "GRUP" and e[1] == args.signature]
    records = [e for e in entries if e[0] == "record" and e[1] == args.signature]
    if len(groups) != 1 or len(records) != 1:
        raise SystemExit(f"expected exactly one {args.signature} group and record, "
                         f"found {len(groups)} and {len(records)}")
    group_kind, _, group_at, group_size = groups[0]
    _, _, record_at, record_size = records[0]

    actual = struct.unpack("<I", data[record_at + 12:record_at + 16])[0]
    if actual != formid:
        raise SystemExit(f"{args.signature} is {actual:08X}, not the expected {formid:08X}")

    # The group must contain exactly this record and nothing else.
    if group_at + group_size != record_at + record_size or group_at + 24 != record_at:
        raise SystemExit(f"{args.signature} group holds more than the one record; not handled")

    # Unreferenced check: the only occurrence may be the record's own header field.
    needle = struct.pack("<I", formid)
    hits = [i for i in range(len(data) - 3) if data[i:i + 4] == needle]
    if hits != [record_at + 12]:
        raise SystemExit(f"{formid:08X} is referenced at {hits}; refusing to remove a referenced record")

    stripped = data[:group_at] + data[group_at + group_size:]

    # TES4 always comes first; fix its record count.
    head_size = struct.unpack("<I", stripped[4:8])[0]
    body, p = stripped[24:24 + head_size], 0
    while p + 6 <= len(body):
        sub = body[p:p + 4].decode("latin1")
        size = struct.unpack("<H", body[p + 4:p + 6])[0]
        if sub == "HEDR":
            at = 24 + p + 6 + 4  # HEDR = float version, uint32 numRecords, uint32 nextObjectID
            count = struct.unpack("<I", stripped[at:at + 4])[0]
            stripped = stripped[:at] + struct.pack("<I", count - 1) + stripped[at + 4:]
            print(f"HEDR numRecords {count} -> {count - 1}")
            break
        p += 6 + size
    else:
        raise SystemExit("no HEDR subrecord in TES4")

    out = args.out or args.esp
    out.write_bytes(stripped)
    print(f"{args.esp.name}: {len(data)} -> {len(stripped)} bytes, removed {args.signature} {formid:08X}")

    # Re-walk the result: every offset must land on a signature, and the file must end exactly.
    print("\nverifying the rewritten file:")
    total = 0
    for kind, sig, at, size in walk(stripped):
        print(f"  {kind:6} {sig} at {at}, {size} bytes")
        total = max(total, at + size)
    if total != len(stripped):
        raise SystemExit(f"structure ends at {total} but the file is {len(stripped)} bytes")
    print(f"  structure accounts for all {len(stripped)} bytes")


if __name__ == "__main__":
    main()
