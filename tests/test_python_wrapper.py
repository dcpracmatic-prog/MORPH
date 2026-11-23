import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python"))

from morph import solve_mis  # noqa: E402


class PythonWrapperTests(unittest.TestCase):
    def test_karate_morph_size_and_validity(self):
        result = solve_mis(REPO_ROOT / "datasets" / "karate.gph",
                           method="morph", budget_ms=100, seed=1)
        self.assertEqual(result["size"], 20)
        self.assertEqual(len(result["vertices"]), 20)
        self.assertTrue(result["valid"])
        self.assertTrue(result["valid_python"])

    def test_degree_is_deterministic(self):
        first = solve_mis(REPO_ROOT / "datasets" / "football.gph",
                          method="degree", budget_ms=100, seed=1)
        second = solve_mis(REPO_ROOT / "datasets" / "football.gph",
                           method="degree", budget_ms=100, seed=1)
        self.assertEqual(first["vertices"], second["vertices"])
        self.assertTrue(first["valid_python"])

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            solve_mis(REPO_ROOT / "datasets" / "karate.gph",
                      method="nope", budget_ms=100, seed=1)


if __name__ == "__main__":
    unittest.main()
