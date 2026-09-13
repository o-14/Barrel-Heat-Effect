r"""Compare two compiled Papyrus scripts by meaning instead of by bytes.

A .pex cannot be reproduced byte for byte: the compiler emits its variable, property, function
and user-flag tables in a different order on every run - two compiles of identical source here
differed in 2,460 of 3,668 bytes - and the header carries the source path, the user, the machine
and two timestamps. So "did only the constant change?" cannot be answered with sha256.

This disassembles both files with the game's PapyrusAssembler, then compares them
order-insensitively: tables become dictionaries keyed by name, and each function's labels are
renumbered in order of first appearance so that reordered output still matches. What remains is a
real difference in code or in a stored value.

Usage:
    python -B tools/diff_pex.py <a.pex> <b.pex> [Namespace:Script]
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from local_paths import required_path

ASSEMBLER = Path(required_path('PAPYRUS_ASSEMBLER'))


def disassemble(pex: Path, obj: str) -> list[str]:
    """PapyrusAssembler resolves Namespace:Script against the cwd, so lay the file out that way."""
    namespace, script = obj.split(":") if ":" in obj else ("", obj)
    work = Path(tempfile.mkdtemp(prefix="pexdiff-"))
    target = work / namespace / f"{script}.pex" if namespace else work / f"{script}.pex"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pex, target)
    result = subprocess.run([str(ASSEMBLER), obj, "-D", "-Q"], cwd=work, capture_output=True, text=True)
    out = next(work.rglob("*.disassemble.pas"), None)
    if out is None:
        raise SystemExit(f"disassembly of {pex} failed: {result.stdout}{result.stderr}")
    text = out.read_text(encoding="utf-8", errors="replace").splitlines()
    return text


STRING_LITERAL = re.compile(r'("(?:[^"\\]|\\.)*")')


def squeeze(line: str) -> str:
    """Collapse runs of whitespace OUTSIDE string literals, so the comment column cannot matter.

    Literals are left exactly as they are: a changed message is a change worth reporting.
    """
    parts = STRING_LITERAL.split(line)
    return "".join(part if STRING_LITERAL.fullmatch(part) else re.sub(r"\s+", " ", part)
                   for part in parts).strip()


def canonical_labels(lines: list[str]) -> list[str]:
    """_label7 -> _label#0, _label3 -> _label#1 ... in order of first appearance.

    Renaming changes the text width, which moves the ;@line comment, so squeeze afterwards.
    """
    order: dict[str, str] = {}
    for line in lines:
        for label in re.findall(r"_label\d+", line):
            order.setdefault(label, f"_label#{len(order)}")
    return [squeeze(re.sub(r"_label\d+", lambda m: order[m.group(0)], line)) for line in lines]


def sections(lines: list[str]) -> dict[str, dict[str, list[str]]]:
    """Split the disassembly into named blocks per table, dropping the volatile .info header."""
    found: dict[str, dict[str, list[str]]] = {"variable": {}, "property": {}, "function": {}, "state": {},
                                              "userFlag": {}, "struct": {}}
    stack: list[tuple[str, str, list[str]]] = []
    for raw in lines:
        line = raw.strip()
        opener = re.match(r"\.(variable|property|function|state|struct)\s+(\S+)", line)
        if line.startswith(".flag "):
            found["userFlag"][line.split()[1]] = [line]
        elif opener:
            stack.append((opener.group(1), opener.group(2), []))
        elif stack:
            kind, name, body = stack[-1]
            if line == f".end{kind.capitalize()}" or line.lower() == f".end{kind}":
                found[kind][name] = canonical_labels(body)
                stack.pop()
            else:
                body.append(line)
        if stack and not opener and line and not line.startswith(".end"):
            pass
    return found


def main() -> None:
    a, b = Path(sys.argv[1]), Path(sys.argv[2])
    obj = sys.argv[3] if len(sys.argv) > 3 else "GunHeat:GunHeatController"
    left, right = sections(disassemble(a, obj)), sections(disassemble(b, obj))

    differences = 0
    for kind in left:
        names = sorted(set(left[kind]) | set(right[kind]))
        for name in names:
            first, second = left[kind].get(name), right[kind].get(name)
            if first == second:
                continue
            differences += 1
            print(f"\n{kind} {name}:")
            if first is None or second is None:
                print(f"  only in {a.name if second is None else b.name}")
                continue
            for x, y in zip(first + [""] * len(second), second + [""] * len(first)):
                if x != y:
                    print(f"  - {x}\n  + {y}")

    counts = {kind: len(left[kind]) for kind in left if left[kind]}
    print(f"\ncompared {counts}")
    print(f"{differences} semantic difference(s) between {a.name} and {b.name}"
          if differences else f"{a.name} and {b.name} are semantically identical")


if __name__ == "__main__":
    main()
