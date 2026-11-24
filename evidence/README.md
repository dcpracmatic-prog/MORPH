# Evidence

- `scale_v1.5.csv` is the packaged synthetic scaling snapshot.
- `qoblib_6_instance_results.csv` is the earlier six-instance raw head-to-head CSV retained for provenance.
- `../scripts/run_qoblib_morph_cpsat.py` is the reproducible QOBLIB benchmark runner.
- `../scripts/run_dimacs_mis.py` is the reproducible DIMACS edge-format runner. It produces raw per-seed results and P10/P50/P90 summaries when run against at least ten documented instances.

The full 50-instance corrected QOBLIB run used during development is summarized in `../docs/RESULTS.md`. Its raw 2,000-row CSV was not present as a standalone artifact at packaging time, so it is not fabricated here.

- `dimacs_mis/` is the measured DIMACS run (2026-11-24): 41 instances,
  5 seeds, budgets 10/50/100/1000 ms, two conventions (as-is and
  complement), 1,640 runs, all flagged valid by the solver. Raw per-seed rows,
  P10/P50/P90 and min/max summaries, and per-budget reports live under
  `dimacs_mis/{as-is,complement}/budget_<n>ms/`. `dimacs_mis/README.md` states
  what the numbers do and do not support; `dimacs_mis/SOURCES.md` records
  where the instance files came from and how the ω reference was obtained.
  The instance files themselves are not vendored in this repository.
- `dimacs_mis/superseded_13_instance_run/` is the earlier 13-instance run. It is kept for history and is not to be cited as current.
