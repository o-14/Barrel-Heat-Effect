"""Resolve F4SE Address Library IDs to RVAs / absolute addresses.

The plugin calls engine functions through REL::ID(n), which only means something once
it is mapped through version-1-10-163-0.bin. This decodes that file so IDs used in the
source can be turned into addresses we can look at in Ghidra.

Fallout 4's address library is NOT the delta-encoded SKSE v2 format. Verified against
version-1-10-163-0.bin (25,327,608 bytes): it is a flat table.

    uint64  count                  (1,582,975)
    count x { uint64 id; uint64 rva; }

8 + 1582975 * 16 == 25327608 exactly.

Usage:
    python tools/addresslib_lookup.py <bin> 357908 1452334
    python tools/addresslib_lookup.py <bin> --rva 0x1e3c0a0
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

IMAGE_BASE = 0x140000000
WORD_SIZE = 8


def load(path: Path) -> dict[int, int]:
    data = path.read_bytes()
    count = struct.unpack_from("<Q", data, 0)[0]
    expected = 8 + (count * 16)
    if expected != len(data):
        raise SystemExit(
            f"size mismatch: header says {count} entries "
            f"(expected {expected} bytes) but file is {len(data)}")

    print(f"# {path.name}: {count} entries", file=sys.stderr)
    mapping: dict[int, int] = {}
    for index in range(count):
        ident, rva = struct.unpack_from("<QQ", data, 8 + (index * 16))
        mapping[ident] = rva
    return mapping


def main() -> None:
    path = Path(sys.argv[1])
    mapping = load(path)

    args = sys.argv[2:]
    if args and args[0] == "--rva":
        target = int(args[1], 0)
        if target > IMAGE_BASE:
            target -= IMAGE_BASE
        hits = [i for i, off in mapping.items() if off == target]
        print(f"RVA 0x{target:x} -> IDs {hits or '(none)'}")
        return

    for token in args:
        ident = int(token, 0)
        rva = mapping.get(ident)
        if rva is None:
            print(f"ID {ident}: NOT FOUND")
        else:
            print(f"ID {ident:>9}  RVA 0x{rva:08x}  ->  {IMAGE_BASE + rva:#x}")


if __name__ == "__main__":
    main()
