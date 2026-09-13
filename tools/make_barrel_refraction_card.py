"""Author the barrel heat refraction card from Bethesda's SaugusSmokeMirage.

Why this base and not the flamethrower spray: SaugusSmokeMirage.nif is already exactly
the asset the audit recipe describes, and it is proven to render in vanilla as an
ordinary world object.

    NiNode "SaugusSmokeMirage"
    +- NiBillboardNode "Cylinder026"          <- already camera-facing
    |  +- BSTriShape "Cylinder026:0"          <- 91 verts, bound r=120.24
    |     +- BSLightingShaderProperty         <- Refraction, no Fire_Refraction
    |        +- BSShaderTextureSet            <- SmokeVapor01Tile_n in both slots
    |     controllers: V Offset -> U Offset -> Refraction Strength
    +- BSTriShape "EditorMarker021:0"         <- editor-only, removed here

It carries none of the machinery that made GunHeatRefractionOnlyStrong.nif unusable:
no BSBehaviorGraphExtraData, no BSConnectPoint::Parents, no BSValueNode add-on nodes,
no collision, no NiControllerManager. Its three controllers are plain NiTimeControllers
that tick on their own, so nothing has to activate a named sequence.

Shader configuration, which is the part that matters:
    flags1 = 0x80408201  Specular | Cast_Shadows | Refraction | Own_Emit | ZBuffer_Test
    flags2 = 0x00000030  Double_Sided | Vertex_Colors        (ZBuffer_Write OFF)

Note this differs from the flamer/minigun card, which sets Fire_Refraction and turns
ZBuffer_Write ON. The mirage flag set is the one proven to render on a standalone
object, and Double_Sided removes any chance of the card being invisible from behind.

Edits applied here, all in place - every block size and reference is unchanged:

1. Rename string 'SaugusSmokeMirage' -> 'GunHeatBarrelHaze' (identical length).
2. Detach the EditorMarker shape from the root.
3. Scale the billboard node down from world-mirage size to barrel size.
4. Set the baked Refraction Strength.
5. Truncate the controller chain after V Offset. The U Offset controller animates a
   curve that is constant zero (a no-op), and the third controller animates Refraction
   Strength itself - which would fight the DLL writing refractionPower every frame.
   Dropping both leaves the scroll to the NIF and the intensity to our code.
6. Raise the V Offset controller frequency. Vanilla scrolls one tile per 33.333 s,
   which reads as a slow drifting mirage; the Minigun scrolls one tile per 1.667 s.

Usage:
    python tools/make_barrel_refraction_card.py \
        "$out/Meshes/Effects/SaugusSmokeMirage.nif" \
        Data/Meshes/GunHeatHaze/GunHeatBarrelRefractionCard.nif
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from inspect_nif_blocks import parse_header

OLD_NAME = b"SaugusSmokeMirage"
NEW_NAME = b"GunHeatBarrelHaze"

MINIGUN_TILE_SECONDS = 1.667
SAUGUS_TILE_SECONDS = 33.333


def node_children_offset(raw: bytes) -> int:
    offset = 4
    extra_count = struct.unpack_from("<I", raw, offset)[0]
    offset += 4 + (extra_count * 4)
    return offset + 4 + 4 + 52 + 4  # controller, flags, transform, collision


def node_scale_offset(raw: bytes) -> int:
    offset = 4
    extra_count = struct.unpack_from("<I", raw, offset)[0]
    offset += 4 + (extra_count * 4)
    offset += 4 + 4  # controller, flags
    return offset + 12 + 36  # after translation and rotation


def lighting_refraction_offset(raw: bytes) -> int:
    offset = 4 + 4  # shader type, name
    extra_count = struct.unpack_from("<I", raw, offset)[0]
    offset += 4 + (extra_count * 4)
    offset += 4        # controller
    offset += 4 + 4    # shader flags 1 and 2
    offset += 8 + 8    # uv offset, uv scale
    offset += 4        # texture set
    offset += 12 + 4   # emissive colour, emissive multiple
    offset += 4        # wet material
    offset += 4        # texture clamp mode
    offset += 4        # alpha
    return offset      # refraction strength


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--scale", type=float, default=0.25,
                        help="Billboard node scale; source card bound radius is 120.24")
    parser.add_argument("--refraction", type=float, default=0.25,
                        help="Baked Refraction Strength (vanilla range 0.03-0.20)")
    parser.add_argument("--tile-seconds", type=float, default=MINIGUN_TILE_SECONDS,
                        help="Seconds for one full V-offset tile scroll")
    args = parser.parse_args()

    data = bytearray(args.source.read_bytes())

    if data.count(OLD_NAME) == 0:
        raise SystemExit(f"{args.source} does not look like SaugusSmokeMirage")
    renames = data.count(OLD_NAME)
    data = bytearray(bytes(data).replace(OLD_NAME, NEW_NAME))
    print(f"rename      {OLD_NAME.decode()} -> {NEW_NAME.decode()} ({renames} occurrence(s), length unchanged)")

    parsed = parse_header(bytes(data))
    blocks = parsed["blocks"]
    strings = parsed["strings"]

    def block_name(block) -> str:
        index = struct.unpack_from("<i", data, block["offset"])[0]
        return strings[index] if 0 <= index < len(strings) else ""

    # 2. Detach the editor marker from the root.
    root = blocks[0]
    raw = bytes(data[root["offset"]: root["offset"] + root["size"]])
    offset = node_children_offset(raw)
    count = struct.unpack_from("<I", raw, offset)[0]
    detached = 0
    for slot in range(count):
        slot_offset = root["offset"] + offset + 4 + (slot * 4)
        child = struct.unpack_from("<i", data, slot_offset)[0]
        if child < 0:
            continue
        if "EditorMarker" in block_name(blocks[child]):
            struct.pack_into("<i", data, slot_offset, -1)
            detached += 1
            print(f"detach      root child slot {slot} -> block {child} ({block_name(blocks[child])})")
    if not detached:
        print("warning     no EditorMarker child found")

    # 3. Scale the billboard node.
    for block in blocks:
        if block["type"] != "NiBillboardNode":
            continue
        raw = bytes(data[block["offset"]: block["offset"] + block["size"]])
        scale_offset = block["offset"] + node_scale_offset(raw)
        previous = struct.unpack_from("<f", data, scale_offset)[0]
        struct.pack_into("<f", data, scale_offset, args.scale)
        print(f"scale       {block_name(block)}: {previous} -> {args.scale} "
              f"(card radius 120.24 -> {120.24 * args.scale:.1f} units)")

    # 4. Bake refraction strength.
    for block in blocks:
        if block["type"] != "BSLightingShaderProperty":
            continue
        raw = bytes(data[block["offset"]: block["offset"] + block["size"]])
        refraction_offset = block["offset"] + lighting_refraction_offset(raw)
        previous = struct.unpack_from("<f", data, refraction_offset)[0]
        struct.pack_into("<f", data, refraction_offset, args.refraction)
        print(f"refraction  {previous:.4f} -> {args.refraction:.4f}")

    # 5 and 6. Keep only the V Offset controller, and speed it up.
    for block in blocks:
        if block["type"] != "BSLightingShaderPropertyFloatController":
            continue
        base = block["offset"]
        variable = struct.unpack_from("<i", data, base + 26 + 4)[0]
        if variable != 22:  # 22 = V Offset
            continue
        following = struct.unpack_from("<i", data, base)[0]
        struct.pack_into("<i", data, base, -1)
        frequency = SAUGUS_TILE_SECONDS / args.tile_seconds
        struct.pack_into("<f", data, base + 6, frequency)
        print(f"controller  V Offset: next block {following} -> -1 (drops U Offset no-op "
              f"and the Refraction Strength oscillator)")
        print(f"controller  V Offset: frequency 1.0 -> {frequency:.3f} "
              f"(one tile per {args.tile_seconds}s)")

    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_bytes(bytes(data))
    print(f"\nWrote {args.target} ({len(data)} bytes, size unchanged from source)")


if __name__ == "__main__":
    main()
