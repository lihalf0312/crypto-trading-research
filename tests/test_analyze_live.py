import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analyze_live import AnalysisError, analyze, demo_trades, read_closed_trades


class AnalysisTests(unittest.TestCase):
    def test_demo_accounting_and_attribution(self):
        report = analyze(demo_trades(), 1000, synthetic=True)
        m = report["metrics"]
        self.assertEqual(m["trades"], 12)
        self.assertEqual(m["net_pnl"], 27)
        self.assertEqual(m["final_realized_equity"], 1027)
        self.assertAlmostEqual(m["total_return"], 0.027)
        self.assertEqual(sum(v["net_pnl"] for v in report["by_pair"].values()), 27)
        self.assertEqual(sum(v["net_pnl"] for v in report["by_side"].values()), 27)
        self.assertEqual(report["remove_best_days"]["1"]["pnl"], 9)
        self.assertTrue(report["metadata"]["synthetic"])
        json.dumps(report, allow_nan=False)

    def test_first_loss_draws_down_from_initial_capital(self):
        row = demo_trades()[0]
        row.update(close_profit_abs=-20, close_profit=-0.02)
        report = analyze([row], 100)
        self.assertAlmostEqual(report["metrics"]["max_daily_realized_drawdown"], -0.2)
        self.assertAlmostEqual(report["daily"][0]["return_ratio"], -0.2)

    def test_zero_trade_days_are_included(self):
        report = analyze([demo_trades()[0]], 1000, date(2024, 1, 1), date(2024, 1, 4))
        self.assertEqual(report["metrics"]["observation_days"], 4)
        self.assertEqual([r["pnl"] for r in report["daily"]], [0, 12, 0, 0])

    def test_empty_and_one_sided_inputs_are_json_safe(self):
        empty = analyze([], 100)
        self.assertEqual(empty["metrics"]["final_realized_equity"], 100)
        self.assertIsNone(empty["metrics"]["win_rate"])
        self.assertIsNone(empty["metrics"]["annualized_sharpe"])
        for profits in ([10, 10], [-10, -10], [0, 0]):
            rows = demo_trades()[:2]
            for row, pnl in zip(rows, profits):
                row.update(close_profit_abs=pnl, close_profit=pnl / 100)
            report = analyze(rows, 100)
            self.assertIsNone(report["metrics"]["payoff_ratio"])
            json.dumps(report, allow_nan=False)
        json.dumps(empty, allow_nan=False)

    def test_insolvency_disables_return_ratios(self):
        rows = demo_trades()[:2]
        rows[0].update(close_profit_abs=-120, close_profit=-1.2)
        report = analyze(rows, 100)
        self.assertIsNone(report["metrics"]["annualized_sharpe"])
        self.assertIsNone(report["metrics"]["annualized_sortino"])
        self.assertIsNone(report["daily"][-1]["return_ratio"])

    def test_input_validation(self):
        for capital in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(AnalysisError):
                analyze([], capital)
        with self.assertRaises(AnalysisError):
            analyze([], 100, date(2024, 1, 4), date(2024, 1, 1))
        bad = demo_trades()[0]
        bad["close_profit_abs"] = float("nan")
        with self.assertRaises(AnalysisError):
            analyze([bad], 100)

    def test_sqlite_fixture_read_without_mutating_input(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "synthetic.sqlite"
            subprocess.run([sys.executable, str(ROOT / "scripts/generate_demo_trades.py"), "--output", str(db)],
                           capture_output=True, check=True)
            before = hashlib.sha256(db.read_bytes()).digest()
            rows = read_closed_trades(db)
            self.assertEqual(len(rows), 12)
            self.assertEqual(hashlib.sha256(db.read_bytes()).digest(), before)
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()), ["synthetic.sqlite"])
            self.assertEqual(analyze(rows, 1000)["metrics"]["net_pnl"], 27)

    def test_missing_database_is_not_created(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "missing.sqlite"
            with self.assertRaises(AnalysisError):
                read_closed_trades(db)
            self.assertFalse(db.exists())

    def test_missing_schema_has_safe_error(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "private-name.sqlite"
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE other (id INTEGER)")
            with self.assertRaises(AnalysisError) as caught:
                read_closed_trades(db)
            self.assertNotIn(str(db), str(caught.exception))

    def test_cli_demo_is_explicitly_synthetic(self):
        proc = subprocess.run([sys.executable, str(ROOT / "analyze_live.py"), "--demo", "--format", "json"],
                              capture_output=True, text=True, check=True)
        result = json.loads(proc.stdout)
        self.assertTrue(result["metadata"]["synthetic"])
        self.assertNotIn("trades", result)

    def test_cli_does_not_overwrite_output(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "summary.json"
            output.write_text("keep")
            proc = subprocess.run([sys.executable, str(ROOT / "analyze_live.py"), "--demo", "--output", str(output)],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            self.assertEqual(output.read_text(), "keep")
            self.assertNotIn(str(output), proc.stderr)

    def test_sqlite_demo_has_explicit_synthetic_label(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "synthetic.sqlite"
            subprocess.run([sys.executable, str(ROOT / "scripts/generate_demo_trades.py"), "--output", str(db)],
                           capture_output=True, check=True)
            result = subprocess.run([sys.executable, str(ROOT / "analyze_live.py"), "--db", str(db),
                                     "--synthetic-input", "--initial-capital", "1000", "--format", "json"],
                                    capture_output=True, text=True, check=True)
            self.assertTrue(json.loads(result.stdout)["metadata"]["synthetic"])
            self.assertEqual(json.loads(result.stdout)["metadata"]["source"], "synthetic_sqlite")


if __name__ == "__main__":
    unittest.main()
