#!/usr/bin/env python3
"""Reproducible multi-seed benchmark for DIMACS Maximum Independent Set graphs.

The input directory must contain at least ten DIMACS edge-format files:
    p edge <number_of_vertices> <number_of_edges>
    e <one_based_vertex_u> <one_based_vertex_v>

The solver binary is built from src/morph_qoblib_solver.cpp. The script records
raw per-seed results, P10/P50/P90 percentiles, and the min/max range over the
seeds. It does not claim optimality.

Convention: pass --convention complement when --dimacs-dir holds complemented
graphs written by scripts/complement_dimacs.py. Then the MIS size equals the
clique number of the original DIMACS graph. The label is recorded in every
output so as-is and complement runs cannot be mixed up.
"""
from __future__ import annotations

import argparse
import csv
import math
import re
import subprocess
import sys
from pathlib import Path
from statistics import mean

SUPPORTED_SUFFIXES = {".clq", ".dimacs", ".graph", ".txt", ".col"}


def parse_dimacs(path: Path) -> tuple[int, int]:
    """Validate DIMACS p edge/e records and return (vertices, unique edges)."""
    n = declared_edges = None
    edges: set[tuple[int, int]] = set()
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line_no, raw in enumerate(stream, 1):
            line = raw.strip()
            if not line or line.startswith("c"):
                continue
            fields = line.split()
            if fields[0] == "p":
                if len(fields) != 4 or fields[1] != "edge":
                    raise ValueError(f"{path}:{line_no}: expected 'p edge n m'")
                if n is not None:
                    raise ValueError(f"{path}:{line_no}: duplicate problem line")
                n, declared_edges = int(fields[2]), int(fields[3])
                if n < 1 or declared_edges < 0:
                    raise ValueError(f"{path}:{line_no}: invalid graph dimensions")
            elif fields[0] == "e":
                if len(fields) != 3:
                    raise ValueError(f"{path}:{line_no}: expected 'e u v'")
                u, v = int(fields[1]), int(fields[2])
                if u < 1 or v < 1 or u == v:
                    raise ValueError(f"{path}:{line_no}: invalid edge endpoints")
                edges.add((min(u, v), max(u, v)))
            else:
                raise ValueError(f"{path}:{line_no}: unsupported record {fields[0]!r}")
    if n is None:
        raise ValueError(f"{path}: missing 'p edge n m' line")
    if any(v > n for edge in edges for v in edge):
        raise ValueError(f"{path}: edge endpoint exceeds declared vertex count")
    if len(edges) != declared_edges:
        raise ValueError(
            f"{path}: declared {declared_edges} edges but parsed {len(edges)} unique edges"
        )
    return n, len(edges)


def percentile(values: list[float], pct: float) -> float:
    """Linear-interpolated percentile, including for small five-seed samples."""
    ordered = sorted(values)
    if not ordered:
        return math.nan
    position = (len(ordered) - 1) * pct / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def median_interval_coverage(n_seeds: int) -> float:
    """Coverage of [min, max] for the population median under iid sampling.

    For continuous outcomes, P(min <= median <= max) = 1 - 2 * (1/2)**n.
    This assumes seeds are an iid sample, which is only an approximation.
    """
    return 1.0 - 2.0 * (0.5 ** n_seeds)


def run_one(binary: Path, graph: Path, budget_ms: int, seed: int, convention: str) -> dict:
    completed = subprocess.run(
        [str(binary), str(graph), "morph", str(budget_ms), str(seed)],
        check=True, capture_output=True, text=True,
    )
    fields = completed.stdout.strip().split(",")
    if len(fields) != 5:
        raise RuntimeError(f"unexpected solver output for {graph}: {completed.stdout!r}")
    n, edges, objective, wall_ms, valid = fields
    if valid != "1":
        raise RuntimeError(f"solver returned an invalid independent set for {graph}, seed={seed}")
    return {
        "instance": graph.stem, "file": graph.name, "convention": convention,
        "n": int(n), "edges": int(edges), "budget_ms": budget_ms, "seed": seed,
        "objective": int(objective), "wall_ms": float(wall_ms), "valid": int(valid),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dimacs-dir", required=True, type=Path)
    parser.add_argument("--solver", default="./morph_qoblib_solver", type=Path)
    parser.add_argument("--out", default=Path("results/dimacs_mis"), type=Path)
    parser.add_argument("--budget-ms", type=int, default=100)
    parser.add_argument("--seeds", default="1,2,3,4,5")
    parser.add_argument(
        "--convention", choices=["as-is", "complement"], default="as-is",
        help="as-is: MIS of the file's graph. complement: the files are complements "
             "(MIS size = clique number of the original DIMACS graph).",
    )
    args = parser.parse_args()

    if args.budget_ms < 1:
        parser.error("--budget-ms must be positive")
    if not args.solver.is_file():
        parser.error(f"solver binary not found: {args.solver}")
    seeds = [int(item.strip()) for item in args.seeds.split(",") if item.strip()]
    if len(seeds) < 5 or len(set(seeds)) != len(seeds):
        parser.error("provide at least five distinct seeds")

    graphs = sorted(
        p for p in args.dimacs_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
    )
    if len(graphs) < 10:
        parser.error(f"need at least 10 DIMACS instances; found {len(graphs)}")

    metadata = {}
    for graph in graphs:
        metadata[graph] = parse_dimacs(graph)

    rows = []
    for graph in graphs:
        for seed in seeds:
            rows.append(run_one(args.solver.resolve(), graph.resolve(),
                                args.budget_ms, seed, args.convention))

    args.out.mkdir(parents=True, exist_ok=True)
    raw_path = args.out / "dimacs_mis_runs.csv"
    with raw_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summaries = []
    for graph in graphs:
        group = [row for row in rows if row["file"] == graph.name]
        objectives = [float(row["objective"]) for row in group]
        times = [float(row["wall_ms"]) for row in group]
        n, edges = metadata[graph]
        summaries.append({
            "convention": args.convention,
            "instance": graph.stem, "n": n, "edges": edges,
            "budget_ms": args.budget_ms, "runs": len(group),
            "objective_mean": mean(objectives),
            "objective_min": min(objectives),
            "objective_p10": percentile(objectives, 10),
            "objective_p50": percentile(objectives, 50),
            "objective_p90": percentile(objectives, 90),
            "objective_max": max(objectives),
            "wall_ms_mean": mean(times),
            "wall_ms_p10": percentile(times, 10),
            "wall_ms_p50": percentile(times, 50),
            "wall_ms_p90": percentile(times, 90),
            "all_valid": all(row["valid"] == 1 for row in group),
        })

    summary_path = args.out / "dimacs_mis_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)

    report = [
        "# DIMACS MIS benchmark",
        "",
        f"- Instances: {len(graphs)}",
        f"- Seeds per instance: {len(seeds)} ({', '.join(map(str, seeds))})",
        f"- Budget: {args.budget_ms} ms",
        f"- Convention: {args.convention}",
        "- Solver: MORPH QOBLIB solver",
        "- Reference optimum/best-known values are not inferred by this runner.",
        "- P10/P50/P90 use linear interpolation across the observed seed results.",
        f"- Min/max over {len(seeds)} seeds: [min, max] covers the population median with "
        f"probability {median_interval_coverage(len(seeds)):.4f} under iid sampling "
        "(an approximation; seeds are not a random sample of the solver's behaviour).",
        "",
        "| Instance | n | Edges | Mean MIS | Min | P10 | P50 | P90 | Max | Mean ms | All valid |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for row in summaries:
        report.append(
            f"| {row['instance']} | {row['n']} | {row['edges']} | "
            f"{row['objective_mean']:.2f} | {row['objective_min']:.0f} | "
            f"{row['objective_p10']:.2f} | {row['objective_p50']:.2f} | "
            f"{row['objective_p90']:.2f} | {row['objective_max']:.0f} | "
            f"{row['wall_ms_mean']:.3f} | {'yes' if row['all_valid'] else 'NO'} |"
        )
    (args.out / "DIMACS_MIS_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"instances={len(graphs)} runs={len(rows)}")
    print(f"raw={raw_path}")
    print(f"summary={summary_path}")
    print(f"report={args.out / 'DIMACS_MIS_REPORT.md'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
