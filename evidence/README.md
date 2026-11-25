# Evidence

- `scale_v1.5.csv` is the packaged synthetic scaling snapshot.
- `qoblib_6_instance_results.csv` is the earlier six-instance raw head-to-head CSV retained for provenance.
- `../scripts/run_qoblib_morph_cpsat.py` is the reproducible QOBLIB benchmark runner.
- `../scripts/run_dimacs_mis.py` is the reproducible DIMACS edge-format runner. It produces raw per-seed results and P10/P50/P90 summaries when run against at least ten documented instances.

The full 50-instance corrected QOBLIB run used during development is summarized in `../docs/RESULTS.md`. Its raw 2,000-row CSV was not present as a standalone artifact at packaging time, so it is not fabricated here.

- `dimacs_mis/` is the first measured DIMACS run (2026-11-23): 13 instances,
  5 seeds, budgets 10/50/100/1000 ms, 260 runs, all valid. Raw per-seed
  rows, P10/P50/P90 summaries and a per-budget report live under
  `dimacs_mis/budget_<n>ms/`; `dimacs_mis/README.md` states what the
  numbers do and do not support, and `dimacs_mis/SOURCES.md` records
  where the instance files came from. The instance files themselves are
  not vendored in this repository.
