import importlib.util
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "validate_absolute_quality", ROOT / "scripts" / "validate_absolute_quality.py")
vaq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vaq)


class ExactQualityGuardTests(unittest.TestCase):
    def test_exact_values(self):
        q, g = vaq.exact_quality_and_gap(39, 62)
        self.assertAlmostEqual(q, 39 / 62 * 100, places=9)
        self.assertAlmostEqual(g, 23 / 62 * 100, places=9)
        self.assertAlmostEqual(q + g, 100.0, places=9)

    def test_guard_accepts_correct_float(self):
        q, g = vaq.guard_quality_and_gap(38, 40, 95.0, 5.0)
        self.assertEqual((q, g), (95.0, 5.0))

    def test_guard_rejects_wrong_float(self):
        with self.assertRaises(RuntimeError):
            vaq.guard_quality_and_gap(39, 62, 50.0, 50.0)

    def test_guard_rejects_nan(self):
        with self.assertRaises(RuntimeError):
            vaq.guard_quality_and_gap(39, 62, math.nan, math.nan)

    def test_zero_reference_raises(self):
        with self.assertRaises(ZeroDivisionError):
            vaq.exact_quality_and_gap(1, 0)


if __name__ == "__main__":
    unittest.main()
