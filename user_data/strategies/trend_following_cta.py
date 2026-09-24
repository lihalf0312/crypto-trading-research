"""
Public medium-frequency CTA strategy example.

This strategy demonstrates a classical trend-following approach
using moving averages and volatility filtering.

The production strategy and proprietary alpha logic are not included.
"""

from pandas import DataFrame

import talib.abstract as ta

from freqtrade.strategy import IStrategy


class TrendFollowingCTA(IStrategy):

    INTERFACE_VERSION = 3

    timeframe = "1h"

    can_short = True

    # Example risk settings
    minimal_roi = {
        "0": 0.05,
        "240": 0.02,
        "720": 0.0
    }

    stoploss = -0.15

    process_only_new_candles = True

    startup_candle_count = 250


    def populate_indicators(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        # Trend indicators
        dataframe["ema_fast"] = ta.EMA(
            dataframe,
            timeperiod=50
        )

        dataframe["ema_slow"] = ta.EMA(
            dataframe,
            timeperiod=200
        )

        # Volatility filter
        dataframe["atr"] = ta.ATR(
            dataframe,
            timeperiod=14
        )

        dataframe["atr_pct"] = (
            dataframe["atr"] /
            dataframe["close"]
        )

        return dataframe


    def populate_entry_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        # Long trend following signal
        dataframe.loc[
            (
                (dataframe["ema_fast"] >
                 dataframe["ema_slow"])
                &
                (dataframe["atr_pct"] > 0.005)
            ),
            "enter_long"
        ] = 1


        # Short trend following signal
        dataframe.loc[
            (
                (dataframe["ema_fast"] <
                 dataframe["ema_slow"])
                &
                (dataframe["atr_pct"] > 0.005)
            ),
            "enter_short"
        ] = 1


        return dataframe


    def populate_exit_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:


        # Exit when trend reverses

        dataframe.loc[
            dataframe["ema_fast"] <
            dataframe["ema_slow"],
            "exit_long"
        ] = 1


        dataframe.loc[
            dataframe["ema_fast"] >
            dataframe["ema_slow"],
            "exit_short"
        ] = 1


        return dataframe
