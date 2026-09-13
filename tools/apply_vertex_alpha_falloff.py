"""Soften a refraction card's edges with a per-vertex alpha falloff.

Why vertex alpha and not the texture: the card's V offset is scrolled by a shader-wide
UV offset (one tile per 1.667 s), so anything baked into texture space would slide around
with the tile. Vertex alpha is fixed to the geometry and does not scroll.

Why this is plausible at all: FlameJetMuzzleFlash.nif's BaseRefractionMesh003 - the
closest vanilla analogue to our card, being small and viewed close up - has an identical
vertex format and sets Vertex_Alpha (shader flags 1 bit 3) alongside Refraction. Our
Saugus-derived card has the same vertex layout and already carries authored alpha, but
never enabled the flag, so it is ignored.

The falloff uses normalised ELLIPTICAL distance, not raw radius. The card is roughly
40 x 82 local units, so a plain radius would treat a vertex at the left edge (r~20) as
interior while fading one at the top (r~41) to nothing, leaving the left and right edges
hard. Normalising each axis by its own half-extent fades all edges evenly.

FO4 vertex layout for attrs VERTEX|UV|NORMAL|TANGENT|COLORS, stride 24:
    +0   position      3 half
    +6   bitangentX    1 half
    +8   UV            2 half
    +12  normal        3 bytes + bitangentY
    +16  tangent       3 bytes + bitangentZ
    +20  colour        RGBA bytes    <- alpha at +23

Usage:
    python tools/apply_vertex_alpha_falloff.py <nif> --shape Cylinder026 --inner 0.45
"""

from __future__ import annotations

import argparse
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from inspect_nif_blocks import parse_header

NUM_TRIANGLES_OFFSET = 0x6C
NUM_VERTICES_OFFSET = 0x70
DATA_SIZE_OFFSET = 0x72
VERTEX_DATA_OFFSET = 0x76
COLOUR_IN_VERTEX = 20
ALPHA_IN_VERTEX = 23

VERTEX_ALPHA_BIT = 1 << 3  # Fallout4ShaderPropertyFlags1: Vertex_Alpha


def lighting_flags1_offset(raw: bytes) -> int:
    offset = 4 + 4  # shader type, name
    extra_count = struct.unpack_from("<I", raw, offset)[0]
    offset += 4 + (extra_count * 4)
    return offset + 4  # past controller


def smoothstep(value: float) -> float:
    value = min(max(value, 0.0), 1.0)
    return value * value * (3.0 - (2.0 * value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("nif", type=Path)
    parser.add_argument("--shape", required=True)
    parser.add_argument("--inner", type=float, default=0.45,
                        help="Normalised distance where the fade starts (0 = centre, 1 = rim)")
    parser.add_argument("--outer", type=float, default=1.0,
                        help="Normalised distance where alpha reaches zero")
    parser.add_argument("--no-flag", action="store_true",
                        help="Write alpha but leave the Vertex_Alpha shader flag alone")
    parser.add_argument("--backup-suffix", default=".pre-alpha-falloff")
    args = parser.parse_args()

    data = bytearray(args.nif.read_bytes())
    parsed = parse_header(bytes(data))
    strings = parsed["strings"]

    touched = 0
    for block in parsed["blocks"]:
        if block["type"] != "BSTriShape":
            continue

        base = block["offset"]
        name_index = struct.unpack_from("<i", data, base)[0]
        name = strings[name_index] if 0 <= name_index < len(strings) else ""
        if args.shape not in name:
            continue

        num_triangles = struct.unpack_from("<I", data, base + NUM_TRIANGLES_OFFSET)[0]
        num_vertices = struct.unpack_from("<H", data, base + NUM_VERTICES_OFFSET)[0]
        data_size = struct.unpack_from("<I", data, base + DATA_SIZE_OFFSET)[0]
        stride, remainder = divmod(data_size - (num_triangles * 6), num_vertices)
        if remainder or stride < 24:
            raise SystemExit(f"{name}: unexpected vertex stride {stride}")

        start = base + VERTEX_DATA_OFFSET
        points = []
        for index in range(num_vertices):
            points.append(struct.unpack_from("<3e", data, start + (index * stride)))

        half_x = max(abs(p[0]) for p in points) or 1.0
        half_y = max(abs(p[1]) for p in points) or 1.0

        span = max(args.outer - args.inner, 1e-4)
        histogram = {}
        for index, (x, y, _z) in enumerate(points):
            distance = (((x / half_x) ** 2) + ((y / half_y) ** 2)) ** 0.5
            fade = 1.0 - smoothstep((distance - args.inner) / span)
            alpha = int(round(min(max(fade, 0.0), 1.0) * 255))
            offset = start + (index * stride)
            data[offset + COLOUR_IN_VERTEX + 0] = 255
            data[offset + COLOUR_IN_VERTEX + 1] = 255
            data[offset + COLOUR_IN_VERTEX + 2] = 255
            data[offset + ALPHA_IN_VERTEX] = alpha
            histogram[alpha // 32] = histogram.get(alpha // 32, 0) + 1

        print(f"alpha    {name}: {num_vertices} verts, half-extents "
              f"({half_x:.1f}, {half_y:.1f}), fade {args.inner} -> {args.outer}")
        for bucket in sorted(histogram, reverse=True):
            print(f"    alpha {bucket * 32:3d}-{bucket * 32 + 31:3d}: {histogram[bucket]:3d} verts")
        touched += 1

    if not touched:
        raise SystemExit("No shape matched; check --shape")

    if not args.no_flag:
        for block in parsed["blocks"]:
            if block["type"] != "BSLightingShaderProperty":
                continue
            base = block["offset"]
            raw = bytes(data[base: base + block["size"]])
            flags_offset = base + lighting_flags1_offset(raw)
            flags = struct.unpack_from("<I", data, flags_offset)[0]
            if flags & VERTEX_ALPHA_BIT:
                print(f"flag     Vertex_Alpha already set (0x{flags:08X})")
            else:
                struct.pack_into("<I", data, flags_offset, flags | VERTEX_ALPHA_BIT)
                print(f"flag     Shader Flags 1 0x{flags:08X} -> 0x{flags | VERTEX_ALPHA_BIT:08X} "
                      f"(+Vertex_Alpha)")

    backup = args.nif.with_suffix(args.nif.suffix + args.backup_suffix)
    if not backup.exists():
        shutil.copy2(args.nif, backup)
    args.nif.write_bytes(bytes(data))
    print(f"\nWrote {args.nif} (size unchanged: {len(data)} bytes)")


if __name__ == "__main__":
    main()
