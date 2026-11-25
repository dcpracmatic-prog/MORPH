import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_absolute_quality.py"
SPEC = importlib.util.spec_from_file_location("validate_absolute_quality", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _fake_qoblib(root: Path) -> Path:
    """Minimal QOBLIB tree: one triangle-free graph with a known optimum."""
    mis_root = root / "07-independentset"
    (mis_root / "instances").mkdir(parents=True)
    (mis_root / "solutions").mkdir(parents=True)
    # Path graph 1-2-3: optimum MIS = 2 (vertices 1 and 3).
    (mis_root / "instances" / "tiny.gph").write_text(
        "p edge 3 2\ne 1 2\ne 2 3\n", encoding="utf-8")
    (mis_root / "solutions" / "tiny.opt.sol").write_text(
        "# Objective value = 2\n1\n3\n", encoding="utf-8")
    return mis_root


class ValidateAbsoluteQualityTests(unittest.TestCase):
    def test_crosscheck_columns_agree(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mis_root = _fake_qoblib(tmp_path)
            refs, _warnings = MODULE.discover_references(mis_root)
            instances = MODULE.discover_instances(mis_root)
            results = tmp_path / "results.csv"
            results.write_text(
                "instance,solver,objective,budget_ms,seed\n"
                "tiny,morph,2,100,1\n"
                "tiny,morph,1,100,2\n",
                encoding="utf-8")
            rows = MODULE.read_results(results)
            MODULE.results_path_global = results
            MODULE.qoblib_global = tmp_path
            MODULE.mis_root_global = mis_root
            _meta, summary = MODULE.compute_reports(
                rows, refs, instances, tmp_path / "out")
            self.assertEqual(len(summary), 1)
            row = summary[0]
            # Mean objective 1.5 / reference 2 = 75% quality, 25% gap,
            # computed both ways.
            self.assertAlmostEqual(float(row["quality_mean_pct"]), 75.0)
            self.assertAlmostEqual(float(row["quality_crosscheck_pct"]), 75.0)
            self.assertAlmostEqual(float(row["gap_mean_pct"]), 25.0)
            self.assertAlmostEqual(float(row["gap_crosscheck_pct"]), 25.0)
            self.assertEqual(row["hit_reference_runs"], 1)

    def test_invalid_reference_is_not_counted_as_hit(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mis_root = _fake_qoblib(tmp_path)
            # Corrupt the reference: vertices 1 and 2 are adjacent.
            (mis_root / "solutions" / "tiny.opt.sol").write_text(
                "# Objective value = 2\n1\n2\n", encoding="utf-8")
            refs, _warnings = MODULE.discover_references(mis_root)
            instances = MODULE.discover_instances(mis_root)
            results = tmp_path / "results.csv"
            results.write_text(
                "instance,solver,objective,budget_ms,seed\n"
                "tiny,morph,2,100,1\n",
                encoding="utf-8")
            rows = MODULE.read_results(results)
            MODULE.results_path_global = results
            MODULE.qoblib_global = tmp_path
            MODULE.mis_root_global = mis_root
            _meta, summary = MODULE.compute_reports(
                rows, refs, instances, tmp_path / "out")
            self.assertEqual(summary, [])


if __name__ == "__main__":
    unittest.main()
