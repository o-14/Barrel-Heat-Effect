"""Dump shape/shader details from FO4 NIFs to diagnose invisible effect assets.

For each BSTriShape: name, vertex count, bound sphere.
For each BSEffectShaderProperty / BSLightingShaderProperty: raw float table with
offsets so refraction strength / alpha / emissive candidates can be eyeballed.
For BSShaderTextureSet: texture paths. For *FloatController blocks: the
controlled-variable id and target/interpolator refs.

Usage: python tools/dump_nif_shader_values.py <nif> [<nif> ...]
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from inspect_nif_blocks import parse_header


def u16(data, off):
    return struct.unpack_from("<H", data, off)[0]


def u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


def i32(data, off):
    return struct.unpack_from("<i", data, off)[0]


def f32(data, off):
    return struct.unpack_from("<f", data, off)[0]


def h3(data, off):
    return struct.unpack_from("<3e", data, off)


def block_name(raw, strings):
    idx = u32(raw, 0)
    if idx < len(strings):
        return strings[idx]
    return f"<str {idx:#x}>"


def dump_trishape(raw, strings):
    name = block_name(raw, strings)
    num_verts = u16(raw, 0x70)
    cx, cy, cz, radius = struct.unpack_from("<4f", raw, 0x48)
    print(f"    name={name!r} verts={num_verts} bound=({cx:.2f},{cy:.2f},{cz:.2f}) r={radius:.2f}")
    if num_verts:
        v0 = h3(raw, 0x76)
        v1 = h3(raw, 0x76 + 24) if num_verts > 1 else None
        print(f"    v0=({v0[0]:.2f},{v0[1]:.2f},{v0[2]:.2f})" + (f" v1=({v1[0]:.2f},{v1[1]:.2f},{v1[2]:.2f})" if v1 else ""))


def dump_float_table(raw, start=0):
    floats = []
    for off in range(start, len(raw) - 3, 4):
        val = f32(raw, off)
        ival = u32(raw, off)
        if val != 0.0 and (abs(val) < 1e6 and abs(val) > 1e-6):
            floats.append(f"+{off:#04x}:{val:.4f}")
        elif ival not in (0, 0xFFFFFFFF) and ival < 0x200:
            floats.append(f"+{off:#04x}:i{ival}")
    print("    " + "  ".join(floats))


def dump_texture_set(raw):
    # BSShaderTextureSet is a bare NiObject: u32 count, then sized strings.
    count = u32(raw, 0)
    pos = 4
    for i in range(min(count, 16)):
        if pos + 4 > len(raw):
            break
        length = u32(raw, pos)
        if pos + 4 + length > len(raw):
            break
        text = raw[pos + 4 : pos + 4 + length].rstrip(b"\x00").decode("ascii", errors="replace")
        pos += 4 + length
        if text:
            print(f"    tex[{i}]={text}")


def dump_effect_shader_strings(raw):
    # BSEffectShaderProperty has inline sized strings (source/greyscale/env/normal/envmask)
    pos = 0
    found = []
    while pos + 4 <= len(raw):
        length = u32(raw, pos)
        if 4 < length < 120:
            candidate = raw[pos + 4 : pos + 4 + length]
            if candidate[:1].isalpha() and (b".dds" in candidate.lower() or b"textures" in candidate.lower()):
                found.append((pos, candidate.decode("ascii", errors="replace")))
                pos += 4 + length
                continue
        pos += 1
    for off, text in found:
        print(f"    str+{off:#04x}={text}")


def dump_controller(raw):
    # NiTimeController: next(4) flags(2) freq(4) phase(4) start(4) stop(4) target(4) interp(4) var(4)
    if len(raw) >= 34:
        nxt = i32(raw, 0)
        flags = u16(raw, 4)
        freq = f32(raw, 6)
        start = f32(raw, 14)
        stop = f32(raw, 18)
        target = i32(raw, 22)
        interp = i32(raw, 26)
        var = u32(raw, 30)
        print(f"    next={nxt} flags={flags:#x} freq={freq:.2f} span=({start:.3f},{stop:.3f}) target={target} interp={interp} controlledVar={var}")


def main() -> None:
    for arg in sys.argv[1:]:
        path = Path(arg)
        data = path.read_bytes()
        parsed = parse_header(data)
        strings = parsed["strings"]
        print(f"\n=== {path.name} ({len(data)} bytes, {parsed['num_blocks']} blocks) ===")
        for block in parsed["blocks"]:
            btype = block["type"]
            raw = data[block["offset"] : block["offset"] + block["size"]]
            if btype == "BSTriShape":
                print(f"[{block['index']:02d}] {btype} size={block['size']}")
                dump_trishape(raw, strings)
            elif btype in ("BSEffectShaderProperty", "BSLightingShaderProperty"):
                print(f"[{block['index']:02d}] {btype} size={block['size']} name={block_name(raw, strings)!r}")
                dump_float_table(raw)
                if btype == "BSEffectShaderProperty":
                    dump_effect_shader_strings(raw)
            elif btype == "BSShaderTextureSet":
                print(f"[{block['index']:02d}] {btype}")
                dump_texture_set(raw)
            elif "FloatController" in btype or btype == "BSLagBoneController":
                print(f"[{block['index']:02d}] {btype}")
                dump_controller(raw)
            elif btype == "NiAlphaProperty":
                flags = u16(raw, 12) if len(raw) >= 14 else 0
                threshold = raw[14] if len(raw) >= 15 else 0
                print(f"[{block['index']:02d}] {btype} flags={flags:#06x} threshold={threshold}")


if __name__ == "__main__":
    main()
