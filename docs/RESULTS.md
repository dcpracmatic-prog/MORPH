# Results snapshot

## Synthetic scaling

| n | edges | degree-greedy | random-degree | MORPH v1.5 |
|---:|---:|---:|---:|---:|
| 32,768 | 163,825 | 12,593 | 12,579 | **13,494** |
| 65,536 | 327,665 | 25,117 | 25,090 | **26,939** |
| 131,072 | 655,345 | 50,115 | 50,059 | **53,819** |
| 262,144 | 1,310,705 | 100,352 | 100,241 | **107,771** |
| 524,288 | 2,621,425 | 200,750 | 200,579 | **215,659** |
| 1,048,576 | 5,242,865 | 401,670 | 401,357 | **431,645** |

The MORPH advantage over degree-greedy is approximately 7.2–7.5% across this synthetic family. No global optimum is known for these BA graphs.

## QOBLIB / CP-SAT

The corrected full-run protocol covered the QOBLIB MIS set used in the validation session: 50 instances, four budgets (10/50/100/1000 ms), five seeds, and MORPH vs CP-SAT, for 2,000 executions.

Representative observations from that run:

- `C125-9`: MORPH reached 34, the official optimum, at 10 ms; CP-SAT had no incumbent at 10 ms.
- `brock200-1`: MORPH returned 6 across the tested budgets; CP-SAT reached lower incumbents under the same short budgets.
- `C4000-5`: the official reference is 18 (BEST_KNOWN); MORPH's best observed value in the absolute-quality validation was 15, so this is not an optimality result.
- `R_500_005_1` and `R_1000_005_1`: MORPH produced useful incumbents quickly while CP-SAT frequently had no incumbent in the tested short budgets.
- Large social/benchmark instances such as `socfb-haverford76` and `socfb-trinity100` also produced MORPH incumbents where CP-SAT did not within 1 s in the reported run.

These observations justify the low-latency heuristic thesis, not a claim of universal solver dominance.

## DIMACS (measured 2026-11-23)

13 instances, 5 seeds, budgets 10/50/100/1000 ms, 260 runs, all valid.
Full raw rows, P10/P50/P90 summaries and provenance: `evidence/dimacs_mis/`.

P50 MIS size at 100 ms: MANN_a9 3, brock200_1 6, brock200_2 10,
brock400_1 6, c-fat200-1 18, c-fat200-5 3, c-fat500-1 40, hamming8-4 16,
keller4 15, p_hat300-1 39, p_hat300-2 26, p_hat300-3 8, san200_0.7_1 7.

Only p_hat300-1 varies across seeds (38 at 10 ms, 39 from 50 ms up).
No budget from 10 ms to 1000 ms changes any other instance. The `.clq`
files are clique-benchmark graphs used as-is as MIS instances, so
published maximum-clique optima do not apply. No competing solver was
run on DIMACS, so this supports no superiority claim. At the 10 ms
budget the measured wall time sometimes exceeds the budget (first
min-residual-degree pass runs to completion before the deadline is
checked).
