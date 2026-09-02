#!/usr/bin/env python3
"""
MORPH v1.5 — QOBLIB ABSOLUTE QUALITY VALIDATOR (Colab)

Purpose
-------
1) Clone/update the official QOBLIB repository.
2) Discover every MIS instance with an official .opt.sol or .bst.sol reference.
3) Parse the reference objective and validate the reference solution against the graph.
4) Load MORPH benchmark results.csv/results-2.csv.
5) Match MORPH runs to QOBLIB instances.
6) Compute absolute quality:
      quality_pct = MORPH_objective / reference_objective * 100
      gap_pct     = (reference_objective - MORPH_objective) /
                     reference_objective * 100
7) Distinguish OPTIMAL from BEST_KNOWN.
8) Detect missing/ambiguous mappings and malformed references.
9) Produce CSV + JSON + Markdown reports.

IMPORTANT
---------
This script does NOT call an objective value "optimal" merely because a
.bst.sol file exists. Only .opt.sol is treated as a proven optimum.
.bst.sol is reported as BEST_KNOWN.

The script also does not silently turn missing MORPH data into zero.

Expected MORPH CSV columns:
    instance, n, edges, budget_ms, seed, solver, objective, ...
The instance field may be either:
    C125-9
    C125-9.gph
    /some/path/C125-9.gph

Colab:
    Run this cell/script directly. It uses /content by default.

Usage:
    python validate_morph_absolute_quality_qoblib_all.py

Optional:
    --results /content/morph_qoblib_v15_bench/results.csv
    --qoblib /content/QOBLIB
    --out /content/morph_absolute_quality_all
    --keep-repo
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path


DEFAULT_ROOT = Path("/content/morph_qoblib_absolute")
DEFAULT_QOBLIB = DEFAULT_ROOT / "QOBLIB"
DEFAULT_RESULTS_CANDIDATES = [
    Path("/content/morph_qoblib_v15_bench/results.csv"),
    Path("/content/morph_qoblib_v15_bench/results-2.csv"),
    Path("/content/results.csv"),
    Path("/content/results-2.csv"),
]


def run_cmd(cmd, cwd=None, check=True):
    print("$", " ".join(map(str, cmd)))
    p = subprocess.run(
        list(map(str, cmd)),
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if p.stdout:
        print(p.stdout.rstrip())
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(map(str, cmd))}")
    return p


def ensure_qoblib(path: Path, keep_repo=False):
    path = path.resolve()
    if (path / ".git").exists():
        print(f"[QOBLIB] Existing repository: {path}")
        try:
            run_cmd(["git", "fetch", "--depth", "1", "origin", "main"], cwd=path, check=False)
            run_cmd(["git", "reset", "--hard", "origin/main"], cwd=path, check=False)
        except Exception as e:
            print("[QOBLIB] Update warning:", e)
        return path

    if path.exists() and any(path.iterdir()):
        raise RuntimeError(
            f"{path} exists but is not a Git repository. "
            "Choose another --qoblib path or delete the directory."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    run_cmd([
        "git", "clone", "--depth", "1",
        "https://github.com/ZIB-AOPT/QOBLIB.git",
        str(path),
    ])
    return path


def locate_mis_root(qoblib: Path) -> Path:
    candidates = [
        qoblib / "07-independentset",
        qoblib / "07-independent-set",
        qoblib / "07_independentset",
    ]
    for c in candidates:
        if c.is_dir():
            return c

    matches = [p for p in qoblib.iterdir() if p.is_dir() and "independent" in p.name.lower()]
    if len(matches) == 1:
        return matches[0]

    raise RuntimeError(
        "Could not locate QOBLIB's Maximum Independent Set directory. "
        f"Checked under {qoblib}"
    )


def find_results_file(user_path: str | None) -> Path:
    if user_path:
        p = Path(user_path)
        if not p.exists():
            raise FileNotFoundError(f"Results file not found: {p}")
        return p.resolve()

    for p in DEFAULT_RESULTS_CANDIDATES:
        if p.exists():
            return p.resolve()

    raise FileNotFoundError(
        "Could not find MORPH results CSV. Use --results /path/to/results.csv"
    )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_graph(path: Path):
    """
    DIMACS-like graph parser:
      p edge N M
      e u v
    QOBLIB MIS instances are expected to use this style.
    Returns n, edge_count, adjacency sets.
    """
    n = None
    declared_m = None
    edges = set()

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            s = raw.strip()
            if not s or s.startswith("c") or s.startswith("#"):
                continue
            parts = s.split()
            if not parts:
                continue
            if parts[0].lower() == "p":
                if len(parts) >= 4:
                    # p edge n m
                    n = int(parts[-2])
                    declared_m = int(parts[-1])
            elif parts[0].lower() == "e" and len(parts) >= 3:
                u, v = int(parts[1]), int(parts[2])
                if u == v:
                    # Self-loops are retained as an edge for validation purposes.
                    edges.add((u, v))
                else:
                    a, b = sorted((u, v))
                    edges.add((a, b))

    if n is None:
        raise ValueError(f"No DIMACS problem line found in {path}")

    return n, len(edges), declared_m, edges


def parse_solution(path: Path):
    """
    QOBLIB solution files can contain:
      # Objective value = 34
    followed by vertex IDs, generally one or more per line.

    We parse all integer tokens outside comments. If an objective header exists,
    use it. Otherwise objective = number of unique vertex IDs.
    """
    text = read_text(path)
    objective = None
    vertices = []

    m = re.search(
        r"(?im)^\s*#\s*objective\s+value\s*=\s*([-+]?\d+(?:\.\d+)?)\s*$",
        text,
    )
    if m:
        objective = float(m.group(1))

    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or s.startswith("c"):
            continue
        # Remove inline comments conservatively.
        s = s.split("#", 1)[0]
        for tok in s.split():
            if re.fullmatch(r"[-+]?\d+", tok):
                vertices.append(int(tok))

    unique_vertices = list(dict.fromkeys(vertices))

    if objective is None:
        objective = float(len(unique_vertices))

    return int(round(objective)), unique_vertices


def validate_solution(n, edges, objective, vertices):
    seen = set()
    errors = []

    for v in vertices:
        if v < 1 or v > n:
            errors.append(f"vertex {v} outside 1..{n}")
        if v in seen:
            errors.append(f"duplicate vertex {v}")
        seen.add(v)

    if objective != len(vertices):
        errors.append(
            f"objective={objective} but solution lists {len(vertices)} vertices"
        )

    for u, v in edges:
        if u in seen and v in seen:
            errors.append(f"adjacent selected vertices: ({u},{v})")
            if len(errors) >= 20:
                break

    return len(errors) == 0, errors


def discover_references(mis_root: Path):
    sol_dir = mis_root / "solutions"
    if not sol_dir.is_dir():
        raise RuntimeError(f"Missing solutions directory: {sol_dir}")

    refs = {}
    warnings = []

    for p in sorted(sol_dir.rglob("*")):
        if not p.is_file():
            continue
        if p.name.endswith(".opt.sol"):
            stem = p.name[:-len(".opt.sol")]
            refs.setdefault(stem, []).append(("OPTIMAL", p))
        elif p.name.endswith(".bst.sol"):
            stem = p.name[:-len(".bst.sol")]
            refs.setdefault(stem, []).append(("BEST_KNOWN", p))

    selected = {}
    for stem, items in refs.items():
        # Prefer OPTIMAL if both exist.
        items = sorted(items, key=lambda x: 0 if x[0] == "OPTIMAL" else 1)
        selected[stem] = items[0]
        if len(items) > 1:
            warnings.append(
                f"{stem}: multiple solution references; selected {items[0][0]}"
            )

    return selected, warnings


def discover_instances(mis_root: Path):
    inst_dir = mis_root / "instances"
    if not inst_dir.is_dir():
        raise RuntimeError(f"Missing instances directory: {inst_dir}")

    by_stem = {}
    for p in sorted(inst_dir.rglob("*")):
        if not p.is_file():
            continue
        # QOBLIB MIS instances are .gph in the current repository.
        if p.suffix.lower() in {".gph", ".graph", ".dimacs", ".txt"}:
            by_stem.setdefault(p.stem, []).append(p)

    return by_stem


def normalize_instance_name(value: str) -> str:
    s = Path(str(value).strip()).name
    # Remove known graph suffix.
    for suffix in [".gph", ".graph", ".dimacs", ".txt"]:
        if s.lower().endswith(suffix):
            s = s[:-len(suffix)]
    return s


def read_results(path: Path):
    with path.open("r", newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise RuntimeError(f"Results CSV is empty: {path}")

    required = {"instance", "solver", "objective"}
    missing = required - set(rows[0].keys())
    if missing:
        raise RuntimeError(f"Results CSV missing columns: {sorted(missing)}")

    for r in rows:
        r["_instance_stem"] = normalize_instance_name(r["instance"])
        try:
            r["_objective"] = float(r["objective"])
        except Exception:
            r["_objective"] = math.nan

        if "budget_ms" in r:
            try:
                r["_budget_ms"] = float(r["budget_ms"])
            except Exception:
                r["_budget_ms"] = math.nan
        else:
            r["_budget_ms"] = math.nan

        if "seed" in r:
            try:
                r["_seed"] = int(float(r["seed"]))
            except Exception:
                r["_seed"] = None
        else:
            r["_seed"] = None

    return rows


def is_morph_solver(name):
    s = str(name).strip().lower()
    return s in {"morph", "morph_v15", "morph v1.5", "morph_v1.5"} or "morph" in s


def compute_reports(rows, refs, instances, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    # Validate official references.
    ref_rows = []
    ref_by_stem = {}

    for stem, (kind, sol_path) in sorted(refs.items()):
        candidates = instances.get(stem, [])
        if not candidates:
            ref_rows.append({
                "instance": stem,
                "reference_type": kind,
                "reference_file": str(sol_path),
                "graph_file": "",
                "n": "",
                "edges": "",
                "reference_objective": "",
                "reference_solution_size": "",
                "reference_valid": "NO_GRAPH",
                "validation_errors": "No matching graph instance found",
            })
            continue

        graph_path = candidates[0]
        try:
            n, edge_count, declared_m, edges = parse_graph(graph_path)
            obj, verts = parse_solution(sol_path)
            valid, errors = validate_solution(n, edges, obj, verts)

            ref_by_stem[stem] = {
                "kind": kind,
                "path": sol_path,
                "graph": graph_path,
                "n": n,
                "edges": edge_count,
                "declared_edges": declared_m,
                "objective": obj,
                "vertices": verts,
                "valid": valid,
                "errors": errors,
            }

            ref_rows.append({
                "instance": stem,
                "reference_type": kind,
                "reference_file": str(sol_path),
                "graph_file": str(graph_path),
                "n": n,
                "edges": edge_count,
                "declared_edges": declared_m if declared_m is not None else "",
                "reference_objective": obj,
                "reference_solution_size": len(verts),
                "reference_valid": "YES" if valid else "NO",
                "validation_errors": " | ".join(errors[:20]),
            })
        except Exception as e:
            ref_rows.append({
                "instance": stem,
                "reference_type": kind,
                "reference_file": str(sol_path),
                "graph_file": str(graph_path),
                "n": "",
                "edges": "",
                "reference_objective": "",
                "reference_solution_size": "",
                "reference_valid": "PARSE_ERROR",
                "validation_errors": str(e),
            })

    with (out_dir / "official_reference_audit.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.DictWriter(f, fieldnames=list(ref_rows[0].keys()) if ref_rows else [])
        if ref_rows:
            w.writeheader()
            w.writerows(ref_rows)

    morph_rows = [r for r in rows if is_morph_solver(r["solver"])]
    absolute = []

    for r in morph_rows:
        stem = r["_instance_stem"]
        ref = ref_by_stem.get(stem)

        if ref is None:
            status = "NO_REFERENCE"
            ref_obj = math.nan
            quality = math.nan
            gap = math.nan
            ref_type = ""
            n = ""
            edges = ""
            ref_valid = ""
        elif not ref["valid"]:
            status = "INVALID_REFERENCE"
            ref_obj = ref["objective"]
            quality = math.nan
            gap = math.nan
            ref_type = ref["kind"]
            n = ref["n"]
            edges = ref["edges"]
            ref_valid = "NO"
        elif math.isnan(r["_objective"]):
            status = "NO_MORPH_OBJECTIVE"
            ref_obj = ref["objective"]
            quality = math.nan
            gap = math.nan
            ref_type = ref["kind"]
            n = ref["n"]
            edges = ref["edges"]
            ref_valid = "YES"
        else:
            ref_obj = float(ref["objective"])
            morph_obj = r["_objective"]
            quality = (morph_obj / ref_obj * 100.0) if ref_obj else math.nan
            gap = ((ref_obj - morph_obj) / ref_obj * 100.0) if ref_obj else math.nan

            if ref["kind"] == "OPTIMAL":
                status = "HIT_OPTIMUM" if morph_obj >= ref_obj else "BELOW_OPTIMUM"
            else:
                status = "MATCH_BEST_KNOWN" if morph_obj >= ref_obj else "BELOW_BEST_KNOWN"

            ref_type = ref["kind"]
            n = ref["n"]
            edges = ref["edges"]
            ref_valid = "YES"

        out = dict(r)
        for k in list(out):
            if k.startswith("_"):
                del out[k]

        out.update({
            "instance_stem": stem,
            "reference_type": ref_type,
            "n": n if n != "" else r.get("n", ""),
            "edges": edges if edges != "" else r.get("edges", ""),
            "reference_objective": ref_obj,
            "reference_valid": ref_valid,
            "absolute_quality_pct": quality,
            "absolute_gap_pct": gap,
            "absolute_status": status,
        })
        absolute.append(out)

    # CSV
    if absolute:
        fieldnames = list(absolute[0].keys())
        with (out_dir / "absolute_quality_runs.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(absolute)

    # Aggregate by instance/budget.
    groups = defaultdict(list)
    for r in absolute:
        if r["absolute_status"] in {"HIT_OPTIMUM", "BELOW_OPTIMUM",
                                    "MATCH_BEST_KNOWN", "BELOW_BEST_KNOWN"}:
            key = (r["instance_stem"], r.get("budget_ms", ""))
            groups[key].append(r)

    summary = []
    for (stem, budget), rs in sorted(groups.items()):
        qualities = []
        gaps = []
        objs = []
        hits = 0

        for r in rs:
            try:
                q = float(r["absolute_quality_pct"])
                if math.isfinite(q):
                    qualities.append(q)
            except Exception:
                pass
            try:
                g = float(r["absolute_gap_pct"])
                if math.isfinite(g):
                    gaps.append(g)
            except Exception:
                pass
            try:
                o = float(r["objective"])
                if math.isfinite(o):
                    objs.append(o)
            except Exception:
                pass
            if r["absolute_status"] in {"HIT_OPTIMUM", "MATCH_BEST_KNOWN"}:
                hits += 1

        ref = ref_by_stem.get(stem)
        summary.append({
            "instance": stem,
            "reference_type": ref["kind"] if ref else "",
            "n": ref["n"] if ref else "",
            "edges": ref["edges"] if ref else "",
            "reference_objective": ref["objective"] if ref else "",
            "budget_ms": budget,
            "runs": len(rs),
            "objective_mean": sum(objs) / len(objs) if objs else "",
            "objective_best": max(objs) if objs else "",
            "objective_worst": min(objs) if objs else "",
            "quality_mean_pct": sum(qualities) / len(qualities) if qualities else "",
            "quality_best_pct": max(qualities) if qualities else "",
            "quality_worst_pct": min(qualities) if qualities else "",
            "gap_mean_pct": sum(gaps) / len(gaps) if gaps else "",
            "gap_best_pct": min(gaps) if gaps else "",
            "hit_reference_runs": hits,
            "hit_reference_pct": (100.0 * hits / len(rs)) if rs else "",
        })

    if summary:
        with (out_dir / "absolute_quality_by_budget.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
            w.writeheader()
            w.writerows(summary)

    # Coverage and aggregate statistics.
    discovered_refs = len(refs)
    valid_refs = sum(
        1 for x in ref_by_stem.values() if x["valid"]
    )
    morph_instances = {r["_instance_stem"] for r in morph_rows}
    matched_instances = morph_instances & set(ref_by_stem)
    missing_from_morph = sorted(set(ref_by_stem) - morph_instances)
    morph_only = sorted(morph_instances - set(ref_by_stem))

    optimal_instances = sum(
        1 for x in ref_by_stem.values() if x["kind"] == "OPTIMAL"
    )
    best_known_instances = sum(
        1 for x in ref_by_stem.values() if x["kind"] == "BEST_KNOWN"
    )

    meta = {
        "generated_at_unix": time.time(),
        "results_file": str(results_path_global),
        "qoblib_path": str(qoblib_global),
        "mis_root": str(mis_root_global),
        "discovered_reference_files": discovered_refs,
        "valid_reference_instances": valid_refs,
        "optimal_instances": optimal_instances,
        "best_known_instances": best_known_instances,
        "morph_result_rows": len(morph_rows),
        "morph_instances": len(morph_instances),
        "matched_reference_instances": len(matched_instances),
        "missing_morph_instances": missing_from_morph,
        "morph_only_instances": morph_only,
    }

    (out_dir / "absolute_quality_metadata.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Markdown report.
    lines = []
    lines.append("# MORPH v1.5 — QOBLIB Absolute Quality Report")
    lines.append("")
    lines.append(f"- Reference instances discovered: **{discovered_refs}**")
    lines.append(f"- Valid official references: **{valid_refs}**")
    lines.append(f"- OPTIMAL references: **{optimal_instances}**")
    lines.append(f"- BEST_KNOWN references: **{best_known_instances}**")
    lines.append(f"- MORPH result rows: **{len(morph_rows)}**")
    lines.append(f"- Matched instances: **{len(matched_instances)}**")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "OPTIMAL means QOBLIB labels the reference as an optimal solution. "
        "BEST_KNOWN means it is a best-known feasible solution, not a proof of optimality."
    )
    lines.append(
        "Quality is MORPH objective divided by the official reference objective. "
        "A 100% result against BEST_KNOWN means MORPH matches the current best-known value; "
        "it does not independently prove optimality."
    )
    lines.append("")
    lines.append("## Per-instance / budget")
    lines.append("")
    if summary:
        lines.append(
            "| Instance | Ref | n | Edges | Budget ms | Mean obj | Best obj | "
            "Mean quality | Best quality | Mean gap | Hit ref |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for s in summary:
            def fmt(v, digits=2):
                if v == "" or v is None:
                    return ""
                try:
                    return f"{float(v):.{digits}f}"
                except Exception:
                    return str(v)

            lines.append(
                f"| {s['instance']} | {s['reference_type']} | {s['n']} | {s['edges']} | "
                f"{s['budget_ms']} | {fmt(s['objective_mean'])} | {fmt(s['objective_best'])} | "
                f"{fmt(s['quality_mean_pct'])}% | {fmt(s['quality_best_pct'])}% | "
                f"{fmt(s['gap_mean_pct'])}% | {fmt(s['hit_reference_pct'])}% |"
            )
    else:
        lines.append("No matched MORPH runs with usable reference data were found.")

    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    if missing_from_morph:
        lines.append("Instances with official reference but no MORPH results:")
        for x in missing_from_morph:
            lines.append(f"- {x}")
    else:
        lines.append("All discovered official-reference instances have MORPH rows.")

    if morph_only:
        lines.append("")
        lines.append("MORPH instances without an official .opt.sol/.bst.sol reference:")
        for x in morph_only:
            lines.append(f"- {x}")

    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append("- `official_reference_audit.csv` — parsed and independently checked QOBLIB references.")
    lines.append("- `absolute_quality_runs.csv` — every MORPH run matched to its reference.")
    lines.append("- `absolute_quality_by_budget.csv` — aggregate quality by instance and budget.")
    lines.append("- `absolute_quality_metadata.json` — coverage metadata.")
    lines.append("")

    (out_dir / "ABSOLUTE_QUALITY_REPORT.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )

    return meta, summary


def print_console_summary(meta, summary):
    print("\n" + "=" * 88)
    print("MORPH v1.5 — QOBLIB ABSOLUTE QUALITY")
    print("=" * 88)
    print(f"Official reference instances : {meta['discovered_reference_files']}")
    print(f"Valid references             : {meta['valid_reference_instances']}")
    print(f"  OPTIMAL                    : {meta['optimal_instances']}")
    print(f"  BEST_KNOWN                 : {meta['best_known_instances']}")
    print(f"MORPH rows                   : {meta['morph_result_rows']}")
    print(f"Matched instances            : {meta['matched_reference_instances']}")
    print("-" * 88)

    if not summary:
        print("NO MATCHED MORPH RUNS WITH VALID REFERENCES")
        return

    for s in summary:
        print(
            f"{s['instance']:22s} "
            f"{s['reference_type']:10s} "
            f"n={str(s['n']):>6s} "
            f"budget={str(s['budget_ms']):>7s}ms "
            f"obj={float(s['objective_best']):>8.2f} "
            f"quality={float(s['quality_best_pct']):>7.2f}% "
            f"gap={float(s['gap_best_pct']):>7.2f}% "
            f"hit={float(s['hit_reference_pct']):>6.1f}%"
        )

    print("-" * 88)
    if meta["missing_morph_instances"]:
        print("Missing MORPH instances:")
        print("  " + ", ".join(meta["missing_morph_instances"]))
    else:
        print("Coverage: all discovered official-reference instances are present in MORPH results.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default=None)
    parser.add_argument("--qoblib", default=str(DEFAULT_QOBLIB))
    parser.add_argument("--out", default=str(DEFAULT_ROOT / "results"))
    parser.add_argument("--keep-repo", action="store_true")
    args, _unknown = parser.parse_known_args()

    root = DEFAULT_ROOT
    root.mkdir(parents=True, exist_ok=True)

    results_path = find_results_file(args.results)
    qoblib_path = ensure_qoblib(Path(args.qoblib))
    mis_root = locate_mis_root(qoblib_path)

    global results_path_global, qoblib_global, mis_root_global
    results_path_global = results_path
    qoblib_global = qoblib_path
    mis_root_global = mis_root

    print("=" * 88)
    print("MORPH v1.5 — QOBLIB ABSOLUTE QUALITY VALIDATOR")
    print("=" * 88)
    print(f"Results : {results_path}")
    print(f"QOBLIB  : {qoblib_path}")
    print(f"MIS root: {mis_root}")

    refs, warnings = discover_references(mis_root)
    instances = discover_instances(mis_root)
    rows = read_results(results_path)

    print(f"\n[1] QOBLIB references discovered: {len(refs)}")
    print(f"[2] QOBLIB graph stems discovered: {len(instances)}")
    print(f"[3] MORPH result rows: {len(rows)}")
    print(f"[4] MORPH rows: {sum(is_morph_solver(r['solver']) for r in rows)}")

    if warnings:
        print("\nReference warnings:")
        for w in warnings[:20]:
            print(" -", w)

    out_dir = Path(args.out)
    meta, summary = compute_reports(rows, refs, instances, out_dir)
    print_console_summary(meta, summary)

    print("\nGenerated:")
    for p in [
        out_dir / "official_reference_audit.csv",
        out_dir / "absolute_quality_runs.csv",
        out_dir / "absolute_quality_by_budget.csv",
        out_dir / "absolute_quality_metadata.json",
        out_dir / "ABSOLUTE_QUALITY_REPORT.md",
    ]:
        if p.exists():
            print(" ", p)

    print("\nDONE.")


if __name__ == "__main__":
    main()
