from __future__ import annotations

import argparse
import shutil
import struct
from datetime import datetime
from pathlib import Path


RECORD_HEADER_SIZE = 24
GROUP_HEADER_SIZE = 24
HEAT_PROJECTILE_FORM_ID = 0x01000801


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def pack_u16(value: int) -> bytes:
    return struct.pack("<H", value)


def pack_u32(value: int) -> bytes:
    return struct.pack("<I", value)


def iter_subrecords(record_data: bytes):
    pos = 0
    while pos + 6 <= len(record_data):
        sig = record_data[pos : pos + 4]
        size = u16(record_data, pos + 4)
        start = pos + 6
        end = start + size
        yield sig, record_data[start:end]
        pos = end


def make_subrecord(signature: bytes, value: bytes) -> bytes:
    if len(value) > 0xFFFF:
        raise ValueError(f"Subrecord {signature!r} is too large")
    return signature + pack_u16(len(value)) + value


def record_editor_id(record: bytes) -> str:
    for sig, value in iter_subrecords(record[RECORD_HEADER_SIZE:]):
        if sig == b"EDID":
            return value.rstrip(b"\x00").decode("ascii", errors="replace")
    return "<no EDID>"


def patch_record(record: bytes, form_id: int, nam1_model: str | None, modl_model: str | None) -> tuple[bytes, bool]:
    if record[:4] != b"PROJ" or u32(record, 12) != form_id:
        return record, False

    header = bytearray(record[:RECORD_HEADER_SIZE])
    patched_data = bytearray()
    saw_nam1 = nam1_model is None
    saw_modl = modl_model is None
    nam1_bytes = nam1_model.encode("ascii") + b"\x00" if nam1_model is not None else None
    modl_bytes = modl_model.encode("ascii") + b"\x00" if modl_model is not None else None

    for sig, value in iter_subrecords(record[RECORD_HEADER_SIZE:]):
        if sig == b"NAM1" and nam1_bytes is not None:
            patched_data += make_subrecord(sig, nam1_bytes)
            saw_nam1 = True
        elif sig == b"MODL" and modl_bytes is not None:
            patched_data += make_subrecord(sig, modl_bytes)
            saw_modl = True
        else:
            patched_data += make_subrecord(sig, value)

    if not saw_nam1:
        raise RuntimeError(f"PROJ {form_id:08X} {record_editor_id(record)} did not contain NAM1")
    if not saw_modl:
        raise RuntimeError(f"PROJ {form_id:08X} {record_editor_id(record)} did not contain MODL")

    header[4:8] = pack_u32(len(patched_data))
    return bytes(header) + bytes(patched_data), True


def patch_chunk(data: bytes, form_id: int, nam1_model: str | None, modl_model: str | None) -> tuple[bytes, bool]:
    out = bytearray()
    pos = 0
    changed = False

    while pos + RECORD_HEADER_SIZE <= len(data):
        sig = data[pos : pos + 4]

        if sig == b"GRUP":
            size = u32(data, pos + 4)
            group_header = bytearray(data[pos : pos + GROUP_HEADER_SIZE])
            body, body_changed = patch_chunk(data[pos + GROUP_HEADER_SIZE : pos + size], form_id, nam1_model, modl_model)
            if body_changed:
                group_header[4:8] = pack_u32(GROUP_HEADER_SIZE + len(body))
                changed = True
            out += bytes(group_header) + body
            pos += size
            continue

        size = u32(data, pos + 4)
        record = data[pos : pos + RECORD_HEADER_SIZE + size]
        patched, record_changed = patch_record(record, form_id, nam1_model, modl_model)
        if record_changed:
            changed = True
        out += patched
        pos += RECORD_HEADER_SIZE + size

    out += data[pos:]
    return bytes(out), changed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--esp", required=True, type=Path)
    parser.add_argument("--form-id", default=f"{HEAT_PROJECTILE_FORM_ID:08X}", type=lambda text: int(text, 16))
    parser.add_argument("--nam1")
    parser.add_argument("--modl")
    args = parser.parse_args()
    if args.nam1 is None and args.modl is None:
        raise RuntimeError("Specify at least one of --nam1 or --modl")

    esp_data = args.esp.read_bytes()
    patched, changed = patch_chunk(esp_data, args.form_id, args.nam1, args.modl)
    if not changed:
        raise RuntimeError(f"Could not find PROJ:{args.form_id:08X} in {args.esp}")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = args.esp.with_suffix(args.esp.suffix + f".nam1-backup-{timestamp}")
    shutil.copy2(args.esp, backup)
    args.esp.write_bytes(patched)

    print(f"Wrote {args.esp}")
    print(f"Backup: {backup}")
    print(f"PROJ: {args.form_id:08X}")
    if args.modl is not None:
        print(f"MODL: {args.modl}")
    if args.nam1 is not None:
        print(f"NAM1: {args.nam1}")


if __name__ == "__main__":
    main()
