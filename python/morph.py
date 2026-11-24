"""MORPH in Python — ctypes wrapper, same pattern as HBAG (libhbag.so).

No hand-compiling: the first import builds ``libmorph.so`` from
``src/morph_api.cpp`` with the repo Makefile (``make libmorph``) if the
shared library is missing or older than the source.

Example (also runnable as ``python -m morph`` from the repo root)::

    from morph import solve_mis
    result = solve_mis("datasets/karate.gph", method="morph",
                       budget_ms=100, seed=1)
    result["size"]        # 20
    result["vertices"]    # [0, 2, 4, ...]  (0-based)
    result["valid"]       # True — checked again here, in Python

The independent set is returned explicitly so a notebook can verify it
against the graph instead of trusting a size number.
"""

from __future__ import annotations

import ctypes
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_LIB_PATH = _REPO_ROOT / "libmorph.so"
_API_SOURCE = _REPO_ROOT / "src" / "morph_api.cpp"
_SOLVER_SOURCE = _REPO_ROOT / "src" / "morph_qoblib_solver.cpp"

_METHODS = ("degree", "random", "local", "morph")


def _ensure_library() -> Path:
    sources = (_API_SOURCE, _SOLVER_SOURCE)  # libmorph.so is built from both
    newest_source = max(src.stat().st_mtime for src in sources)
    if _LIB_PATH.exists() and _LIB_PATH.stat().st_mtime >= newest_source:
        return _LIB_PATH
    print(f"[morph] building {_LIB_PATH.name} ...", file=sys.stderr)
    subprocess.run(["make", "libmorph"], cwd=_REPO_ROOT, check=True)
    return _LIB_PATH


_lib = ctypes.CDLL(str(_ensure_library()))
_lib.morph_solve.argtypes = [
    ctypes.c_char_p,  # graph_path
    ctypes.c_char_p,  # method
    ctypes.c_int,  # budget_ms
    ctypes.c_ulonglong,  # seed
    ctypes.POINTER(ctypes.c_int),  # out_num_vertices
    ctypes.POINTER(ctypes.c_int),  # out_num_edges
    ctypes.POINTER(ctypes.c_int),  # out_size
    ctypes.POINTER(ctypes.c_double),  # out_wall_ms
    ctypes.POINTER(ctypes.c_int),  # out_valid
    ctypes.POINTER(ctypes.c_int),  # out_vertices
    ctypes.c_int,  # out_vertices_capacity
]
_lib.morph_solve.restype = ctypes.c_int


def _read_graph_edges(graph_path: str | Path) -> set[tuple[int, int]]:
    """Edge set (0-based) of a .gph/.clq file, for the Python-side check."""
    edges: set[tuple[int, int]] = set()
    for raw in Path(graph_path).read_text(encoding="utf-8", errors="replace").splitlines():
        fields = raw.split()
        if len(fields) == 3 and fields[0] == "e":
            u, v = int(fields[1]) - 1, int(fields[2]) - 1
            edges.add((min(u, v), max(u, v)))
    return edges


def solve_mis(graph_path: str | Path, method: str = "morph",
              budget_ms: int = 100, seed: int = 1) -> dict:
    """Run MORPH on a graph file and return the independent set.

    Parameters
    ----------
    graph_path : DIMACS edge-format file (``p edge n m`` / ``e u v``).
    method : ``degree`` | ``random`` | ``local`` | ``morph``.
    budget_ms : time budget for ``morph`` (other methods ignore it).
    seed : fixed seed — the deterministic methods are bit-for-bit
        reproducible; ``morph`` also depends on wall-clock time, so its
        size can vary between runs at small budgets.

    Returns a dict with ``n``, ``edges``, ``size``, ``vertices`` (0-based),
    ``wall_ms``, ``valid`` (the C++ check) and ``valid_python`` (re-checked
    here, in Python, from the edge list).
    """
    if method not in _METHODS:
        raise ValueError(f"unknown method {method!r}, expected one of {_METHODS}")
    if budget_ms < 1:
        raise ValueError("budget_ms must be positive")

    n = ctypes.c_int(0)
    edges = ctypes.c_int(0)
    size = ctypes.c_int(0)
    wall_ms = ctypes.c_double(0.0)
    valid = ctypes.c_int(0)
    # The independent set can hold at most n vertices; read n from the
    # file header first so the buffer is exactly sized.
    header_n = None
    for raw in Path(graph_path).read_text(encoding="utf-8", errors="replace").splitlines():
        fields = raw.split()
        if len(fields) == 4 and fields[0] == "p":
            header_n = int(fields[2])
            break
    if header_n is None:
        raise ValueError(f"no 'p edge n m' line in {graph_path}")
    vertices = (ctypes.c_int * header_n)()

    code = _lib.morph_solve(
        str(graph_path).encode(), method.encode(), budget_ms, seed,
        ctypes.byref(n), ctypes.byref(edges), ctypes.byref(size),
        ctypes.byref(wall_ms), ctypes.byref(valid),
        vertices, header_n,
    )
    if code == 2:
        raise ValueError(f"unknown method {method!r}")
    if code == 3:
        raise FileNotFoundError(f"cannot open graph: {graph_path}")
    if code == -1:
        raise RuntimeError("solver returned a set larger than the vertex buffer")
    if code != 0:
        raise RuntimeError(f"morph_solve failed with code {code}")

    chosen = sorted(vertices[i] for i in range(size.value))
    edge_set = _read_graph_edges(graph_path)
    chosen_set = set(chosen)
    valid_python = all(
        not (u in chosen_set and v in chosen_set) for u, v in edge_set
    )
    return {
        "graph": str(graph_path),
        "method": method,
        "budget_ms": budget_ms,
        "seed": seed,
        "n": n.value,
        "edges": edges.value,
        "size": size.value,
        "vertices": chosen,
        "wall_ms": wall_ms.value,
        "valid": bool(valid.value),
        "valid_python": valid_python,
    }


if __name__ == "__main__":
    for dataset in ("datasets/karate.gph", "datasets/football.gph",
                    "datasets/kangaroo.gph"):
        result = solve_mis(_REPO_ROOT / dataset, method="morph",
                           budget_ms=100, seed=1)
        print(f"{dataset}: MIS size {result['size']} "
              f"(valid C++={result['valid']}, valid Python={result['valid_python']}) "
              f"in {result['wall_ms']:.1f} ms")
        print(f"  vertices (0-based): {result['vertices']}")
