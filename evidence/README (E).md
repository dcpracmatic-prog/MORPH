# Evidence

`scale_v1.5.csv` is the packaged synthetic scaling snapshot.

`qoblib_6_instance_results.csv` is the earlier six-instance raw head-to-head CSV retained for provenance. The reproducible current benchmark is `scripts/run_qoblib_morph_cpsat.py`, which discovers the complete QOBLIB MIS instance set and writes a new raw CSV.

The full 50-instance corrected run used during development is summarized in `docs/RESULTS.md`. Its raw 2,000-row CSV was not present as a standalone artifact at packaging time, so it is not fabricated here.
