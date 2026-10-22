"""Run both consistency controls inside the same pinned Freqtrade container."""
import json
import runpy
import subprocess
from pathlib import Path

from analyze_results import load

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
runpy.run_path(str(HERE / "prepare_aligned_data.py"))
for mode in ["1h", "5m"]:
    output = ROOT / f"user_data/backtest_results/comparison_aligned_{mode}"
    output.mkdir(parents=True, exist_ok=True)
    args = ["freqtrade", "backtesting", "--userdir", str(ROOT / "user_data"),
            "--datadir", str(ROOT / "user_data/data/binance_aligned"),
            "--config", str(ROOT / "configs/research.example.json"), "--strategy", "MyStrategy",
            "--timeframe", "1h", "--timerange", "20230101-20260901", "--fee", "0.0005",
            "--cache", "none", "--export", "trades", "--backtest-directory", str(output)]
    if mode == "5m":
        args += ["--timeframe-detail", "5m"]
    with (output / "run.log").open("w") as log:
        subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=True)
    print(f"Finished aligned {mode}", flush=True)
results = {mode: load("aligned_" + mode)[0] for mode in ["1h", "5m"]}
results["pnl_delta"] = results["5m"]["profit_total_abs"] - results["1h"]["profit_total_abs"]
(HERE / "alignment_control.json").write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps(results, indent=2), flush=True)
