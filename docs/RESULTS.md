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

## DIMACS (measured 2026-11-24)

41 DIMACS clique-benchmark graphs, seeds 1–5, budgets 10/50/100/1000 ms,
both conventions, 1,640 runs, all flagged valid by the solver (the solver's
own check; no separate checker). Full per-instance table with ω and
[min–max] over seeds: `evidence/dimacs_mis/COMBINED_TABLE.md`. Provenance
and checksums: `evidence/dimacs_mis/SOURCES.md`.

Two conventions, reported side by side:

- **complement** (MIS of the complement = clique number of the original):
  comparable to published ω. At 1000 ms, 15 of 35 instances with exact ω reach
  ω on all five seeds. Five instances whose published value is only a lower
  bound come out below it (p_hat1000-1, p_hat1000-2, p_hat1000-3, p_hat500-3,
  p_hat700-2).
- **as-is** (MIS of the file's graph): a different quantity, not compared with ω.
  Included because PR #2 and the QOBLIB MIS runs used this convention.

Large gaps to ω exist on several families at 1000 ms, for example
san200_0.9_1 52 vs 70, san400_0.7_1 23 vs 40, brock400_4 23 vs 33, san1000 10 vs 15.

Only a few instances vary across seeds or budgets; see
`evidence/dimacs_mis/README.md`. Budgets are deadlines for starting restarts,
not hard caps: mean wall time is 10.9 ms at a 10 ms budget (worst instance
mean 17.0 ms). No competing solver was run on DIMACS, so these results
support no superiority claim.
