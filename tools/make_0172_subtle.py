"""Reduce the original BC5 normal-vector amplitude; retain every 0.17.1 NIF block.

This edits encoded vector data, not a painted replacement plume. All inputs are
read-only; outputs are created only once in the isolated 0.17.1 refinement tree.
"""
from pathlib import Path
from local_paths import required_path
import hashlib
import io
import json
import struct
import sys
import zipfile
import zlib

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] if Path(__file__).parent.name == 'tools' else Path(required_path('BHE_PROJECT_ROOT'))
PROJECT = Path(required_path('BHE_PROJECT_ROOT'))
BACKUP = PROJECT / 'Backups/before-0.17.2-opacity-trial-20260909'
BA2 = Path(required_path('FALLOUT4_DIR') / 'Data/Fallout4 - Textures1.ba2')
NIF_PATH = 'Meshes/GunHeatHaze/GunHeatBarrelRefractionCard.nif'
OLD_TEXTURE = r'textures\Effects\SmokeVapor01Tile_n.dds'
NEW_TEXTURE = r'textures\GunHeatHaze\Soft0172_n.dds'
sys.path.insert(0, str(ROOT / 'tools'))
from inspect_nif_blocks import parse_header


def sha(data):
    return hashlib.sha256(data).hexdigest()


def create(path, data):
    if path.exists():
        assert path.read_bytes() == data, f'Refusing to replace {path}'
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)
    assert path.read_bytes() == data


def header(size, mip_count):
    raw = bytearray(148)
    raw[:4] = b'DDS '
    struct.pack_into('<7I', raw, 4, 124, 0xa1007, size, size, max(1, (size + 3)//4)**2*16, 0, mip_count)
    struct.pack_into('<8I', raw, 76, 32, 4, int.from_bytes(b'DX10', 'little'), 0, 0, 0, 0, 0)
    struct.pack_into('<I', raw, 108, 0x401008)
    struct.pack_into('<5I', raw, 128, 83, 3, 0, 1, 0)
    return bytes(raw)


def vanilla_mips():
    with BA2.open('rb') as stream:
        magic, version, kind, count, names = struct.unpack('<4sI4sIQ', stream.read(24))
        assert (magic, version, kind) == (b'BTDX', 1, b'DX10')
        stream.seek(names)
        matches = []
        for i in range(count):
            length = struct.unpack('<H', stream.read(2))[0]
            if stream.read(length).decode().lower() == OLD_TEXTURE.lower():
                matches.append(i)
        assert len(matches) == 1
        stream.seek(24)
        for _ in range(matches[0] + 1):
            record = struct.unpack('<I4sIBBHHHBBH', stream.read(24))
            chunks = [struct.unpack('<QIIHHI', stream.read(24)) for _ in range(record[4])]
        assert record[5:10] == (24, 512, 512, 10, 83)
        levels = {}
        for offset, packed, unpacked, first, last, marker in chunks:
            assert marker == 0xbaadf00d
            stream.seek(offset)
            payload = stream.read(packed or unpacked)
            if packed:
                payload = zlib.decompress(payload)
            assert len(payload) == unpacked
            cursor = 0
            for mip in range(first, last + 1):
                size = max(1, 512 >> mip)
                length = max(1, (size + 3)//4)**2*16
                assert mip not in levels
                levels[mip] = payload[cursor:cursor+length]
                cursor += length
            assert cursor == len(payload)
        assert sorted(levels) == list(range(10))
        return [levels[i] for i in range(10)]


def palette(a, b):
    # BC4_UNORM integer decode for choosing the nearest encoded normal value.
    p = np.zeros((len(a), 8), dtype=np.int32)
    p[:, 0], p[:, 1] = a, b
    eight = a > b
    for i in range(1, 7):
        p[eight, i+1] = ((7-i)*a[eight] + i*b[eight])//7
    for i in range(1, 5):
        p[~eight, i+1] = ((5-i)*a[~eight] + i*b[~eight])//5
    p[~eight, 6], p[~eight, 7] = 0, 255
    return p


def halve_bc5(payload):
    # A BC5 block is two BC4 blocks: 2 endpoints + 16 three-bit selectors each.
    original = np.frombuffer(payload, dtype=np.uint8).reshape(-1, 8)
    p = palette(original[:, 0].astype(int), original[:, 1].astype(int))
    selector_bits = np.zeros(len(original), dtype=np.uint64)
    for i in range(6):
        selector_bits |= original[:, i+2].astype(np.uint64) << (8*i)
    selectors = ((selector_bits[:, None] >> (np.arange(16, dtype=np.uint64)*3)) & 7).astype(int)
    values = p[np.arange(len(p))[:, None], selectors]
    # UNORM neutral is 127.5. Half tangent-space X/Y, preserving each mip's pattern.
    desired = 127.5 + .5 * (values - 127.5)
    a = np.rint(desired.max(axis=1)).astype(int)
    b = np.rint(desired.min(axis=1)).astype(int)
    encoded_palette = palette(a, b)
    chosen = np.abs(encoded_palette[:, None, :] - desired[:, :, None]).argmin(axis=2)
    output = np.zeros_like(original)
    output[:, 0], output[:, 1] = a, b
    bits = np.sum(chosen.astype(np.uint64) << (np.arange(16, dtype=np.uint64)*3), axis=1, dtype=np.uint64)
    for i in range(6):
        output[:, i+2] = ((bits >> (i*8)) & 255).astype(np.uint8)
    return output.tobytes()


def retarget_nif(original):
    parsed = parse_header(original)
    blocks = [original[b['offset']:b['offset']+b['size']] for b in parsed['blocks']]
    assert len(blocks) == 18 and parsed['blocks'][14]['type'] == 'BSShaderTextureSet'
    raw = blocks[14]
    count, = struct.unpack_from('<I', raw)
    cursor, slots = 4, []
    for _ in range(count):
        length, = struct.unpack_from('<I', raw, cursor)
        cursor += 4
        slots.append(raw[cursor:cursor+length])
        cursor += length
    assert cursor == len(raw) and slots[:2] == [OLD_TEXTURE.encode()]*2
    slots[:2] = [NEW_TEXTURE.encode()]*2
    blocks[14] = struct.pack('<I', count) + b''.join(struct.pack('<I', len(s))+s for s in slots)
    leading = bytearray(original[:parsed['blocks'][0]['offset']])
    # Locate only the block-size table; preserve all other header bytes.
    pos = original.index(b'\n') + 1 + 17
    for _ in range(4):
        pos += original[pos] + 1
    types, = struct.unpack_from('<H', original, pos)
    pos += 2
    for _ in range(types):
        length, = struct.unpack_from('<I', original, pos)
        pos += 4 + length
    pos += len(blocks)*2
    struct.pack_into('<I', leading, pos+14*4, len(blocks[14]))
    result = bytes(leading) + b''.join(blocks) + original[parsed['data_end']:]
    after = parse_header(result)
    for i, block in enumerate(after['blocks']):
        if i != 14:
            assert result[block['offset']:block['offset']+block['size']] == blocks[i]
    assert struct.unpack_from('<f', blocks[4], 72)[0] == 0.0
    return result


def main():
    original_nif = (BACKUP/'GunHeatBarrelRefractionCard.nif').read_bytes()
    assert sha(original_nif) == '98ddd6fd6738d79b1c54e3dd78cbbd7c6e9e54c630f77c9405669bc70aad7ff9'
    assert (ROOT/'Data'/NIF_PATH).read_bytes() == original_nif
    original = vanilla_mips()
    # Preserve the original texture data before producing the modified vector map.
    old_dds = header(512, 10) + b''.join(original)
    create(BACKUP/'SmokeVapor01Tile_n.dds', old_dds)
    new = [halve_bc5(level) for level in original]
    measurements = []
    for i, (old_level, new_level) in enumerate(zip(original, new)):
        size = max(1, 512 >> i)
        def decode(level):
            return np.array(Image.open(io.BytesIO(header(size, 1)+level)))[..., :2].astype(float)
        old_values, new_values = decode(old_level), decode(new_level)
        desired = 127.5 + .5*(old_values-127.5)
        max_error = float(np.abs(new_values-desired).max())
        # Independent DDS decoder checks the encoded result, not just endpoints.
        assert max_error <= 11, (i, max_error)
        before_rms = float(np.sqrt(np.mean((old_values-127.5)**2)))
        after_rms = float(np.sqrt(np.mean((new_values-127.5)**2)))
        ratio = after_rms/before_rms
        corr = float(np.corrcoef(old_values.ravel(), new_values.ravel())[0, 1]) if np.std(old_values) > 2 else None
        if before_rms > 8:
            assert .47 <= ratio <= .54, (i, ratio)
        else:
            assert abs(after_rms-.5*before_rms) <= 1, (i, ratio)
        if corr is not None:
            assert corr > .98, (i, corr)
        measurements.append(dict(size=size, rms_ratio=ratio, correlation=corr, max_encoded_error=max_error))
    dds = header(512, 10)+b''.join(new)
    nif = retarget_nif(original_nif)
    create(ROOT/'Data/Textures/GunHeatHaze/Soft0172_n.dds', dds)
    # This is the only existing asset being changed, in the isolated worktree.
    assert (BACKUP/'GunHeatBarrelRefractionCard.nif').read_bytes() == original_nif
    (ROOT/'Data'/NIF_PATH).write_bytes(nif)
    report = dict(baseline='0.17.1', trial='0.17.2-subtle-refraction', original_texture_sha256=sha(old_dds),
                  texture_sha256=sha(dds), nif_sha256=sha(nif), vanilla_source=str(BA2),
                  normal_xy_multiplier=.5, preserved_nif_blocks=17, changed_nif_block='BSShaderTextureSet paths only',
                  mips=measurements, limitation='Static vector checks only; perceived transparency needs in-game comparison.')
    create(ROOT/'docs/subtle-0.17.2/asset-verification.json', (json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
