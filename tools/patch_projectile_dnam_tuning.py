from __future__ import annotations

import argparse
import shutil
import struct
from datetime import datetime
from pathlib import Path


RECORD_HEADER_SIZE = 24
GROUP_HEADER_SIZE = 24

DNAM_SPEED_OFFSET = 8
DNAM_RANGE_OFFSET = 12
DNAM_FADE_DURATION_OFFSET = 44
DNAM_COLLISION_RADIUS_OFFSET = 68
DNAM_LIFETIME_OFFSET = 72
HEAT_PROJECTILE_FORM_ID = 0x01000801


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def pack_u16(value: int) -> bytes:
    return struct.pack("<H", value)


def pack_u32(value: int) -> bytes:
    return struct.pack("<I", value)


def pack_float(value: float) -> bytes:
    return struct.pack("<f", value)


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


def make_subrecord(signature: bytes, value: bytes) -> bytes:
    if len(value) > 0xFFFF:
        raise ValueError(f"Subrecord {signature!r} is too large")
    return signature + pack_u16(len(value)) + value


def patch_dnam(value: bytes, speed: float, range_: float, fade: float, lifetime: float, collision_radius: float) -> bytes:
    if len(value) < 93:
        raise RuntimeError(f"Projectile DNAM is unexpectedly short: {len(value)} bytes")

    patched = bytearray(value)
    patched[DNAM_SPEED_OFFSET : DNAM_SPEED_OFFSET + 4] = pack_float(speed)
    patched[DNAM_RANGE_OFFSET : DNAM_RANGE_OFFSET + 4] = pack_float(range_)
    patched[DNAM_FADE_DURATION_OFFSET : DNAM_FADE_DURATION_OFFSET + 4] = pack_float(fade)
    patched[DNAM_COLLISION_RADIUS_OFFSET : DNAM_COLLISION_RADIUS_OFFSET + 4] = pack_float(collision_radius)
    patched[DNAM_LIFETIME_OFFSET : DNAM_LIFETIME_OFFSET + 4] = pack_float(lifetime)
    return bytes(patched)


def patch_record(record: bytes, form_id: int, args: argparse.Namespace) -> tuple[bytes, bool]:
    if record[:4] != b"PROJ" or u32(record, 12) != form_id:
        return record, False

    header = bytearray(record[:RECORD_HEADER_SIZE])
    patched_data = bytearray()
    saw_dnam = False

    for sig, value in iter_subrecords(record):
        if sig == b"DNAM":
            patched_data += make_subrecord(
                sig,
                patch_dnam(
                    value,
                    speed=args.speed,
                    range_=args.range,
                    fade=args.fade,
                    lifetime=args.lifetime,
                    collision_radius=args.collision_radius,
                ),
            )
            saw_dnam = True
        else:
            patched_data += make_subrecord(sig, value)

    if not saw_dnam:
        raise RuntimeError(f"PROJ {form_id:08X} did not contain DNAM")

    header[4:8] = pack_u32(len(patched_data))
    return bytes(header) + bytes(patched_data), True


def patch_chunk(data: bytes, form_id: int, args: argparse.Namespace) -> tuple[bytes, bool]:
    out = bytearray()
    pos = 0
    changed = False

    while pos + RECORD_HEADER_SIZE <= len(data):
        sig = data[pos : pos + 4]
        if sig == b"GRUP":
            size = u32(data, pos + 4)
            header = bytearray(data[pos : pos + GROUP_HEADER_SIZE])
            body, body_changed = patch_chunk(data[pos + GROUP_HEADER_SIZE : pos + size], form_id, args)
            if body_changed:
                header[4:8] = pack_u32(GROUP_HEADER_SIZE + len(body))
                changed = True
            out += bytes(header) + body
            pos += size
            continue

        size = u32(data, pos + 4)
        record = data[pos : pos + RECORD_HEADER_SIZE + size]
        patched, record_changed = patch_record(record, form_id, args)
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
    parser.add_argument("--speed", type=float, default=450.0)
    parser.add_argument("--range", type=float, default=56.0)
    parser.add_argument("--fade", type=float, default=1.2)
    parser.add_argument("--lifetime", type=float, default=1.8)
    parser.add_argument("--collision-radius", type=float, default=0.01)
    args = parser.parse_args()

    esp_data = args.esp.read_bytes()
    patched, changed = patch_chunk(esp_data, args.form_id, args)
    if not changed:
        raise RuntimeError(f"Could not find PROJ:{args.form_id:08X} in {args.esp}")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = args.esp.with_suffix(args.esp.suffix + f".dnam-tuning-backup-{timestamp}")
    shutil.copy2(args.esp, backup)
    args.esp.write_bytes(patched)

    print(f"Wrote {args.esp}")
    print(f"Backup: {backup}")
    print(f"PROJ: {args.form_id:08X}")
    print(f"speed={args.speed}, range={args.range}, fade={args.fade}, lifetime={args.lifetime}, collision_radius={args.collision_radius}")


if __name__ == "__main__":
    main()
