from __future__ import annotations

import argparse
import shutil
import struct
from datetime import datetime
from pathlib import Path


RECORD_HEADER_SIZE = 24
GROUP_HEADER_SIZE = 24
HEAT_PROJECTILE_FORM_ID = 0x01000801
NEXT_OBJECT_ID_AFTER_HEAT_PUFF = 0x00000802

DNAM_FLAGS_OFFSET = 0
DNAM_SPEED_OFFSET = 8
DNAM_RANGE_OFFSET = 12
DNAM_LIGHT_OFFSET = 16
DNAM_MUZZLE_FLASH_LIGHT_OFFSET = 20
DNAM_EXPLOSION_PROXIMITY_OFFSET = 24
DNAM_EXPLOSION_TIMER_OFFSET = 28
DNAM_EXPLOSION_OFFSET = 32
DNAM_SOUND_OFFSET = 36
DNAM_MUZZLE_FLASH_DURATION_OFFSET = 40
DNAM_FADE_DURATION_OFFSET = 44
DNAM_IMPACT_FORCE_OFFSET = 48
DNAM_SOUND_COUNTDOWN_OFFSET = 52
DNAM_SOUND_DISABLE_OFFSET = 56
DNAM_DEFAULT_WEAPON_SOURCE_OFFSET = 60
DNAM_CONE_SPREAD_OFFSET = 64
DNAM_COLLISION_RADIUS_OFFSET = 68
DNAM_LIFETIME_OFFSET = 72
DNAM_RELAUNCH_INTERVAL_OFFSET = 76
DNAM_DECAL_DATA_OFFSET = 80
DNAM_COLLISION_LAYER_OFFSET = 84
DNAM_TRACER_FREQUENCY_OFFSET = 88
DNAM_VATS_PROJECTILE_OFFSET = 89

PROJECTILE_FLAG_MUZZLE_FLASH = 0x00000008
PROJECTILE_FLAG_PASS_THROUGH_SMALL_TRANSPARENT = 0x00000200


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


def make_subrecord(signature: bytes, value: bytes) -> bytes:
    if len(value) > 0xFFFF:
        raise ValueError(f"Subrecord {signature!r} is too large")
    return signature + pack_u16(len(value)) + value


def record_editor_id(record: bytes) -> str:
    for sig, value in iter_subrecords(record):
        if sig == b"EDID":
            return value.rstrip(b"\x00").decode("ascii", errors="replace")
    return "<no EDID>"


def patch_tes4_header(existing_esp: bytes, record_count: int) -> bytes:
    if existing_esp[:4] != b"TES4":
        raise RuntimeError("ESP does not start with TES4")

    size = u32(existing_esp, 4)
    tes4 = bytearray(existing_esp[: RECORD_HEADER_SIZE + size])
    data = tes4[RECORD_HEADER_SIZE:]

    pos = 0
    while pos + 6 <= len(data):
        sig = data[pos : pos + 4]
        sub_size = u16(data, pos + 4)
        if sig == b"HEDR":
            value_start = RECORD_HEADER_SIZE + pos + 6
            tes4[value_start + 4 : value_start + 8] = pack_u32(record_count)
            tes4[value_start + 8 : value_start + 12] = pack_u32(NEXT_OBJECT_ID_AFTER_HEAT_PUFF)
            return bytes(tes4)
        pos += 6 + sub_size

    raise RuntimeError("TES4 header did not contain HEDR")


def patch_dnam(value: bytes) -> bytes:
    if len(value) < 93:
        raise RuntimeError(f"Projectile DNAM is unexpectedly short: {len(value)} bytes")

    patched = bytearray(value)
    flags = u32(value, DNAM_FLAGS_OFFSET)
    flags = (flags | PROJECTILE_FLAG_PASS_THROUGH_SMALL_TRANSPARENT) & ~PROJECTILE_FLAG_MUZZLE_FLASH
    patched[DNAM_FLAGS_OFFSET : DNAM_FLAGS_OFFSET + 4] = pack_u32(flags)
    patched[DNAM_SPEED_OFFSET : DNAM_SPEED_OFFSET + 4] = pack_float(1000.0)
    patched[DNAM_RANGE_OFFSET : DNAM_RANGE_OFFSET + 4] = pack_float(192.0)
    patched[DNAM_LIGHT_OFFSET : DNAM_LIGHT_OFFSET + 4] = pack_u32(0)
    patched[DNAM_MUZZLE_FLASH_LIGHT_OFFSET : DNAM_MUZZLE_FLASH_LIGHT_OFFSET + 4] = pack_u32(0)
    patched[DNAM_EXPLOSION_PROXIMITY_OFFSET : DNAM_EXPLOSION_PROXIMITY_OFFSET + 4] = pack_float(0.0)
    patched[DNAM_EXPLOSION_TIMER_OFFSET : DNAM_EXPLOSION_TIMER_OFFSET + 4] = pack_float(0.0)
    patched[DNAM_EXPLOSION_OFFSET : DNAM_EXPLOSION_OFFSET + 4] = pack_u32(0)
    patched[DNAM_SOUND_OFFSET : DNAM_SOUND_OFFSET + 4] = pack_u32(0)
    patched[DNAM_MUZZLE_FLASH_DURATION_OFFSET : DNAM_MUZZLE_FLASH_DURATION_OFFSET + 4] = pack_float(0.0)
    patched[DNAM_FADE_DURATION_OFFSET : DNAM_FADE_DURATION_OFFSET + 4] = pack_float(0.25)
    patched[DNAM_IMPACT_FORCE_OFFSET : DNAM_IMPACT_FORCE_OFFSET + 4] = pack_float(0.0)
    patched[DNAM_SOUND_COUNTDOWN_OFFSET : DNAM_SOUND_COUNTDOWN_OFFSET + 4] = pack_u32(0)
    patched[DNAM_SOUND_DISABLE_OFFSET : DNAM_SOUND_DISABLE_OFFSET + 4] = pack_u32(0)
    patched[DNAM_DEFAULT_WEAPON_SOURCE_OFFSET : DNAM_DEFAULT_WEAPON_SOURCE_OFFSET + 4] = pack_u32(0)
    patched[DNAM_CONE_SPREAD_OFFSET : DNAM_CONE_SPREAD_OFFSET + 4] = pack_float(0.0)
    patched[DNAM_COLLISION_RADIUS_OFFSET : DNAM_COLLISION_RADIUS_OFFSET + 4] = pack_float(0.01)
    patched[DNAM_LIFETIME_OFFSET : DNAM_LIFETIME_OFFSET + 4] = pack_float(0.70)
    patched[DNAM_RELAUNCH_INTERVAL_OFFSET : DNAM_RELAUNCH_INTERVAL_OFFSET + 4] = pack_float(0.01)
    patched[DNAM_DECAL_DATA_OFFSET : DNAM_DECAL_DATA_OFFSET + 4] = pack_u32(0)
    patched[DNAM_COLLISION_LAYER_OFFSET : DNAM_COLLISION_LAYER_OFFSET + 4] = pack_u32(0)
    patched[DNAM_TRACER_FREQUENCY_OFFSET] = 0
    patched[DNAM_VATS_PROJECTILE_OFFSET : DNAM_VATS_PROJECTILE_OFFSET + 4] = pack_u32(0)
    return bytes(patched)


def patch_heat_projectile(record: bytes, model: str) -> bytes:
    if record[:4] != b"PROJ" or u32(record, 12) != HEAT_PROJECTILE_FORM_ID:
        raise RuntimeError("Input record is not GunHeatHeatPuffProjectile")

    header = bytearray(record[:RECORD_HEADER_SIZE])
    patched_data = bytearray()
    saw_dnam = False
    saw_modl = False

    for sig, value in iter_subrecords(record):
        if sig == b"MODL":
            patched_data += make_subrecord(sig, model.encode("ascii") + b"\x00")
            saw_modl = True
            continue
        if sig == b"DNAM":
            patched_data += make_subrecord(sig, patch_dnam(value))
            saw_dnam = True
            continue
        if sig in { b"NAM1", b"NAM2", b"MODT" }:
            continue
        if sig == b"VNAM":
            patched_data += make_subrecord(sig, pack_u32(0))
            continue
        patched_data += make_subrecord(sig, value)

    if not saw_dnam:
        raise RuntimeError("GunHeatHeatPuffProjectile did not contain DNAM")
    if not saw_modl:
        raise RuntimeError("GunHeatHeatPuffProjectile did not contain MODL")

    header[4:8] = pack_u32(len(patched_data))
    return bytes(header) + bytes(patched_data)


def make_top_group(signature: bytes, records: list[bytes]) -> bytes:
    body = b"".join(records)
    return b"GRUP" + pack_u32(GROUP_HEADER_SIZE + len(body)) + signature + pack_u32(0) + pack_u32(0) + pack_u32(0) + body


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--esp", required=True, type=Path)
    parser.add_argument("--model", default=r"Effects\GasLeakAnim.nif")
    args = parser.parse_args()

    esp_data = args.esp.read_bytes()
    heat_record = None
    for record in iter_records_and_groups(esp_data, 0, len(esp_data)):
        if record[:4] == b"PROJ" and u32(record, 12) == HEAT_PROJECTILE_FORM_ID:
            heat_record = record
            break

    if heat_record is None:
        raise RuntimeError(f"Could not find PROJ:{HEAT_PROJECTILE_FORM_ID:08X}")

    patched_heat = patch_heat_projectile(heat_record, args.model)
    tes4 = patch_tes4_header(esp_data, record_count=1)
    patched_esp = tes4 + make_top_group(b"PROJ", [patched_heat])

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = args.esp.with_suffix(args.esp.suffix + f".clean-isolation-backup-{timestamp}")
    shutil.copy2(args.esp, backup)
    args.esp.write_bytes(patched_esp)

    print(f"Wrote {args.esp}")
    print(f"Backup: {backup}")
    print(f"Kept: {HEAT_PROJECTILE_FORM_ID:08X} {record_editor_id(patched_heat)}")
    print("Removed: PROJ 0000481F AssaultRifleProjectile override")
    print(f"MODL: {args.model}")
    print("Removed: NAM1/NAM2 muzzle flash models")
    print("Cleared: muzzle flash flag/light/duration")


if __name__ == "__main__":
    main()
