#!/usr/bin/env python3
"""Join DIMACS benchmark summaries with published clique-number references.

Reads evidence/dimacs_mis/{as-is,complement}/budget_<ms>ms/dimacs_mis_summary.csv
and evidence/dimacs_mis/omega_reference.csv, then writes:
  - combined_summary.csv: one row per (convention, instance, budget)
  - COMBINED_TABLE.md:    per-instance table with omega references

Check: for a complement run, the MIS of the complement is a clique of the
original graph, so it cannot exceed the clique number omega. A complement
result above an EXACT omega is reported as a violation and makes the script
exit non-zero. Results above a lower-bound reference are reported as notes.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "evidence" / "dimacs_mis"
BUDGETS = [10, 50, 100, 1000]
CONVENTIONS = ["as-is", "complement"]


def load_summaries() -> list[dict]:
    rows = []
    for conv in CONVENTIONS:
        for budget in BUDGETS:
            path = ROOT / conv / f"budget_{budget}ms" / "dimacs_mis_summary.csv"
            with path.open(encoding="utf-8") as stream:
                for row in csv.DictReader(stream):
                    row["budget_ms"] = int(row["budget_ms"])
                    row["convention"] = conv
                    rows.append(row)
    return rows


def main() -> int:
    refs = {}
    with (ROOT / "omega_reference.csv").open(encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            refs[row["instance"]] = (int(row["omega"]), row["exact"] == "1")

    rows = load_summaries()
    instances = sorted({r["instance"] for r in rows}, key=lambda s: s.lower())
    violations, notes = [], []
    for row in rows:
        if row["convention"] != "complement" or row["instance"] not in refs:
            continue
        omega, exact = refs[row["instance"]]
        top = float(row["objective_max"])
        if top > omega and exact:
            violations.append(f"{row['instance']} @{row['budget_ms']}ms: {top:.0f} > omega {omega}")
        elif top > omega:
            notes.append(f"{row['instance']} @{row['budget_ms']}ms: {top:.0f} exceeds lower bound {omega}")

    long_path = ROOT / "combined_summary.csv"
    fields = ["convention", "instance", "n", "edges", "budget_ms", "runs",
              "objective_min", "objective_p10", "objective_p50", "objective_p90",
              "objective_max", "objective_mean", "wall_ms_mean", "all_valid"]
    with long_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    index = {(r["convention"], r["instance"], r["budget_ms"]): r for r in rows}

    def cell(conv, inst, budget):
        r = index[(conv, inst, budget)]
        lo, med, hi = float(r["objective_min"]), float(r["objective_p50"]), float(r["objective_max"])
        span = f"{lo:.0f}" if lo == hi else f"{lo:.0f}–{hi:.0f}"
        return f"{med:.0f} [{span}]"

    lines = [
        "# DIMACS MIS: combined table",
        "",
        "Each cell: P50 over 5 seeds, with [min–max] over the same 5 seeds.",
        "Complement columns: MIS of the complement = clique number of the DIMACS graph.",
        "As-is columns: MIS of the DIMACS file's graph (a different quantity).",
        "omega: published clique number from the roars.dev table; '≥' marks a lower bound.",
        "",
        "| Instance | n | m | ω | Complement 10 ms | 50 ms | 100 ms | 1000 ms | As-is 100 ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for inst in instances:
        base = index[("as-is", inst, 100)]
        omega, exact = refs.get(inst, (None, False))
        omega_txt = "n/a" if omega is None else (f"{omega}" if exact else f"≥{omega}")
        comp = [cell("complement", inst, b) for b in BUDGETS]
        lines.append(
            f"| {inst} | {base['n']} | {base['edges']} | {omega_txt} | "
            + " | ".join(comp) + f" | {cell('as-is', inst, 100)} |"
        )
    lines += ["", "## Checks", ""]
    lines.append(f"- Complement results above an exact omega: {len(violations)}")
    lines += [f"  - {v}" for v in violations]
    lines.append(f"- Complement results above a lower-bound reference: {len(notes)}")
    lines += [f"  - {n}" for n in notes]
    lines.append(f"- Runs with any invalid set: {sum(1 for r in rows if r['all_valid'] != 'True')}")
    (ROOT / "COMBINED_TABLE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {long_path.name} and COMBINED_TABLE.md; violations={len(violations)} notes={len(notes)}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
