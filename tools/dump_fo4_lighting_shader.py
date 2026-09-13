"""Decode Fallout 4 BSLightingShaderProperty blocks exactly, not by offset guessing.

Field order verified against NifSkope 2.0 dev7 nif.xml, BSLightingShaderProperty
with `User Version 2 == 130`. Prints the shader flag names, refraction strength,
texture set, and any attached *FloatController with its resolved
LightingShaderControlledVariable name.

This is a read-only diagnostic. Usage:
    python tools/dump_fo4_lighting_shader.py <nif> [<nif> ...]
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from inspect_nif_blocks import parse_header

FLAGS1 = [
    "Specular", "Skinned", "Temp_Refraction", "Vertex_Alpha",
    "GreyscaleToPalette_Color", "GreyscaleToPalette_Alpha", "Use_Falloff",
    "Environment_Mapping", "RGB_Falloff", "Cast_Shadows", "Face",
    "UI_Mask_Rects", "Model_Space_Normals", "Non_Projective_Shadows",
    "Landscape", "Refraction", "Fire_Refraction", "Eye_Environment_Mapping",
    "Hair", "Screendoor_Alpha_Fade", "Localmap_Hide_Secret", "Skin_Tint",
    "Own_Emit", "Projected_UV", "Multiple_Textures", "Tessellate", "Decal",
    "Dynamic_Decal", "Character_Lighting", "External_Emittance", "Soft_Effect",
    "ZBuffer_Test",
]

FLAGS2 = [
    "ZBuffer_Write", "LOD_Landscape", "LOD_Objects", "No_Fade", "Double_Sided",
    "Vertex_Colors", "Glow_Map", "Transform_Changed", "Dismemberment_Meatcuff",
    "Tint", "Grass_Vertex_Lighting", "Grass_Uniform_Scale", "Grass_Fit_Slope",
    "Grass_Billboard", "No_LOD_Land_Blend", "Dismemberment", "Wireframe",
    "Weapon_Blood", "Hide_On_Local_Map", "Premult_Alpha", "VATS_Target",
    "Anisotropic_Lighting", "Skew_Specular_Alpha", "Menu_Screen",
    "Multi_Layer_Parallax", "Alpha_Test", "Gradient_Remap",
    "VATS_Target_Draw_All", "Pipboy_Screen", "Tree_Anim", "Effect_Lighting",
    "Refraction_Writes_Depth",
]

LSCV = {
    0: "Refraction Strength", 8: "Environment Map Scale", 9: "Glossiness",
    10: "Specular Strength", 11: "Emissive Multiple", 12: "Alpha",
    20: "U Offset", 21: "U Scale", 22: "V Offset", 23: "V Scale",
}

ESCV = {
    0: "Emissive Multiple", 1: "Falloff Start Angle", 2: "Falloff Stop Angle",
    3: "Falloff Start Opacity", 4: "Falloff Stop Opacity", 5: "Alpha",
    6: "U Offset", 7: "U Scale", 8: "V Offset", 9: "V Scale",
}


def named_bits(value: int, names: list[str]) -> str:
    hits = [names[i] for i in range(32) if value & (1 << i)]
    return f"0x{value:08X} [{', '.join(hits) if hits else 'none'}]"


def parse_lighting_shader(raw: bytes, strings: list[str]) -> dict:
    o = 0

    def u32():
        nonlocal o
        v = struct.unpack_from("<I", raw, o)[0]
        o += 4
        return v

    def i32():
        nonlocal o
        v = struct.unpack_from("<i", raw, o)[0]
        o += 4
        return v

    def f32():
        nonlocal o
        v = struct.unpack_from("<f", raw, o)[0]
        o += 4
        return v

    def name_of(idx: int) -> str:
        return strings[idx] if 0 <= idx < len(strings) else f"<str {idx}>"

    out: dict = {}
    out["shaderType"] = u32()
    out["name"] = name_of(i32())
    extra_count = u32()
    o += extra_count * 4
    out["controller"] = i32()
    out["flags1"] = u32()
    out["flags2"] = u32()
    out["uvOffset"] = (f32(), f32())
    out["uvScale"] = (f32(), f32())
    out["textureSet"] = i32()
    out["emissiveColor"] = (f32(), f32(), f32())
    out["emissiveMultiple"] = f32()
    out["wetMaterial"] = name_of(i32())
    out["texClampMode"] = u32()
    out["alpha"] = f32()
    out["refractionStrength"] = f32()
    out["smoothness"] = f32()
    out["specularColor"] = (f32(), f32(), f32())
    out["specularStrength"] = f32()
    return out


def parse_float_controller(raw: bytes) -> dict:
    # NiTimeController: next(4) flags(2) frequency(4) phase(4) start(4) stop(4)
    # target(4); then BSNiInterpController adds nothing; NiFloatInterpController
    # adds interpolator(4); Bethesda float controller adds controlled variable(4).
    nxt, flags = struct.unpack_from("<iH", raw, 0)
    freq, phase, start, stop, target = struct.unpack_from("<ffffi", raw, 6)
    interp, variable = struct.unpack_from("<ii", raw, 26)
    return {
        "next": nxt, "flags": flags, "frequency": freq, "phase": phase,
        "start": start, "stop": stop, "target": target,
        "interpolator": interp, "variable": variable,
    }


def main() -> None:
    for path in (Path(p) for p in sys.argv[1:]):
        data = path.read_bytes()
        parsed = parse_header(data)
        strings = parsed["strings"]
        print(f"\n=== {path.name} ===")
        for block in parsed["blocks"]:
            raw = data[block["offset"]: block["offset"] + block["size"]]
            kind = block["type"]
            if kind == "BSLightingShaderProperty":
                p = parse_lighting_shader(raw, strings)
                print(f"[{block['index']:02d}] BSLightingShaderProperty name={p['name']!r} type={p['shaderType']}")
                print(f"     flags1 = {named_bits(p['flags1'], FLAGS1)}")
                print(f"     flags2 = {named_bits(p['flags2'], FLAGS2)}")
                print(f"     alpha={p['alpha']:.4f}  refractionStrength={p['refractionStrength']:.4f}"
                      f"  smoothness={p['smoothness']:.3f}")
                print(f"     uvOffset={p['uvOffset']} uvScale={p['uvScale']}"
                      f" textureSet=blk{p['textureSet']} controller=blk{p['controller']}")
            elif kind in ("BSLightingShaderPropertyFloatController", "BSEffectShaderPropertyFloatController"):
                c = parse_float_controller(raw)
                table = LSCV if kind.startswith("BSLighting") else ESCV
                var = table.get(c["variable"], f"<{c['variable']}>")
                print(f"[{block['index']:02d}] {kind}")
                print(f"     variable={c['variable']} ({var}) target=blk{c['target']}"
                      f" interp=blk{c['interpolator']} next=blk{c['next']}")
                print(f"     freq={c['frequency']:.3f} phase={c['phase']:.3f}"
                      f" start={c['start']:.3f} stop={c['stop']:.3f} flags=0x{c['flags']:04X}")


if __name__ == "__main__":
    main()
