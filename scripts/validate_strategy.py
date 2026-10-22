"""Load MyStrategy offline and exercise its indicators on synthetic candles."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from freqtrade.resolvers import StrategyResolver

ROOT = Path(__file__).resolve().parents[1]
config = json.loads((ROOT / "configs/research.example.json").read_text())
config.update(strategy="MyStrategy", user_data_dir=ROOT / "user_data",
              strategy_path=str(ROOT / "user_data/strategies"))
strategy = StrategyResolver.load_strategy(config)
close = np.concatenate([np.linspace(100, 160, 300), np.linspace(160, 80, 300)])
frame = pd.DataFrame(dict(date=pd.date_range("2024-01-01", periods=len(close), freq="1h", tz="UTC"),
                          open=close, high=close + 1, low=close - 1, close=close, volume=1.0))
frame = strategy.populate_indicators(frame, {"pair": "DEMO/USDT:USDT"})
frame = strategy.populate_entry_trend(frame, {"pair": "DEMO/USDT:USDT"})
frame = strategy.populate_exit_trend(frame, {"pair": "DEMO/USDT:USDT"})
assert strategy.timeframe == "1h" and strategy.can_short
assert {"sma240", "ema10"}.issubset(frame.columns)
assert (frame.enter_long == 1).any() and (frame.enter_short == 1).any()
assert not frame.exit_long.any() and not frame.exit_short.any()
print(json.dumps(dict(strategy=type(strategy).__name__, timeframe=strategy.timeframe,
                      synthetic_indicator_check="passed; no trades or performance simulated",
                      sha256=hashlib.sha256((ROOT / "user_data/strategies/my_strategy.py").read_bytes()).hexdigest()), indent=2))
