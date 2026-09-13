"""Detach named child nodes from their parent by nulling the child reference.

Why: GunHeatRefractionOnlyStrong.nif carries two BSValueNode add-on nodes,
`AddOnNode196` and `AddOnNode212`. A BSValueNode holds no geometry of its own - the
engine looks up the ADDN record whose Node Index matches the value and attaches that
record's model at load time. That is why collapsing every m_Flames BSTriShape in the
file did not remove the fire: the fire was never in the file.

Setting the parent's child reference to -1 removes the node from the scene graph
entirely, so the engine has nothing to attach to. Block sizes and all other references
stay byte-identical - only the one int32 slot changes.

FO4 node layout, verified against this file:
    +0x00 uint32  name
    +0x04 uint32  numExtraDataList
    +...  int32   extraDataList[n]
    +...  int32   controller
    +...  uint32  flags
    +...          transform: translation(12) + rotation(36) + scale(4)
    +...  int32   collisionObject
    +...  uint32  numChildren
    +...  int32   children[numChildren]
FO4 NiNode has no effects array.

Usage:
    python tools/detach_nif_child_nodes.py <nif> --names AddOnNode
"""

from __future__ import annotations

import argparse
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from inspect_nif_blocks import parse_header

NODE_TYPES = {"NiNode", "NiBillboardNode", "BSValueNode", "BSOrderedNode", "NiSwitchNode"}


def children_offset(raw: bytes) -> int:
    offset = 4
    extra_count = struct.unpack_from("<I", raw, offset)[0]
    offset += 4 + (extra_count * 4)
    offset += 4   # controller
    offset += 4   # flags
    offset += 52  # transform
    offset += 4   # collision object
    return offset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("nif", type=Path)
    parser.add_argument("--names", nargs="+", required=True, help="Substring match on child node names")
    parser.add_argument("--backup-suffix", default=".pre-addon-detach")
    args = parser.parse_args()

    data = bytearray(args.nif.read_bytes())
    parsed = parse_header(bytes(data))
    strings = parsed["strings"]

    names: dict[int, str] = {}
    for block in parsed["blocks"]:
        index = struct.unpack_from("<i", data, block["offset"])[0]
        if 0 <= index < len(strings):
            names[block["index"]] = strings[index]

    detached = 0
    for block in parsed["blocks"]:
        if block["type"] not in NODE_TYPES:
            continue

        base = block["offset"]
        raw = bytes(data[base : base + block["size"]])
        offset = children_offset(raw)
        count = struct.unpack_from("<I", raw, offset)[0]

        for slot in range(count):
            slot_offset = base + offset + 4 + (slot * 4)
            child = struct.unpack_from("<i", data, slot_offset)[0]
            if child < 0:
                continue
            child_name = names.get(child, "")
            if not any(pattern in child_name for pattern in args.names):
                continue

            struct.pack_into("<i", data, slot_offset, -1)
            detached += 1
            print(f"detach  {names.get(block['index'], '?')} -> slot {slot} was block {child} ({child_name})")

    if not detached:
        raise SystemExit("No child detached; check --names")

    backup = args.nif.with_suffix(args.nif.suffix + args.backup_suffix)
    if not backup.exists():
        shutil.copy2(args.nif, backup)
    args.nif.write_bytes(bytes(data))
    print(f"\nWrote {args.nif} ({detached} child reference(s) nulled, size unchanged: {len(data)} bytes)")


if __name__ == "__main__":
    main()
