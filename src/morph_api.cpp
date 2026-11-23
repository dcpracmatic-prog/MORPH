// MORPH C API — shared-library entry point for the Python wrapper
// (python/morph.py, ctypes, same pattern as HBAG's libhbag.so).
//
// This file does NOT change the solver. It includes
// morph_qoblib_solver.cpp with its `main` renamed (the same trick the
// regression tests in tests/ already use) and exposes one C function,
// `morph_solve`, that runs a method and returns the independent set
// itself — not just its size — so a notebook can check it in Python.
//
// Build:  make libmorph        (produces libmorph.so next to the Makefile)
// Return value: 0 on success, 2 for a bad method name, 3 if the graph
// file cannot be opened (load_graph throws), -1 if `out_vertices` is
// null while the solution is non-empty.

#define main morph_qoblib_cli_main
#include "morph_qoblib_solver.cpp"
#undef main

#include <chrono>
#include <cstring>

extern "C" int morph_solve(const char* graph_path, const char* method,
                           int budget_ms, unsigned long long seed,
                           int* out_num_vertices, int* out_num_edges,
                           int* out_size, double* out_wall_ms,
                           int* out_valid, int* out_vertices,
                           int out_vertices_capacity) {
    // load_graph throws runtime_error on a missing file; catch it here
    // so the exception never crosses the C boundary into Python.
    try {
    Graph graph = load_graph(graph_path);
    std::string method_name = method ? method : "";

    auto start = std::chrono::steady_clock::now();
    Solution solution;

    if (method_name == "degree") {
        solution = greedy(graph, degree_order(graph, 0));
    } else if (method_name == "random") {
        solution = greedy(graph, degree_order(graph, seed));
    } else if (method_name == "local") {
        solution = greedy(graph, degree_order(graph, seed));
        improve_1_to_2(graph, solution);
    } else if (method_name == "morph") {
        solution = morph(graph, seed, budget_ms);
    } else {
        return 2;  // unknown method
    }

    auto end = std::chrono::steady_clock::now();
    double wall_ms =
        std::chrono::duration<double, std::milli>(end - start).count();

    if (out_num_vertices) *out_num_vertices = graph.n;
    if (out_num_edges) *out_num_edges = (int)(graph.adj.size() / 2);
    if (out_size) *out_size = solution.size;
    if (out_wall_ms) *out_wall_ms = wall_ms;
    if (out_valid) *out_valid = valid(graph, solution) ? 1 : 0;

    if (solution.size > 0) {
        if (!out_vertices || out_vertices_capacity < solution.size) {
            return -1;
        }
        int written = 0;
        for (int v = 0; v < graph.n; ++v) {
            if (solution.x[v]) out_vertices[written++] = v;
        }
    }
    return 0;
    } catch (...) {
        return 3;  // graph file cannot be opened / parsed
    }
}
