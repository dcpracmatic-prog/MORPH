# Evidence

- `scale_v1.5.csv` is the packaged synthetic scaling snapshot.
- `qoblib_6_instance_results.csv` is the earlier six-instance raw head-to-head CSV retained for provenance.
- `../scripts/run_qoblib_morph_cpsat.py` is the reproducible QOBLIB benchmark runner.
- `../scripts/run_dimacs_mis.py` is the reproducible DIMACS edge-format runner. It produces raw per-seed results and P10/P50/P90 summaries when run against at least ten documented instances.

The full 50-instance corrected QOBLIB run used during development is summarized in `../docs/RESULTS.md`. Its raw 2,000-row CSV was not present as a standalone artifact at packaging time, so it is not fabricated here.

No DIMACS benchmark measurements are packaged yet. The presence of a runner is not evidence that those experiments have been executed.
