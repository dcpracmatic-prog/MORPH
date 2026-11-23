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


if __name__ == "__main__":
    unittest.main()
