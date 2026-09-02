# Validation policy

1. Every heuristic solution must satisfy the independent-set invariant.
2. Official QOBLIB references are parsed from the repository rather than copied into the solver.
3. `OPTIMAL` and `BEST_KNOWN` references are kept distinct.
4. CP-SAT `UNKNOWN` without an incumbent is represented as no incumbent, not objective zero.
5. Comparisons use identical wall-clock budgets and five seeds.
6. CP-SAT uses one search worker.
7. Synthetic BA results are explicitly labeled synthetic and are not used as real-world optimality evidence.
