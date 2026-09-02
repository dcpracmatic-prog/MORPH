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
