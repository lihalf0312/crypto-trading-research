# TrendFollowingCTA Backtest Summary

## Strategy Overview

A medium-frequency trend-following CTA strategy implemented with the Freqtrade framework.

The strategy uses:

- 1-hour Binance Futures candles
- EMA-based trend signals
- ATR volatility filtering
- Long/short directional trading
- Rule-based risk management


## Backtest Configuration

| Item | Value |
|---|---|
| Market | BTC/USDT Perpetual Futures |
| Exchange | Binance Futures |
| Timeframe | 1h |
| Period | 2023-09-11 to 2026-09-01 |
| Starting Capital | 10,000 USDT |
| Maximum Open Trades | 1 |


## Performance Results

| Metric | Value |
|---|---:|
| Total Trades | 921 |
| Total Return | -6.05% |
| Sharpe Ratio | -0.43 |
| Maximum Drawdown | 13.22% |
| Profit Factor | 0.91 |


## Notes

This strategy is published as a reproducible research example.

The objective is to demonstrate the complete quantitative workflow:

data preparation → strategy development → backtesting → performance evaluation.

The production strategy and proprietary alpha signals are not included.
