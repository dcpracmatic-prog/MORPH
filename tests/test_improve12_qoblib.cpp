#define main morph_qoblib_cli_main
#include "../src/morph_qoblib_solver.cpp"
#undef main

static Graph graph3(bool triangle) {
    Graph g;
    g.n = 3;
    if (triangle) {
        g.off = {0, 2, 4, 6};
        g.adj = {1, 2, 0, 2, 0, 1};
        g.deg = {2, 2, 2};
    } else {
        g.off = {0, 2, 3, 4};
        g.adj = {1, 2, 0, 0};
        g.deg = {2, 1, 1};
    }
    return g;
}
int main() {
    auto g = graph3(false);
    Solution s; s.x = {1, 0, 0}; s.size = 1;
    improve_1_to_2(g, s);
    if (s.size != 2 || !valid(g, s)) return 1;
    auto tri = graph3(true);
    Solution t; t.x = {1, 0, 0}; t.size = 1;
    improve_1_to_2(tri, t);
    if (t.size != 1 || !valid(tri, t)) return 2;
    cout << "QOBLIB 1-to-2 regression: PASS\n";
}