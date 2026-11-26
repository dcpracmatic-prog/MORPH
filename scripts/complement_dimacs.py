#!/usr/bin/env python3
"""Write the complement of DIMACS edge-format graphs.

Why this exists: the DIMACS files are clique-benchmark graphs. Their
maximum-clique number omega(G) equals the maximum independent set of the
complement, alpha(complement(G)). Running MIS on the complement therefore
gives sizes that can be compared with published clique optima. Running MIS
on the file as-is gives a different (much smaller) quantity. The runner
handles both; this script produces the complemented copies.

Usage:
    python scripts/complement_dimacs.py --in-dir DIR --out-dir DIR2
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_dimacs_mis import SUPPORTED_SUFFIXES, parse_dimacs  # noqa: E402


def read_edges(path: Path) -> tuple[int, set[tuple[int, int]]]:
    """Validated parse, then return (n, set of 1-based (u, v) with u < v)."""
    n, _ = parse_dimacs(path)
    edges: set[tuple[int, int]] = set()
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for raw in stream:
            fields = raw.split()
            if fields and fields[0] == "e":
                u, v = int(fields[1]), int(fields[2])
                edges.add((min(u, v), max(u, v)))
    return n, edges


def write_complement(source: Path, target: Path) -> tuple[int, int]:
    """Write the complement of `source` to `target`. Returns (n, edges_out)."""
    n, edges = read_edges(source)
    lines = [
        f"c complement of {source.name} (MIS of this graph = clique number of {source.name})",
        f"p edge {n} {n * (n - 1) // 2 - len(edges)}",
    ]
    count = 0
    for u in range(1, n + 1):
        for v in range(u + 1, n + 1):
            if (u, v) not in edges:
                lines.append(f"e {u} {v}")
                count += 1
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return n, count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for source in sorted(args.in_dir.iterdir()):
        if not source.is_file() or source.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        write_complement(source, args.out_dir / source.name)
        count += 1
    print(f"wrote {count} complemented instances to {args.out_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
