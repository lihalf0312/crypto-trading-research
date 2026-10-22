"""Audit the exact input files used by the two backtests (run in Freqtrade image)."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DATA = ROOT / "user_data/data/binance/futures"
START = pd.Timestamp("2023-01-01", tz="UTC")
END = pd.Timestamp("2026-09-01", tz="UTC")
config = json.loads((ROOT / "configs/research.example.json").read_text())
records = []
comparisons = []
mismatch_rows = []
for pair in config["exchange"]["pair_whitelist"]:
    stem = pair.replace("/", "_").replace(":", "_")
    frames = {}
    for tf, kind in [("1h", "futures"), ("5m", "futures"),
                     ("1h", "mark"), ("1h", "funding_rate")]:
        path = DATA / f"{stem}-{tf}-{kind}.feather"
        frame = pd.read_feather(path).sort_values("date")
        subset = frame[(frame.date >= START) & (frame.date < END)]
        item = dict(pair=pair, timeframe=tf, kind=kind, rows=len(frame),
                    first=str(frame.date.min()), last=str(frame.date.max()),
                    period_rows=len(subset), duplicates=int(frame.date.duplicated().sum()),
                    zero_volume_rows=int((subset.volume == 0).sum()) if "volume" in subset else None,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        if kind in ("futures", "mark"):
            expected = pd.date_range(START, END, freq=tf.replace("m", "min"), inclusive="left")
            missing = expected.difference(subset.date)
            item.update(missing_in_period=len(missing), missing_first=[str(x) for x in missing[:5]],
                        warmup_1h_rows=int(((frame.date >= START - pd.Timedelta(hours=240)) &
                                            (frame.date < START)).sum()) if tf == "1h" else None)
        else:
            item["max_interval_hours"] = float(subset.date.diff().dt.total_seconds().max() / 3600)
        records.append(item)
        frames[(tf, kind)] = subset.set_index("date")
    detail = frames[("5m", "futures")].resample("1h").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    main = frames[("1h", "futures")]
    joint = main.index.intersection(detail.index)
    diffs = {col: int((~np.isclose(main.loc[joint, col], detail.loc[joint, col],
                                  rtol=1e-7, atol=1e-8)).sum()) for col in detail.columns}
    price_columns = ["open", "high", "low", "close"]
    price_diff = (~np.isclose(main.loc[joint, price_columns], detail.loc[joint, price_columns],
                             rtol=1e-7, atol=1e-8)).any(axis=1)
    for date in joint[price_diff]:
        mismatch_rows.append(dict(pair=pair, date=str(date),
                                  **{f"{col}_1h": float(main.loc[date, col]) for col in detail.columns},
                                  **{f"{col}_5m_aggregated": float(detail.loc[date, col]) for col in detail.columns}))
    comparisons.append(dict(pair=pair, common_hours=len(joint), mismatched_hours_by_column=diffs))
result = dict(start=str(START), end_exclusive=str(END), files=records,
              aggregation_comparison=comparisons,
              strategy_sha256=hashlib.sha256((ROOT / "user_data/strategies/my_strategy.py").read_bytes()).hexdigest())
(OUT / "data_audit.json").write_text(json.dumps(result, indent=2) + "\n")
private_output = ROOT / "analysis_outputs/backtest_analysis"
private_output.mkdir(parents=True, exist_ok=True)
pd.DataFrame(mismatch_rows).to_csv(private_output / "data_mismatches.csv", index=False)
print(json.dumps(dict(files=len(records),
                     missing_candles=sum(r.get("missing_in_period", 0) for r in records),
                     comparisons=comparisons), indent=2))
