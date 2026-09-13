from __future__ import annotations

import argparse
import shutil
import struct
from datetime import datetime
from pathlib import Path


RECORD_HEADER_SIZE = 24
GROUP_HEADER_SIZE = 24

ASSAULT_RIFLE_PROJECTILE_FORM_ID = 0x0000481F
HEAT_PUFF_PROJECTILE_FORM_ID = 0x01000801
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

# Keep the non-hostile pass-through style flag only. This avoids muzzle flash,
# explosion, alt trigger, and vanilla bullet penetration flags on the visual puff.
PROJECTILE_FLAG_PASS_THROUGH_SMALL_TRANSPARENT = 0x00000200
PROJECTILE_FLAG_MUZZLE_FLASH = 0x00000008


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
            yield pos, pos + size, sig
            yield from iter_records_and_groups(data, pos + GROUP_HEADER_SIZE, pos + size)
            pos += size
            continue

        size = u32(data, pos + 4)
        yield pos, pos + RECORD_HEADER_SIZE + size, sig
        pos += RECORD_HEADER_SIZE + size


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


def find_record(data: bytes, signature: bytes, form_id: int) -> bytes:
    for start, end, sig in iter_records_and_groups(data, 0, len(data)):
        if sig == signature and u32(data, start + 12) == form_id:
            return data[start:end]
    raise RuntimeError(f"Could not find {signature.decode()}:{form_id:08X}")


def find_existing_records(data: bytes, signature: bytes) -> list[bytes]:
    records: list[bytes] = []
    for start, end, sig in iter_records_and_groups(data, 0, len(data)):
        if sig == signature:
            records.append(data[start:end])
    return records


def record_editor_id(source_record: bytes) -> str:
    for sig, value in iter_subrecords(source_record[RECORD_HEADER_SIZE:]):
        if sig == b"EDID":
            return value.rstrip(b"\x00").decode("ascii", errors="replace")
    return "<no EDID>"


def patched_tes4_header(existing_esp: bytes, record_count: int, next_object_id: int) -> bytes:
    if existing_esp[:4] != b"TES4":
        raise RuntimeError("Existing ESP does not start with TES4")

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
            tes4[value_start + 8 : value_start + 12] = pack_u32(next_object_id)
            return bytes(tes4)
        pos += 6 + sub_size

    raise RuntimeError("TES4 header did not contain HEDR")


def make_top_group(signature: bytes, records: list[bytes]) -> bytes:
    body = b"".join(records)
    size = GROUP_HEADER_SIZE + len(body)
    return b"GRUP" + pack_u32(size) + signature + pack_u32(0) + pack_u32(0) + pack_u32(0) + body


def patch_dnam_for_heat_puff(value: bytes) -> bytes:
    if len(value) < 93:
        raise RuntimeError(f"Projectile DNAM is unexpectedly short: {len(value)} bytes")

    patched = bytearray(value)
    source_flags = u32(value, DNAM_FLAGS_OFFSET)
    patched_flags = (source_flags | PROJECTILE_FLAG_PASS_THROUGH_SMALL_TRANSPARENT) & ~PROJECTILE_FLAG_MUZZLE_FLASH
    patched[DNAM_FLAGS_OFFSET : DNAM_FLAGS_OFFSET + 4] = pack_u32(patched_flags)
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


def make_heat_puff_projectile(source_record: bytes, form_id: int, model_path: str | None) -> bytes:
    header = bytearray(source_record[:RECORD_HEADER_SIZE])
    header[12:16] = pack_u32(form_id)

    patched_data = bytearray()
    saw_dnam = False
    saw_model = False

    for sig, value in iter_subrecords(source_record[RECORD_HEADER_SIZE:]):
        if sig == b"EDID":
            patched_data += make_subrecord(sig, b"GunHeatHeatPuffProjectile\x00")
            continue

        if sig == b"OBND":
            patched_data += make_subrecord(sig, struct.pack("<hhhhhh", -16, -16, -16, 16, 96, 16))
            continue

        if sig == b"MODL":
            patched_data += make_subrecord(sig, (model_path.encode("ascii") + b"\x00") if model_path else value)
            saw_model = True
            continue

        if sig == b"MODT":
            continue

        if sig == b"DNAM":
            patched_data += make_subrecord(sig, patch_dnam_for_heat_puff(value))
            saw_dnam = True
            continue

        if sig in { b"NAM1", b"NAM2" }:
            continue

        if sig == b"VNAM":
            patched_data += make_subrecord(sig, pack_u32(0))
            continue

        patched_data += make_subrecord(sig, value)

    if not saw_model:
        raise RuntimeError(f"{record_editor_id(source_record)} did not contain MODL")
    if not saw_dnam:
        raise RuntimeError(f"{record_editor_id(source_record)} did not contain DNAM")

    header[4:8] = pack_u32(len(patched_data))
    return bytes(header) + bytes(patched_data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--esp", required=True, type=Path)
    parser.add_argument("--model", default=r"GunHeatHaze\AssaultRifleHeatMuzzle.nif")
    parser.add_argument("--source-esm", type=Path)
    parser.add_argument("--source-form-id", type=lambda text: int(text, 16))
    parser.add_argument("--form-id", default=f"{HEAT_PUFF_PROJECTILE_FORM_ID:08X}", type=lambda text: int(text, 16))
    args = parser.parse_args()

    esp_data = args.esp.read_bytes()
    existing_projectiles = find_existing_records(esp_data, b"PROJ")

    source_projectile = None
    if args.source_esm and args.source_form_id is not None:
        source_projectile = find_record(args.source_esm.read_bytes(), b"PROJ", args.source_form_id)
    else:
        for record in existing_projectiles:
            if u32(record, 12) == ASSAULT_RIFLE_PROJECTILE_FORM_ID:
                source_projectile = record
                break
        if source_projectile is None:
            source_projectile = existing_projectiles[0] if existing_projectiles else None
        if source_projectile is None:
            raise RuntimeError("Existing ESP did not contain a source PROJ record to clone")

    model_path = None if args.model.lower() == "preserve" else args.model
    heat_projectile = make_heat_puff_projectile(source_projectile, args.form_id, model_path)

    records_by_form = { u32(record, 12): record for record in existing_projectiles }
    records_by_form[args.form_id] = heat_projectile
    records = [records_by_form[form_id] for form_id in sorted(records_by_form)]

    tes4 = patched_tes4_header(
        esp_data,
        record_count=len(records),
        next_object_id=max(NEXT_OBJECT_ID_AFTER_HEAT_PUFF, (args.form_id & 0x00FFFFFF) + 1),
    )
    proj_group = make_top_group(b"PROJ", records)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = args.esp.with_suffix(args.esp.suffix + f".heat-puff-backup-{timestamp}")
    shutil.copy2(args.esp, backup)
    args.esp.write_bytes(tes4 + proj_group)

    print(f"Wrote {args.esp}")
    print(f"Backup: {backup}")
    print(f"Source projectile: {u32(source_projectile, 12):08X} {record_editor_id(source_projectile)}")
    print(f"Added projectile: {args.form_id:08X} GunHeatHeatPuffProjectile")
    print(f"Model: {args.model}")
    print(f"Projectile records: {len(records)}")


if __name__ == "__main__":
    main()
