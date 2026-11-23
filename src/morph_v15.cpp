// MORPH v1.5 — Maximum Independent Set (MIS), low-latency heuristic.
//
// The core construction repeatedly picks an active vertex of minimum
// residual degree, adds it to the independent set, and removes it and its
// active neighbours. On top of that, `morph` runs time-budgeted restarts
// with randomized degree orders, a small perturbation and a repair pass,
// and finishes with a 1-to-2 local improvement (`improve12`).
//
// This file is a reformat of the original v1.5 source: same function names,
// same struct fields (the tests include this file directly), same logic.
// Only layout, local names and comments changed. One fix: `main` now
// returns 0 explicitly (the old version fell off the end, which GCC
// warned about with -Wreturn-type).
//
// Graph layout (CSR):
//   n   — number of vertices (0-based inside the program; files are 1-based)
//   off — offsets into `adj`; neighbours of v are adj[off[v] .. off[v+1])
//   adj — concatenated neighbour lists
//   deg — degree of each vertex (static, from the input graph)

#include <bits/stdc++.h>
#include <sys/resource.h>
using namespace std;

struct Graph {
    int n;
    vector<int> off, adj;
    vector<int> deg;
};

// splitmix64: fast deterministic 64-bit mixer. Used to derive per-vertex
// tie-break keys from a seed, so runs are reproducible for a fixed seed.
static uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

// Load a graph in .gph format: tokens `p edge n m` and `e u v` (1-based).
// Any other token is skipped, exactly as in the original loader.
Graph load_gph(const string& path) {
    ifstream in(path);
    string token;
    int num_vertices = 0, num_edges = 0;
    vector<pair<int, int>> edges;

    while (in >> token) {
        if (token == "p") {
            string format;
            in >> format >> num_vertices >> num_edges;
            edges.reserve(num_edges);
        } else if (token == "e") {
            int u, v;
            in >> u >> v;
            --u;
            --v;  // files are 1-based, the program is 0-based
            edges.push_back({u, v});
        }
    }

    Graph graph;
    graph.n = num_vertices;
    graph.deg.assign(num_vertices, 0);
    graph.off.assign(num_vertices + 1, 0);

    // First pass: count degrees and CSR offsets.
    for (auto [u, v] : edges) {
        graph.deg[u]++;
        graph.deg[v]++;
        graph.off[u + 1]++;
        graph.off[v + 1]++;
    }
    for (int i = 0; i < num_vertices; i++) {
        graph.off[i + 1] += graph.off[i];
    }

    // Second pass: fill the adjacency lists.
    graph.adj.resize(graph.off[num_vertices]);
    auto cursor = graph.off;
    for (auto [u, v] : edges) {
        graph.adj[cursor[u]++] = v;
        graph.adj[cursor[v]++] = u;
    }
    return graph;
}

// Barabási–Albert random graph, for the synthetic scaling harness.
// Starts from a clique of `initial_clique_size` vertices; each new vertex
// attaches to `edges_per_new_vertex` earlier vertices, chosen with
// probability proportional to their current degree. `targets` is the
// preferential-attachment list: every vertex appears in it once per
// incident edge, so picking a uniform entry picks a vertex with
// probability proportional to its degree. `seed` makes the graph
// reproducible; the edge order follows the iteration order of the
// unordered set, as in the original code.
Graph ba_graph(int num_vertices, int initial_clique_size,
               int edges_per_new_vertex, uint64_t seed) {
    vector<pair<int, int>> edges;
    edges.reserve((size_t)num_vertices * edges_per_new_vertex);
    vector<int> degree(num_vertices);
    vector<int> targets;
    targets.reserve((size_t)num_vertices * edges_per_new_vertex * 2);
    mt19937_64 rng(seed);

    // Initial clique.
    for (int i = 0; i < initial_clique_size; i++) {
        for (int j = i + 1; j < initial_clique_size; j++) {
            edges.push_back({i, j});
            degree[i]++;
            degree[j]++;
            targets.push_back(i);
            targets.push_back(j);
        }
    }

    // Grow the graph one vertex at a time.
    for (int v = initial_clique_size; v < num_vertices; v++) {
        unordered_set<int> chosen_neighbours;
        chosen_neighbours.reserve(edges_per_new_vertex * 2);
        while ((int)chosen_neighbours.size() < edges_per_new_vertex) {
            int u = targets[rng() % targets.size()];
            if (u != v) {
                chosen_neighbours.insert(u);
            }
        }
        for (int u : chosen_neighbours) {
            edges.push_back({u, v});
            degree[u]++;
            degree[v]++;
            targets.push_back(u);
            targets.push_back(v);
        }
    }

    // Same CSR build as load_gph, from the generated edge list.
    Graph graph;
    graph.n = num_vertices;
    graph.deg = degree;
    graph.off.assign(num_vertices + 1, 0);
    for (auto [u, v] : edges) {
        graph.off[u + 1]++;
        graph.off[v + 1]++;
    }
    for (int i = 0; i < num_vertices; i++) {
        graph.off[i + 1] += graph.off[i];
    }
    graph.adj.resize(graph.off[num_vertices]);
    vector<int> cursor = graph.off;
    for (auto [u, v] : edges) {
        graph.adj[cursor[u]++] = v;
        graph.adj[cursor[v]++] = u;
    }
    return graph;
}

struct Sol {
    int size = 0;
    vector<uint8_t> x;  // x[v] == 1 iff v is in the independent set
};

// Greedy construction: scan vertices in the given order and take a vertex
// whenever none of its neighbours is already taken.
Sol greedy(const Graph& graph, const vector<int>& order) {
    Sol solution;
    solution.x.assign(graph.n, 0);
    for (int v : order) {
        bool can_add = true;
        for (int p = graph.off[v]; p < graph.off[v + 1]; p++) {
            if (solution.x[graph.adj[p]]) {
                can_add = false;
                break;
            }
        }
        if (can_add) {
            solution.x[v] = 1;
            solution.size++;
        }
    }
    return solution;
}

// Vertices sorted by increasing static degree (ties by vertex id).
vector<int> degree_order(const Graph& graph) {
    vector<int> order(graph.n);
    iota(order.begin(), order.end(), 0);
    stable_sort(order.begin(), order.end(), [&](int a, int b) {
        if (graph.deg[a] != graph.deg[b]) {
            return graph.deg[a] < graph.deg[b];
        }
        return a < b;
    });
    return order;
}

// Same order, but ties are broken by a per-vertex key derived from `seed`,
// so different seeds give different (still degree-first) orders.
vector<int> random_degree_order(const Graph& graph, uint64_t seed) {
    vector<int> order(graph.n);
    iota(order.begin(), order.end(), 0);
    vector<uint32_t> tie_key(graph.n);
    for (int i = 0; i < graph.n; i++) {
        tie_key[i] = (uint32_t)splitmix64(seed + i);
    }
    stable_sort(order.begin(), order.end(), [&](int a, int b) {
        uint64_t key_a = ((uint64_t)graph.deg[a] << 32) | tie_key[a];
        uint64_t key_b = ((uint64_t)graph.deg[b] << 32) | tie_key[b];
        return key_a < key_b;
    });
    return order;
}

// Local search: attempt a valid 1-to-2 exchange. Both unselected vertices
// must have exactly one selected neighbour (the same u), and must not be
// adjacent to each other. Removing u and adding both of them grows the
// independent set by one.
//
// Two passes over the candidates are intentional: the first pass collects
// every vertex with exactly one selected neighbour (capped at `maxv`);
// the second pass groups those candidates by their single selected
// neighbour, so a pair sharing the same u can be found. At most one
// exchange is applied per call; the caller may invoke again.
void improve12(const Graph& g, Sol& s, int maxv = 5000) {
    vector<int> candidates;
    candidates.reserve(min(maxv, g.n));

    for (int v = 0; v < g.n; ++v) {
        if (s.x[v]) continue;
        int selected = -1, count = 0;
        for (int p = g.off[v]; p < g.off[v + 1]; ++p) {
            int u = g.adj[p];
            if (s.x[u]) {
                selected = u;
                ++count;
            }
            if (count > 1) break;
        }
        if (count == 1) candidates.push_back(v);
    }
    if ((int)candidates.size() > maxv) candidates.resize(maxv);

    vector<vector<int>> by_selected(g.n);
    for (int v : candidates) {
        int u = -1, count = 0;
        for (int p = g.off[v]; p < g.off[v + 1]; ++p) {
            int z = g.adj[p];
            if (s.x[z]) {
                u = z;
                ++count;
            }
        }
        if (count == 1) by_selected[u].push_back(v);
    }

    // `adjacent[w] == 1` while v is being examined means w is a neighbour
    // of v (or v itself is never in the list, so it is not marked).
    vector<uint8_t> adjacent(g.n, 0);
    for (int u = 0; u < g.n; ++u) {
        if (by_selected[u].size() < 2) continue;
        for (int v : by_selected[u]) {
            for (int p = g.off[v]; p < g.off[v + 1]; ++p) {
                adjacent[g.adj[p]] = 1;
            }
            for (int w : by_selected[u]) {
                if (v == w || adjacent[w]) continue;
                s.x[u] = 0;
                s.x[v] = 1;
                s.x[w] = 1;
                ++s.size;
                return;  // One exchange per call; caller may invoke again.
            }
            for (int p = g.off[v]; p < g.off[v + 1]; ++p) {
                adjacent[g.adj[p]] = 0;
            }
        }
    }
}

// Time-budgeted MORPH: repeat until the deadline, then improve once.
// Every fourth iteration reuses the deterministic degree order; the
// others use a fresh randomized degree order derived from the seed and
// the iteration number. Each candidate is perturbed (a small deterministic
// sample of selected vertices is removed) and then repaired by scanning
// vertices in the same order and re-adding any vertex whose neighbours
// are all unselected. The best candidate seen is kept.
//
// Note: the result depends on wall-clock time, so two runs with the same
// seed can differ in size when the budget allows a different number of
// iterations. Only the deterministic pieces (greedy, minres, improve12)
// are bit-for-bit reproducible.
Sol morph(const Graph& graph, uint64_t seed, int budget_ms) {
    auto start = chrono::steady_clock::now();
    auto deadline = start + chrono::milliseconds(budget_ms);

    auto base_order = degree_order(graph);
    Sol best = greedy(graph, base_order);

    vector<int> order(graph.n);
    vector<int> selected;
    int iteration = 0;

    while (chrono::steady_clock::now() < deadline) {
        uint64_t round_key = splitmix64(seed + iteration++);
        const vector<int>* current_order = &base_order;
        if ((iteration & 3) != 0) {
            order = random_degree_order(graph, round_key);
            current_order = &order;
        }

        Sol candidate = greedy(graph, *current_order);

        // Perturb: remove a small deterministic sample from the selected
        // solution, then repair with the same order (see below).
        if (candidate.size > 100) {
            int to_remove = max(1, min(candidate.size / 50, 2000));
            selected.clear();
            for (int v = 0; v < graph.n; v++) {
                if (candidate.x[v]) selected.push_back(v);
            }
            for (int j = 0; j < to_remove; j++) {
                int k = (int)(splitmix64(round_key + j) % selected.size());
                swap(selected[k], selected.back());
                int v = selected.back();
                selected.pop_back();
                candidate.x[v] = 0;
                candidate.size--;
            }
        }

        // Repair: scan vertices in the (randomized) degree order and
        // re-add any vertex whose neighbours are all unselected.
        for (int v : *current_order) {
            if (candidate.x[v]) continue;
            bool can_add = true;
            for (int p = graph.off[v]; p < graph.off[v + 1]; p++) {
                if (candidate.x[graph.adj[p]]) {
                    can_add = false;
                    break;
                }
            }
            if (can_add) {
                candidate.x[v] = 1;
                candidate.size++;
            }
        }

        if (candidate.size > best.size) {
            best = candidate;
        }
    }

    improve12(graph, best);
    return best;
}

// Minimum residual degree construction: repeatedly take the active vertex
// of smallest residual degree (degree counting only active neighbours),
// using a lazy min-heap — stale heap entries are skipped by comparing
// the stored degree with the current residual degree. Taking a vertex
// removes it and all its neighbours, which lowers the residual degree
// of the neighbours' neighbours.
Sol minres(const Graph& graph) {
    int n = graph.n;
    vector<int> residual_degree = graph.deg;
    vector<uint8_t> alive(n, 1), in_set(n, 0);
    priority_queue<pair<int, int>, vector<pair<int, int>>,
                   greater<pair<int, int>>>
        heap;
    for (int i = 0; i < n; i++) {
        heap.push({residual_degree[i], i});
    }

    int size = 0;
    while (!heap.empty()) {
        auto [degree, v] = heap.top();
        heap.pop();
        if (!alive[v] || degree != residual_degree[v]) continue;  // stale entry

        in_set[v] = 1;
        size++;
        alive[v] = 0;

        for (int p = graph.off[v]; p < graph.off[v + 1]; p++) {
            int u = graph.adj[p];
            if (!alive[u]) continue;
            alive[u] = 0;  // neighbour of a selected vertex: removed
            for (int q = graph.off[u]; q < graph.off[u + 1]; q++) {
                int w = graph.adj[q];
                if (alive[w]) {
                    residual_degree[w]--;
                    heap.push({residual_degree[w], w});
                }
            }
        }
    }
    return Sol{size, move(in_set)};
}

// Check that no two selected vertices are adjacent.
bool valid(const Graph& graph, const Sol& solution) {
    for (int v = 0; v < graph.n; v++) {
        if (!solution.x[v]) continue;
        for (int p = graph.off[v]; p < graph.off[v + 1]; p++) {
            if (solution.x[graph.adj[p]]) return false;
        }
    }
    return true;
}

// Usage:
//   morph_v15 ba [n] [budget_ms] [seed]   — synthetic BA graph (default n=65536)
//   morph_v15 <file.gph> [budget_ms] [seed]
// Output (one CSV line): source,n,edges,degree_greedy,random_degree,
// improved_random_degree,minres,rss_mb,elapsed_ms,valid_flags
// The trailing valid flags are one digit (0/1) per method, in the same
// order as the four sizes. Elapsed time and RSS vary run to run; the
// four sizes are deterministic for a fixed seed and graph.
int main(int argc, char** argv) {
    string source = argc > 1 ? argv[1] : "ba";
    int num_vertices = 0, budget_ms = 100;
    uint64_t seed = 1;
    Graph graph;

    if (source == "ba") {
        num_vertices = argc > 2 ? atoi(argv[2]) : 65536;
        budget_ms = argc > 3 ? atoi(argv[3]) : 100;
        seed = argc > 4 ? strtoull(argv[4], 0, 10) : 1;
        graph = ba_graph(num_vertices, 5, 5, seed);
    } else {
        budget_ms = argc > 2 ? atoi(argv[2]) : 100;
        seed = argc > 3 ? strtoull(argv[3], 0, 10) : 1;
        graph = load_gph(source);
        num_vertices = graph.n;
    }

    auto start_time = chrono::steady_clock::now();
    auto degree_ordered = degree_order(graph);
    auto degree_greedy = greedy(graph, degree_ordered);
    auto random_ordered = random_degree_order(graph, seed + 99);
    auto random_greedy = greedy(graph, random_ordered);
    auto improved = random_greedy;
    improve12(graph, improved);
    auto minres_solution = minres(graph);
    auto end_time = chrono::steady_clock::now();

    struct rusage resource_usage {};
    getrusage(RUSAGE_SELF, &resource_usage);
    double rss_mb = resource_usage.ru_maxrss / 1024.0;

    cout << source << "," << num_vertices << "," << graph.adj.size() / 2
         << "," << degree_greedy.size << "," << random_greedy.size << ","
         << improved.size << "," << minres_solution.size << "," << rss_mb
         << "," << chrono::duration<double, milli>(end_time - start_time).count()
         << "," << valid(graph, degree_greedy) << valid(graph, random_greedy)
         << valid(graph, improved) << valid(graph, minres_solution) << "\n";
    return 0;
}
