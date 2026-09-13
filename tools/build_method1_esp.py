from __future__ import annotations

import argparse
import shutil
import struct
from datetime import datetime
from pathlib import Path


RECORD_HEADER_SIZE = 24
GROUP_HEADER_SIZE = 24
MINIGUN_PROJECTILE_FORM_ID = 0x0003ADFB
DNAM_MUZZLE_FLASH_DURATION_OFFSET = 40
DNAM_MUZZLE_FLASH_LIGHT_OFFSET = 20


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def pack_u16(value: int) -> bytes:
    return struct.pack("<H", value)


def pack_u32(value: int) -> bytes:
    return struct.pack("<I", value)


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


def find_record(data: bytes, signature: bytes, form_id: int) -> bytes:
    for start, end, sig in iter_records_and_groups(data, 0, len(data)):
        if sig != signature:
            continue
        if u32(data, start + 12) == form_id:
            return data[start:end]
    raise RuntimeError(f"Could not find {signature.decode()}:{form_id:08X}")


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


def record_editor_id(source_record: bytes) -> str:
    for sig, value in iter_subrecords(source_record[RECORD_HEADER_SIZE:]):
        if sig == b"EDID":
            return value.rstrip(b"\x00").decode("ascii", errors="replace")
    return "<no EDID>"


def get_subrecord(source_record: bytes, signature: bytes) -> bytes:
    for sig, value in iter_subrecords(source_record[RECORD_HEADER_SIZE:]):
        if sig == signature:
            return value
    raise RuntimeError(f"{record_editor_id(source_record)} did not contain {signature.decode()}")


def parse_form_id(value: str) -> int:
    text = value.strip()
    if text.lower().startswith("0x"):
        text = text[2:]
    return int(text, 16)


def patched_projectile_record(
    source_record: bytes,
    haze_model: str,
    duration: float,
    null_muzzle_flash_light: bool,
    model_info: bytes | None,
) -> bytes:
    header = bytearray(source_record[:RECORD_HEADER_SIZE])
    record_data = source_record[RECORD_HEADER_SIZE:]
    patched_data = bytearray()

    saw_nam1 = False
    saw_dnam = False

    for sig, value in iter_subrecords(record_data):
        if sig == b"DNAM":
            value = bytearray(value)
            struct.pack_into("<f", value, DNAM_MUZZLE_FLASH_DURATION_OFFSET, duration)
            if null_muzzle_flash_light:
                value[DNAM_MUZZLE_FLASH_LIGHT_OFFSET : DNAM_MUZZLE_FLASH_LIGHT_OFFSET + 4] = b"\x00\x00\x00\x00"
            value = bytes(value)
            saw_dnam = True
        elif sig == b"NAM1":
            value = haze_model.encode("ascii") + b"\x00"
            patched_data += make_subrecord(sig, value)
            if model_info is not None:
                patched_data += make_subrecord(b"NAM2", model_info)
            saw_nam1 = True
            continue
        elif sig == b"NAM2":
            continue

        patched_data += make_subrecord(sig, value)

    if not saw_dnam:
        raise RuntimeError(f"{record_editor_id(source_record)} did not contain DNAM")
    if not saw_nam1:
        raise RuntimeError(f"{record_editor_id(source_record)} did not contain NAM1")

    header[4:8] = pack_u32(len(patched_data))
    return bytes(header) + bytes(patched_data)


def patched_tes4_header(existing_esp: bytes, record_count: int) -> bytes:
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
            return bytes(tes4)
        pos += 6 + sub_size

    raise RuntimeError("TES4 header did not contain HEDR")


def make_top_group(signature: bytes, record: bytes) -> bytes:
    size = GROUP_HEADER_SIZE + len(record)
    return b"GRUP" + pack_u32(size) + signature + pack_u32(0) + pack_u32(0) + pack_u32(0) + record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fallout4-esm", required=True, type=Path)
    parser.add_argument("--esp", required=True, type=Path)
    parser.add_argument("--projectile-form-id", default=f"{MINIGUN_PROJECTILE_FORM_ID:08X}", type=parse_form_id)
    parser.add_argument("--haze-model", default=r"Effects\SaugusSmokeMirage.nif")
    parser.add_argument("--duration", default=0.25, type=float)
    parser.add_argument("--null-muzzle-flash-light", action="store_true")
    parser.add_argument(
        "--model-info-arto-form-id",
        type=parse_form_id,
        help="Copy MODT model metadata from this ARTO record into projectile NAM2.",
    )
    args = parser.parse_args()

    esm_data = args.fallout4_esm.read_bytes()
    esp_data = args.esp.read_bytes()

    source_projectile = find_record(esm_data, b"PROJ", args.projectile_form_id)
    model_info = None
    model_info_edid = None
    if args.model_info_arto_form_id is not None:
        model_info_record = find_record(esm_data, b"ARTO", args.model_info_arto_form_id)
        model_info = get_subrecord(model_info_record, b"MODT")
        model_info_edid = record_editor_id(model_info_record)

    projectile_edid = record_editor_id(source_projectile)
    projectile = patched_projectile_record(
        source_projectile,
        args.haze_model,
        args.duration,
        args.null_muzzle_flash_light,
        model_info,
    )
    tes4 = patched_tes4_header(esp_data, record_count=1)
    proj_group = make_top_group(b"PROJ", projectile)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = args.esp.with_suffix(args.esp.suffix + f".method1-backup-{timestamp}")
    shutil.copy2(args.esp, backup)
    args.esp.write_bytes(tes4 + proj_group)

    print(f"Wrote {args.esp}")
    print(f"Backup: {backup}")
    print(f"Override: PROJ {args.projectile_form_id:08X} {projectile_edid}")
    print(f"NAM1: {args.haze_model}")
    if args.model_info_arto_form_id is not None:
        print(f"NAM2 copied from ARTO {args.model_info_arto_form_id:08X} {model_info_edid}")
    print(f"Muzzle duration: {args.duration:.6f}")
    print(f"Null muzzle flash light: {args.null_muzzle_flash_light}")


if __name__ == "__main__":
    main()
