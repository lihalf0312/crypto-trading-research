from pandas import DataFrame

import talib.abstract as ta
from freqtrade.strategy import IStrategy


class MyStrategy(IStrategy):
    """SMA240 major-trend filter with EMA10 minor-trend entries."""

    INTERFACE_VERSION = 3

    # Can this strategy go short?
    can_short: bool = True

    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi".
    minimal_roi = {
        # "120": 0.0,  # exit after 120 minutes at break even
        "0": 0.15
    }

    # Optimal stoploss designed for the strategy.
    # This attribute will be overridden if the config file contains "stoploss".
    stoploss = -0.06

    # Trailing stoploss
    trailing_stop = True
    trailing_only_offset_is_reached = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.05  # Disabled / not configured

    # Optimal timeframe for the strategy.
    timeframe = "1h"

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = True

    # These values can be overridden in the config.
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # SMA240 is the longest indicator used by this strategy.
    startup_candle_count: int = 240

    # Optional order type mapping.
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "limit",
        "stoploss_on_exchange": True,
        "stoploss_on_exchange_limit_ratio": 0.995,
        "stoploss_on_exchange_interval": 60,
        "emergency_exit": "market",
    }

    # Optional order time in force.
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    plot_config = {
        "main_plot": {
            "sma240": {"color": "orange"},
            "ema10": {"color": "blue"},
        },
    }

    def leverage(
        self,
        pair: str,
        current_time,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        leverage_map = {
            "BTC/USDT:USDT": 5.0,
            "ETH/USDT:USDT": 4.0,
            "SOL/USDT:USDT": 3.0,
            "XRP/USDT:USDT": 3.0,
            "BNB/USDT:USDT": 3.0
        }
        target = leverage_map.get(pair, 2.0)
        return min(target, max_leverage)

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate only the moving averages used by the entry rules."""
        dataframe["sma240"] = ta.SMA(dataframe, timeperiod=240)
        dataframe["ema10"] = ta.EMA(dataframe, timeperiod=10)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Enter only when both the major and minor trends agree."""
        dataframe.loc[
            (
                (dataframe["close"] > dataframe["sma240"])
                & (dataframe["close"] > dataframe["ema10"])
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "above_sma240_ema10")

        dataframe.loc[
            (
                (dataframe["close"] < dataframe["sma240"])
                & (dataframe["close"] < dataframe["ema10"])
                & (dataframe["volume"] > 0)
            ),
            ["enter_short", "enter_tag"],
        ] = (1, "below_sma240_ema10")

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Do not produce indicator exits; use stoploss, trailing stop, and ROI."""
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0

        return dataframe
