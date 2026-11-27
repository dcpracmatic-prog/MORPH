# MORPH

**A low-latency heuristic for the Maximum Independent Set (MIS) problem.**

[![CI](https://github.com/dcpracmatic-prog/MORPH/actions/workflows/ci.yml/badge.svg)](https://github.com/dcpracmatic-prog/MORPH/actions/workflows/ci.yml)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)

MORPH builds large feasible independent sets quickly using a residual-degree construction, compact CSR graph storage, and a lazy min-heap. It is designed for time-limited graph optimization—not as an exact solver or a universal replacement for CP-SAT.

## At a glance

- **Problem:** Maximum Independent Set (MIS)
- **Implementation:** C++17, with an optional Python `ctypes` wrapper
- **Approach:** repeatedly choose an active vertex with minimum residual degree, add it to the solution, then remove it and its active neighbors
- **Validation:** returned sets are checked for independence in C++; the Python wrapper checks them again
- **Benchmarks:** QOBLIB comparisons, DIMACS experiments, and synthetic Barabási–Albert scaling results

An independent set contains no pair of adjacent vertices. MORPH returns a feasible set; its size is a heuristic result and is not guaranteed to be optimal.

## Quick start

### Requirements

- A Linux-like environment with `g++` (or another compatible C++17 compiler) and `make`
- Python 3.10 or newer for the test suite and Python wrapper

Build the command-line solvers and run the smoke test:

```bash
git clone https://github.com/dcpracmatic-prog/MORPH.git
cd MORPH
make
bash scripts/smoke_test.sh
```

Run the full project test target:

```bash
make test
```

The smoke test runs the solver on the bundled `.gph` examples and checks its validity flag. `make test` also runs the C++ and Python tests.

## Use from Python

Build the shared library and run the included example:

```bash
make libmorph
PYTHONPATH=python python -m morph
```

Or run your own script from the repository root with `PYTHONPATH=python python your_script.py`:

```python
from morph import solve_mis

result = solve_mis(
    "datasets/karate.gph",
    method="morph",
    budget_ms=100,
    seed=1,
)

print(result["size"])
print(result["vertices"])       # zero-based vertex IDs
print(result["valid_python"])   # independent-set check in Python
```

`solve_mis` accepts DIMACS edge-format input (`p edge n m` and `e u v` records). Available methods are `degree`, `random`, `local`, and `morph`. The time budget applies to `morph`; deterministic baselines do not use it. Small-budget `morph` runs can vary because the search also depends on wall-clock time.

## Benchmarks and evidence

Benchmark results are reported with their protocol and limitations; they should not be read as proof of optimality or general superiority.

### QOBLIB

Compare MORPH with OR-Tools CP-SAT on discovered QOBLIB MIS instances:

```bash
python scripts/run_qoblib_morph_cpsat.py \
  --qoblib /path/to/QOBLIB \
  --out results/qoblib_morph_vs_cpsat.csv \
  --solver ./morph_qoblib_solver
```

This benchmark requires Git, Python with `pip`, and OR-Tools. The runner attempts to install OR-Tools if it is missing and clones QOBLIB if the supplied path does not exist. The default protocol uses all discovered instances, budgets of 10, 50, 100, and 1000 ms, five seeds, and both solvers. CP-SAT uses one worker and the same wall-clock limit. Runs without a feasible incumbent are recorded explicitly rather than assigned an artificial objective of zero.

Validate results against the official QOBLIB `.opt.sol` and `.bst.sol` references:

```bash
python scripts/validate_absolute_quality.py \
  --results results/qoblib_morph_vs_cpsat.csv \
  --out results/absolute_quality
```

The validator distinguishes `OPTIMAL` from `BEST_KNOWN`: matching a best-known value is not an independent proof of optimality. It is Colab-oriented and creates `/content/morph_qoblib_absolute` by default. **Use a disposable QOBLIB checkout:** when a Git checkout is present at its QOBLIB path, the script attempts `git fetch` and `git reset --hard origin/main`, potentially discarding local changes. Its independent set checks apply to the reference solutions; the benchmark CSV contains objectives, not MORPH vertex lists.

### DIMACS

The runner accepts DIMACS edge-format instances with a `p edge n m` header and `e u v` edges. It requires at least ten instances and five distinct seeds, and writes per-seed results, per-instance P10/P50/P90 summaries, and a Markdown report.

```bash
python scripts/run_dimacs_mis.py \
  --dimacs-dir /path/to/dimacs-instances \
  --solver ./morph_qoblib_solver \
  --budget-ms 100 \
  --seeds 1,2,3,4,5 \
  --out results/dimacs_mis
```

The recorded experiment and its interpretation are in [`evidence/dimacs_mis/README.md`](evidence/dimacs_mis/README.md). It covers 41 DIMACS clique-benchmark graphs, five seeds, four budgets, and both the original and complement graph conventions. The complement convention is relevant when comparing MIS results with published clique numbers. The run has no competing solver column, so it does not support a comparative-superiority claim. Percentiles over five seeds are descriptive, not confidence intervals; the published reference values were not independently checked against the original DIMACS files.

### Scaling experiment

The v1.5 residual-degree construction improved solution quality by approximately 7.2–7.5% over degree-greedy in the repository's synthetic Barabási–Albert stress tests across 32,768 to 1,048,576 vertices. These are synthetic comparisons, not optimality results. See [`evidence/`](evidence/) for the available records.

## Repository map

| Path | Purpose |
| --- | --- |
| `src/morph_v15.cpp` | Scalable v1.5 implementation and synthetic scaling harness |
| `src/morph_qoblib_solver.cpp` | Budgeted solver used by benchmark scripts |
| `src/morph_api.cpp` | C API used to build the Python shared library |
| `python/morph.py` | Python wrapper and example entry point |
| `scripts/` | Benchmark, validation, and smoke-test scripts |
| `tests/` | C++ and Python tests |
| `datasets/` | Small graph examples used in development and smoke tests |
| `evidence/` | Recorded benchmark evidence and supporting reports |
| `docs/` | Validation notes and project results |

## Reproducibility and limitations

Wall-clock budgets are not equivalent to equal CPU-cycle budgets. Record the hardware, compiler, OR-Tools version, solver settings, seed, and budget when producing new measurements. The MORPH search budget is a deadline for starting new restarts, not a strict cap on total process wall time. Benchmark results also depend on the graph convention: MIS on an input graph and MIS on its complement are different problems.

MORPH is a low-latency heuristic for MIS. The repository does **not** establish exactness, exponential speedups, quantum resistance, or universal superiority over other solvers.

## License

MORPH is distributed under the [GNU General Public License v3.0](LICENSE).
