"""Check the BTC example against unmodified native Freqtrade pricing functions.

Run in the pinned Freqtrade image. This checks the candidate-price/fill rules;
it does not replace a full-period counterfactual backtest.
"""
import json
from pathlib import Path
from types import SimpleNamespace

from freqtrade.enums import ExitCheckTuple, ExitType
from freqtrade.optimize.backtesting import Backtesting

engine = Backtesting.__new__(Backtesting)
engine.strategy = SimpleNamespace(
    use_custom_stoploss=False, trailing_stop=True,
    trailing_only_offset_is_reached=True,
    trailing_stop_positive_offset=0.05, trailing_stop_positive=0.015,
)
exit_signal = ExitCheckTuple(exit_type=ExitType.TRAILING_STOP_LOSS)
records = []
for mode, minutes, open_, high, low, stop in [
    ("1h", 0, 61000.0, 62672.3, 60971.1, 62484.3),
    ("5m", 30, 61478.3, 61845.0, 61347.0, 61659.5),
]:
    trade = SimpleNamespace(is_short=False, leverage=5.0, stop_loss=stop)
    row = (None, open_, high, low)
    rate = engine._get_close_rate_for_stoploss(row, trade, exit_signal, minutes)
    records.append(dict(mode=mode, elapsed_minutes=minutes, low=low, high=high,
                        candidate_exit_rate=rate, fills_within_candle=engine._get_order_filled(rate, row)))
assert abs(records[0]["candidate_exit_rate"] - 63867.0) < 1e-7
assert records[0]["fills_within_candle"] is False
assert records[1]["fills_within_candle"] is True
path = Path(__file__).resolve().parent / "case_engine_check.json"
path.write_text(json.dumps(records, indent=2) + "\n")
print(path.read_text())
