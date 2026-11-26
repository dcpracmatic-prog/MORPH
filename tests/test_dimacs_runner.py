import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_dimacs_mis.py"
SPEC = importlib.util.spec_from_file_location("run_dimacs_mis", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DimacsRunnerTests(unittest.TestCase):
    def test_parse_dimacs_edge_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tiny.clq"
            path.write_text("c tiny graph\np edge 3 2\ne 1 2\ne 1 3\n", encoding="utf-8")
            self.assertEqual(MODULE.parse_dimacs(path), (3, 2))

    def test_rejects_declared_edge_count_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.clq"
            path.write_text("p edge 3 2\ne 1 2\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                MODULE.parse_dimacs(path)

    def test_percentiles_for_five_seed_values(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertAlmostEqual(MODULE.percentile(values, 10), 1.4)
        self.assertAlmostEqual(MODULE.percentile(values, 50), 3.0)
        self.assertAlmostEqual(MODULE.percentile(values, 90), 4.6)

    def test_median_interval_coverage_for_five_seeds(self):
        self.assertAlmostEqual(MODULE.median_interval_coverage(5), 0.9375)


COMPLEMENT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "complement_dimacs.py"
COMPLEMENT_SPEC = importlib.util.spec_from_file_location("complement_dimacs", COMPLEMENT_PATH)
COMPLEMENT = importlib.util.module_from_spec(COMPLEMENT_SPEC)
COMPLEMENT_SPEC.loader.exec_module(COMPLEMENT)


class ComplementTests(unittest.TestCase):
    def test_complement_of_path_on_four_vertices(self):
        # Path 1-2-3-4 has edges {12, 23, 34}. Complement on 4 vertices has 6-3=3 edges:
        # {13, 14, 24}.
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "path4.clq"
            dst = Path(tmp) / "out" / "path4.clq"
            dst.parent.mkdir()
            src.write_text("p edge 4 3\ne 1 2\ne 2 3\ne 3 4\n", encoding="utf-8")
            n, count = COMPLEMENT.write_complement(src, dst)
            self.assertEqual((n, count), (4, 3))
            self.assertEqual(MODULE.parse_dimacs(dst), (4, 3))
            edges = {tuple(sorted(map(int, l.split()[1:])))
                     for l in dst.read_text().splitlines() if l.startswith("e ")}
            self.assertEqual(edges, {(1, 3), (1, 4), (2, 4)})

    def test_double_complement_is_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "g.clq"
            once = Path(tmp) / "once.clq"
            twice = Path(tmp) / "twice.clq"
            src.write_text("p edge 5 4\ne 1 2\ne 1 3\ne 2 5\ne 4 5\n", encoding="utf-8")
            COMPLEMENT.write_complement(src, once)
            COMPLEMENT.write_complement(once, twice)
            def edge_set(path):
                return {tuple(sorted(map(int, l.split()[1:])))
                        for l in path.read_text().splitlines() if l.startswith("e ")}
            self.assertEqual(edge_set(twice), edge_set(src))


if __name__ == "__main__":
    unittest.main()
