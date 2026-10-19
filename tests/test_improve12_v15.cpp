#define main morph_v15_cli_main
#include "../src/morph_v15.cpp"
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
    Sol s; s.x = {1, 0, 0}; s.size = 1;
    improve12(g, s);
    if (s.size != 2 || !valid(g, s)) return 1;
    auto tri = graph3(true);
    Sol t; t.x = {1, 0, 0}; t.size = 1;
    improve12(tri, t);
    if (t.size != 1 || !valid(tri, t)) return 2;
    cout << "improve12 v1.5 regression: PASS\n";
}