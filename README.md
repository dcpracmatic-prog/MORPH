# MORPH v1.5


 [![Tests](https://github.com/dcpracmatic-prog/MORPH/actions/workflows/ci.yml/badge.svg)](https://github.com/dcpracmatic-prog/MORPH/actions/workflows/ci.yml)


**Maximum Independent Set — Low-Latency Heuristic Solver**
MORPH v1.5 is a heuristic solver for the Maximum Independent Set (MIS) problem. Its core construction repeatedly selects a currently active vertex with minimum residual degree, adds that vertex to the independent set, and removes it and its active neighbors. The implementation uses CSR adjacency storage and a lazy min-heap.

This repository is intentionally focused: source, reproducibility scripts, small real datasets, and benchmark evidence. It does not claim a general-purpose exact-solver replacement.

## What is here

- `src/morph_v15.cpp` — scalable v1.5 implementation and synthetic BA scaling harness.
- `src/morph_qoblib_solver.cpp` — budgeted MORPH solver used for QOBLIB head-to-head runs.
- `src/morph_api.cpp` — C API (`morph_solve`) for the Python wrapper; the solver itself is untouched.
- `python/morph.py` — Python wrapper (ctypes, same pattern as HBAG): builds `libmorph.so` on first import and returns the independent set itself, re-checked in Python. Run `python -m morph` from the repo root for a demo on the three small datasets.
- `scripts/run_qoblib_morph_cpsat.py` — MORPH vs OR-Tools CP-SAT benchmark over discovered QOBLIB MIS instances.
- `scripts/run_dimacs_mis.py` — DIMACS edge-format MIS benchmark with at least ten instances, five or more seeds, raw rows, and P10/P50/P90 summaries.
- `scripts/validate_absolute_quality.py` — validates MORPH results against official QOBLIB `.opt.sol` / `.bst.sol` references. Its per-instance/budget aggregates carry an internal cross-check (mean of percentages vs percentage of the mean); a mismatch fails loudly. No external RR-PF oracle is wired in — none exists in this repository.
- `datasets/` — Karate Club, College Football, and Kangaroo examples used during development.
- `evidence/` — scaling evidence and the earlier six-instance raw CSV.

## Build

```bash
make clean
make
bash scripts/smoke_test.sh
```

## Python wrapper

```bash
make libmorph
PYTHONPATH=python python -m morph
```

`python/morph.py` loads `libmorph.so` through ctypes (building it first
if needed) and exposes `solve_mis(path, method="morph", budget_ms=100,
seed=1)`, which returns the independent set itself — size, vertices,
and validity checked both in C++ and again in Python.

## QOBLIB benchmark

In Google Colab or another Linux environment with Git and Python:

```bash
python scripts/run_qoblib_morph_cpsat.py \
  --qoblib /content/QOBLIB \
  --out results/qoblib_morph_vs_cpsat.csv \
  --solver ./morph_qoblib_solver
```

The default protocol is all discovered QOBLIB MIS graphs, budgets `10, 50, 100, 1000 ms`, five seeds, and two solvers. For the 50-instance QOBLIB set used in the validation run, that is 2,000 solver executions.

CP-SAT is configured with `num_search_workers=1` and the same wall-clock limit. A run with no feasible incumbent is recorded as `has_incumbent=0` and does not receive an artificial objective of zero.

## DIMACS MIS benchmark

Place at least ten DIMACS edge-format instances in a directory. Supported suffixes are `.clq`, `.dimacs`, `.graph`, `.txt`, and `.col`. Each file must use the standard `p edge n m` problem line and `e u v` edge records. Curated instance families may include brock, C-fat, keller, and p_hat; this repository does not claim to vendor those benchmark files.

```bash
make
python scripts/run_dimacs_mis.py \
  --dimacs-dir /path/to/dimacs-instances \
  --solver ./morph_qoblib_solver \
  --budget-ms 100 \
  --seeds 1,2,3,4,5 \
  --out results/dimacs_mis
```

The runner refuses fewer than ten input instances or fewer than five distinct seeds. It validates graph dimensions and edge counts, checks the solver's independent-set validity flag, and writes per-seed CSV, per-instance P10/P50/P90 CSV, and a Markdown report. The percentiles describe variability across the specified seeds; they are not confidence intervals and do not establish optimality. Downloaded DIMACS data must be retained with its original source/license information.

Measured DIMACS results are packaged in `evidence/dimacs_mis/` (13 instances, 5 seeds, budgets 10/50/100/1000 ms, 260 runs, all valid; run 2026-11-23). At 100 ms the P50 sizes are: MANN_a9 3, brock200_1 6, brock200_2 10, brock400_1 6, c-fat200-1 18, c-fat200-5 3, c-fat500-1 40, hamming8-4 16, keller4 15, p_hat300-1 39, p_hat300-2 26, p_hat300-3 8, san200_0.7_1 7. Only p_hat300-1 varies across seeds (38 at 10 ms, 39 from 50 ms up); every other instance is identical on all seeds at all budgets. The `.clq` files are clique-benchmark graphs used as-is as MIS instances, so published maximum-clique optima do not apply to these sizes. There is no CP-SAT column for DIMACS yet, so this run supports no superiority claim. The budget is a deadline for new restarts, not a hard cap: at the 10 ms budget the measured wall time sometimes reaches ~30–65 ms, because the first min-residual-degree pass runs to completion first. See `evidence/dimacs_mis/README.md` for the full statement.

## Absolute quality

The absolute-quality validator parses official QOBLIB references and distinguishes `OPTIMAL` from `BEST_KNOWN`. Matching a `BEST_KNOWN` value is not an independent proof of optimality.

```bash
python scripts/validate_absolute_quality.py \
  --results results/qoblib_morph_vs_cpsat.csv \
  --out results/absolute_quality
```

## Current evidence

The v1.5 residual-degree construction improved the synthetic Barabási–Albert stress results by roughly 7.2–7.5% over degree-greedy across 32,768 to 1,048,576 vertices. These are synthetic quality comparisons, not optimality claims.

The QOBLIB validation showed rapid feasible MIS construction on real benchmark graphs. MORPH reached known optimal values on several instances and produced incumbents on some instances where CP-SAT had no incumbent within the same short wall-clock budget. This supports a low-latency heuristic hypothesis; it does not establish general superiority over CP-SAT.

The DIMACS outcome is the measured run in `evidence/dimacs_mis/` — MORPH alone, no competing solver, no optimality claim. Under the complement convention at 1000 ms, MORPH reached the published ω on all five seeds for 15 of the 35 instances with exact ω, and fell below the published lower bound on five of the six instances that have only a bound. The ω values come from a third-party table and were not checked against the DIMACS originals.

## Reproducibility note

Wall-clock equality is not equal CPU-cycle equality. The CP-SAT baseline is deliberately single-worker to keep the comparison controlled. Hardware, compiler, OR-Tools version, seed, and budget should be recorded with any new benchmark.

## Scope

MORPH is currently best described as a low-latency combinatorial heuristic for MIS. Claims of exactness, exponential speedups, quantum resistance, or universal superiority are outside the evidence in this repository.

## License

MORPH is licensed under the GNU General Public License v3.0.

See [`LICENSE`](LICENSE) for the full license text.
