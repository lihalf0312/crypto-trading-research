"""
Public Freqtrade strategy interface.

This module demonstrates integration with Freqtrade.
Proprietary alpha signals are intentionally excluded.

SAFETY:
This example does not generate entry or exit signals.
It is not intended for live trading.
"""

from pandas import DataFrame
from freqtrade.strategy import IStrategy


class ExampleStrategy(IStrategy):
    """Non-trading strategy interface for portfolio demonstration."""

    INTERFACE_VERSION = 3

    timeframe = "5m"
    can_short = False

    minimal_roi = {"0": 0.02}
    stoploss = -0.10

    process_only_new_candles = True
    startup_candle_count = 1

    def populate_indicators(
        self,
        dataframe: DataFrame,
        metadata: dict,
    ) -> DataFrame:
        """Reserved interface for feature engineering."""

        return dataframe

    def populate_entry_trend(
        self,
        dataframe: DataFrame,
        metadata: dict,
    ) -> DataFrame:
        """Disable entries: proprietary signal logic is excluded."""

        dataframe["enter_long"] = 0

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: DataFrame,
        metadata: dict,
    ) -> DataFrame:
        """Disable exits: this public example never opens positions."""

        dataframe["exit_long"] = 0

        return dataframe
