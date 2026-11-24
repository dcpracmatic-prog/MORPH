# SUPERSEDED — DIMACS MIS benchmark, 13-instance run (kept for history)

> **Superseded.** This 13-instance run is replaced by the 41-instance, two-convention
> run in `evidence/dimacs_mis/` (see `../../README.md`). Do not cite the numbers or the
> claims below as current.
>
> Known problems with this document:
> - **Environment line is unverified.** The "htch-runtime 7.0.0-44-generic, 4 CPUs,
>   g++ 13.3.0, Python 3.12.3" description cannot be confirmed from the repository. It
>   is not the environment of the current run (Linux 6.1.189, 2 vCPUs, g++ 14.2.0,
>   Python 3.13.5).
> - **Convention claim is incomplete.** It says the `.clq` files are used "the same
>   convention as the QOBLIB MIS set". The as-is convention matches QOBLIB's brock200_1,
>   but QOBLIB is not uniform across its clique-derived files, and the complement
>   convention (the one comparable to published clique numbers) was not run.
> - **"Re-checked by the solver" is self-reported.** No independent checker verified the
>   returned sets.
> - **Input checksums** for the 13 files were carried over; their origin is not
>   recorded in the repository.
>
> The as-is numbers below reproduce on the overlapping instances in the current run
> (P50 identical at 100 ms on all 13; one mean differs, p_hat300-1 38.8 vs 39.0, timing).

First measured DIMACS run for this repository, 2026-11-23.

## Protocol

- **Instances:** 13 DIMACS edge-format graphs (see `SOURCES.md` for the
  source mirror and `SHA256SUMS.txt` for checksums). Families: brock
  (200_1, 200_2, 400_1), c-fat (200-1, 200-5, 500-1), keller4,
  p_hat (300-1, 300-2, 300-3), hamming8-4, MANN_a9, san200_0.7_1.
  The `.clq` files are used as-is, as MIS instances — the same convention
  as the QOBLIB MIS set in this repo. They are clique-benchmark graphs,
  so published maximum-clique optima for these files do **not** apply
  to the MIS sizes below, and no optimality claim is made here.
- **Solver:** `morph_qoblib_solver`, method `morph`, built from the
  reformatted source (reformat verified: deterministic outputs identical
  before/after, see the commit message).
- **Seeds:** 1, 2, 3, 4, 5. **Budgets:** 10, 50, 100, 1000 ms.
  13 instances × 5 seeds × 4 budgets = **260 runs**, all with a valid
  independent set (`valid=1`, re-checked by the solver).
- **Environment:** Linux x86_64 (htch-runtime 7.0.0-44-generic, 4 CPUs),
  g++ 13.3.0, `-O3 -std=c++17 -DNDEBUG`, Python 3.12.3.
- **Runner:** `scripts/run_dimacs_mis.py` — raw per-seed rows in
  `budget_<n>ms/dimacs_mis_runs.csv`, P10/P50/P90 summaries in
  `budget_<n>ms/dimacs_mis_summary.csv`. P10/P50/P90 describe
  variability across the five seeds; they are not confidence intervals
  and do not establish optimality.

## Results (MIS size, P50 across 5 seeds)

| Instance | n | Edges | 10 ms | 50 ms | 100 ms | 1000 ms |
|---|---:|---:|---:|---:|---:|---:|
| MANN_a9 | 45 | 918 | 3 | 3 | 3 | 3 |
| brock200_1 | 200 | 14834 | 6 | 6 | 6 | 6 |
| brock200_2 | 200 | 9876 | 10 | 10 | 10 | 10 |
| brock400_1 | 400 | 59723 | 6 | 6 | 6 | 6 |
| c-fat200-1 | 200 | 1534 | 18 | 18 | 18 | 18 |
| c-fat200-5 | 200 | 8473 | 3 | 3 | 3 | 3 |
| c-fat500-1 | 500 | 4459 | 40 | 40 | 40 | 40 |
| hamming8-4 | 256 | 20864 | 16 | 16 | 16 | 16 |
| keller4 | 171 | 9435 | 15 | 15 | 15 | 15 |
| p_hat300-1 | 300 | 10933 | 38 | 39 | 39 | 39 |
| p_hat300-2 | 300 | 21928 | 26 | 26 | 26 | 26 |
| p_hat300-3 | 300 | 33390 | 8 | 8 | 8 | 8 |
| san200_0.7_1 | 200 | 13930 | 7 | 7 | 7 | 7 |

## What the numbers do and do not say

- **Stability, not sensitivity:** 12 of 13 instances return the exact
  same size on all five seeds at every budget. Only `p_hat300-1`
  varies: mean 38.4 at 10 ms (P10 38, P50 38, P90 39), mean 38.8 at
  50/100 ms, and a stable 39 at 1000 ms. That is the whole seed
  variability in this run.
- **No budget effect beyond p_hat300-1:** raising the budget from
  10 ms to 1000 ms (100×) changes no other instance's result. Either
  the heuristic saturates immediately on these graphs, or the extra
  restarts find nothing better — this run cannot distinguish the two.
- **Plausibility check:** an independent pure-Python min-degree greedy
  (not MORPH code) gives the same sizes on the densest cases
  (c-fat200-5: 3, brock200_1: 6, keller4: up to 15), and MORPH beats it
  on MANN_a9 (3 vs 2). The small sizes on dense graphs are a property
  of the graphs, not a solver bug.
- **Wall-clock note:** at the 10 ms budget the measured wall time
  sometimes exceeds the budget (means up to ~33 ms, P90 up to ~65 ms
  on some instances; at 50 ms, means up to ~90 ms). The budget is a
  deadline for starting new restarts, not a hard cap: the first
  min-residual-degree pass runs to completion before the deadline is
  checked. At 100 ms and 1000 ms the wall time is the budget plus a
  few ms. Do not read the 10 ms column as "10 ms of work".
- **No comparison here:** this run measures MORPH alone. There is no
  CP-SAT (or other solver) column for DIMACS yet, so nothing here
  supports a claim of superiority over any other solver on DIMACS.

## Reproduce

```bash
make
python scripts/run_dimacs_mis.py \
  --dimacs-dir /path/to/dimacs-instances \
  --solver ./morph_qoblib_solver \
  --budget-ms 100 \
  --seeds 1,2,3,4,5 \
  --out results/dimacs_mis
```

The instance files themselves are not vendored in this repository;
download them from the source in `SOURCES.md` and verify against
`SHA256SUMS.txt`.
