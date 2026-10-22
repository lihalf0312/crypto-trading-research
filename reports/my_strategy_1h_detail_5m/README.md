# MyStrategy Return Differences Between 1h and 5m Detailed Backtests

All capital, equity and individual trade examples in this study come from historical backtest simulations. They contain no actual account balances, execution records or live performance. The complete strategy source is public.

Both runs keep the strategy's primary timeframe at **1h** and change only the resolution used to simulate fills and exits. The 5m detailed run does not recalculate SMA240 or EMA10 on 5m candles, and no strategy parameters were retuned. To remove minor inconsistencies between the locally downloaded timeframes, both runs in the main comparison use the same 5m dataset and the 1h candles aggregated from it.

**The strong 1h baseline performance did not survive 5m execution refinement.** With consistent source data, the 1h baseline returned **+2,393.40%**, while the 5m detailed run returned **-80.19%**, a net profit difference of **12,367.95 USDT**.

The differences begin with exit simulation: the intrahour order of trailing-stop and ROI triggers, together with this engine version's special pricing on entry candles, changes the profit captured. Earlier or later release of position slots then changes the trade sequence and the capital path. The detailed run eventually fell below the fixed entry-capital requirement and recorded no further trades after 2024-03-08. The outcome therefore cannot be interpreted as a uniform reduction in returns on the same set of trades.

## Overall Results

| Metric | 1h baseline | 1h signals with 5m detail |
| --- | ---: | ---: |
| Initial capital, USDT | 500.00 | 500.00 |
| Final balance, USDT | 12,467.01 | 99.06 |
| Net profit, USDT | 11,967.01 | -400.94 |
| Total return | +2,393.40% | -80.19% |
| Trades | 21,074 | 3,017 |
| Win rate | 54.53% | 52.87% |
| Average return per trade | +0.5745% | -0.1372% |
| Profit factor | 1.205 | 0.955 |
| Maximum relative drawdown | 33.96% | 87.18% |
| Maximum absolute drawdown, USDT | 437.08 | 673.59 |
| Average holding time | 7 hours 16 minutes | 8 hours 01 minute |
| Last trade close, UTC | 2026-09-01 00:00 | 2024-03-08 15:30 |

Both engine runs cover the period through 2026-09-01. The detailed run ended with 99.06 USDT, below the configured 100 USDT target margin per trade, with no additional capital injected. Its subsequent inactivity does not imply an absence of trend signals. Likewise, the difference between 3,017 and 21,074 trades is not evidence that finer execution resolution inherently reduces trading frequency.

Maximum relative drawdown uses the engine's `max_relative_drawdown` field. The 7.20% shown in the 1h command-line summary is the relative decline associated with the largest absolute drawdown interval. That interval differs from the one with the largest percentage decline; the maximum relative drawdown over the full period is 33.96%. These metrics use closed trades rather than account equity marked to market with open-position PnL.

![Realized equity and exit-reason comparison](comparison.png)

The equity curves accumulate daily closed-trade PnL, and the first panel uses a logarithmic vertical axis. The drawdown panel is calculated from daily realized equity. Neither includes floating PnL, and the daily drawdown chart is not the same measure as the engine's trade-level drawdown metrics in the table.

## Quantitative Evidence Behind the Return Difference

### Lower Winning-Trade Returns Turn Expectancy Negative

The average winning-trade return fell from **6.22%** in the baseline to **5.36%** in the detailed run. Average losing-trade returns were **-6.19%** and **-6.31%**, respectively. Combined with the win-rate decline from 54.53% to 52.87%, the identity "win rate × average win + loss rate × average loss" gives an average trade return of +0.5745% for the baseline and -0.1372% for the detailed run. These returns already include the effects of costs.

| Exit reason | 1h trades | 1h average return | 1h net profit, USDT | 5m trades | 5m average return | 5m net profit, USDT |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `trailing_stop_loss` | 10,846 | 5.38% | 57,535.21 | 1,527 | 4.92% | 7,446.84 |
| `roi` | 848 | 15.00% | 12,560.80 | 69 | 15.00% | 1,027.45 |
| `stop_loss` | 9,375 | -6.29% | -58,122.99 | 1,421 | -6.31% | -8,875.23 |
| `force_exit` | 5 | -1.21% | -6.01 | 0 | — | 0.00 |

The average trailing-stop return declined from 5.38% to 4.92%, while the share of ROI exits fell from 4.02% to 2.29%. Because the trade sets and active periods differ, differences in these totals are not isolated causal contributions of individual exit rules. Matched entries below provide a closer examination of what changed.

### Slot Availability and Capital Constraints Change Most of the Trade Set

Exact matching on pair, direction and entry time identifies **288 shared entries**, all with identical entry prices and margin amounts. There are 20,786 trades unique to the baseline and 2,729 unique to the detailed run. In the detailed run, **2,578 entries, or 85.45%, occur between hourly boundaries**. This shows that reusing the same 1h signal after a slot becomes available changes the trade sequence; it does not mean that indicators were recalculated on 5m candles.

Across the 288 shared entries, the detailed run earned **92.58 USDT less**. Exit reasons changed for 21 trades: 16 switched from ROI to trailing stop, reducing profit by 118.48 USDT in total, while 5 switched from fixed stoploss to trailing stop, improving profit by 57.36 USDT. Finer resolution did not make every trade worse.

The full-period profit difference reconciles exactly as follows:

```text
5m net profit − 1h net profit
= PnL difference on shared entries + PnL of 5m-only trades − PnL of 1h-only trades
= −92.58326663 − 489.33948862 − 11786.02698506
= −12367.94974031 USDT
```

This is an accounting decomposition. The unmatched component includes slot competition, continued holding, capital constraints and market periods after the detailed run stopped trading. It cannot be attributed entirely to any single mechanism. In particular, the trade records do not support describing the full gap of roughly 12,400 USDT as reduced trailing-stop profits on the same trades.

### Trading Costs Consume the Detailed Run's Thin Price Profit

| PnL component, USDT | 1h baseline | 5m detail |
| --- | ---: | ---: |
| Directional PnL from entry and exit prices only | 18,216.71 | 590.19 |
| Entry and exit trading fees | −6,109.19 | −964.21 |
| Net funding income | -140.51 | -26.91 |
| Final net profit | 11,967.01 | -400.94 |

Trading fees were recalculated from filled quantities, prices and fee rates, then reconciled against each trade's net PnL. Both runs use the same fee rate. Total fees were lower in the detailed run, so an increase in aggregate fees does not explain the gap. However, its 590.19 USDT price profit could not cover 964.21 USDT in trading fees and 26.91 USDT in funding costs, turning the result into a net loss.

## A Shared BTC Entry With Different Exits

At 2024-02-28 16:00 UTC, both runs opened a BTC long at **61,000 USDT**, with 5x leverage, a quantity of 0.008 BTC and a simulated margin amount of 97.60 USDT.

| Item | 1h baseline | 5m detail |
| --- | ---: | ---: |
| Start time of the exit candle, UTC | 17:00 | 16:30 |
| Exit reason | ROI | Trailing stop |
| Exit price | 62,925.5 | 61,659.5 |
| Engine-reported net return | 15.00% | 4.63% |
| Net profit, USDT | 14.65 | 4.52 |

The 16:30 5m candle has a high of 61,845 and a low of 61,347. The engine adjusts the trailing stop using the high, giving approximately `61845 × (1 − 0.015 / 5) = 61659.465`, rounded to 61,659.5. This price lies inside the candle's range and can therefore fill in the simulation. The market subsequently rose further: the 5m candle starting at 17:00 reached 62,952.8, enough to trigger the baseline's ROI price. The detailed run had already exited and could not capture that later move on this trade.

**This example also involves the engine version's special handling of entry candles.** For the hourly entry candle, recalculating the candidate trailing-stop exit price with the native function gives:

```text
61000 × (1 + 0.05 − 0.015 / 5) = 63867
```

That price exceeds the hourly high of 62,672.3 and fails the native `low ≤ price ≤ high` limit-fill check. At 30 minutes after entry, the detailed run no longer uses the zero-minute holding-time branch; its candidate stop price of 61,659.5 can fill. The baseline ultimately exits through ROI in the next hour. Native-function calculations are recorded in [case_engine_check.json](case_engine_check.json) and can be checked with [check_case_engine.py](check_case_engine.py). This combines intrabar path effects with version-specific stop pricing and fill checks; calling it simply "more noise on 5m candles" misses those mechanisms.

![BTC exit prices and 5m market candles](case_btc_20240228.png)

Exit markers use the candle start times recorded in the exports, not tick-level execution timestamps. Vertical lines show each 5m candle's high-low range. The ordering of high and low within a 5m candle is still an engine assumption. This repository retains the historical simulation figure and native pricing-function check, without distributing raw market files.

The 1h baseline includes 512 zero-minute trailing-stop trades with combined profits of 4,454.46 USDT, approximately 37.2% of full-period net profit. This makes entry-candle handling worth examining, but the amount is not an estimate of simulation bias. No full-period ablation was performed by replacing each engine rule in isolation, so the entire return gap cannot be attributed to this special branch.

## Annual Results and the Capital Path

| Year of close | 1h trades | 1h net profit, USDT | 5m trades | 5m net profit, USDT |
| --- | ---: | ---: | ---: | ---: |
| 2023 | 4,370 | 2,104.00 | 2,388 | -339.78 |
| 2024 | 6,953 | 4,233.89 | 629 | -61.15 |
| 2025 | 6,746 | 3,239.58 | 0 | 0.00 |
| 2026 (first eight months) | 3,005 | 2,389.54 | 0 | 0.00 |

In 2023, while both runs were still trading, the baseline earned 2,104.00 USDT and the detailed run lost 339.78 USDT. Divergence therefore appeared before trading stopped. The detailed run's absence of trades in 2025 and 2026 reflects the subsequent effects of earlier losses and the fixed entry-capital requirement. Zero PnL in those years is not evidence about its ability to adapt to those market regimes.

## Backtest Scope and Shared Configuration

The study uses [MyStrategy](../../user_data/strategies/my_strategy.py), Freqtrade 2026.8 and CCXT 4.5.76. The period is **2023-01-01 00:00 through 2026-09-01 00:00, all in UTC**. Warmup data starts on 2022-12-22 and supplies the required 240 hourly candles. Positions still open at the end are recorded as `force_exit`.

| Setting | Shared value |
| --- | --- |
| Venue | Binance USDT perpetual futures, isolated margin |
| Initial capital | 500 USDT |
| Margin per trade | Fixed 100 USDT target, subject to balance, precision and exchange limits |
| Maximum concurrent positions | 5 |
| Signal and indicator timeframe | 1h, SMA240 and EMA10 |
| Direction | Both long and short |
| Leverage targets | BTC 5x, ETH 4x, SOL/XRP/BNB 3x, others 2x |
| Trading fee | 0.05% of notional per side, charged on entry and exit |
| Fixed stoploss | `stoploss = -0.06` |
| Minimal ROI | `minimal_roi = {"0": 0.15}` |
| Trailing stop | 5% profit activation threshold; 1.5% trailing distance |
| Result cache | `--cache none`, recomputed |

Pairs are processed in the fixed configuration order: BTC, ETH, SOL, XRP, BNB, DOGE, ADA, LINK, AVAX, LTC, BCH, DOT, NEAR and UNI, all in `ASSET/USDT:USDT` format. Credentials and private service settings are excluded. The shared experiment settings are provided in the [credential-free research configuration](../../configs/research.example.json).

The target margin remains fixed at 100 USDT per trade. Cumulative returns should therefore not be interpreted as compounding from position sizes maintained at a constant fraction of account equity.

## Why Identical 1h Signals Can Produce Different Outcomes

### Exits Depend on the Intrahour Price Path

The strategy enters long when the close is above both SMA240 and EMA10, and short when it is below both. Signals persist while those conditions hold; entries are not limited to moving-average crossings. `populate_exit_trend()` always sets both long and short exit signals to zero. Actual exits use fixed stoploss, trailing stop, ROI and end-of-backtest forced exits.

Hourly OHLC records the open, high, low and close without revealing whether a profit target or a stop was reached first. Detail mode divides each hour into 12 ordered 5m intervals and processes positions through them. A position closed in an earlier interval cannot benefit from a later move in the same hour. Freqtrade still applies exit priorities and trailing-stop assumptions within each simulated candle; 5m detail narrows the interval over which those assumptions operate. [Backtesting assumptions](https://www.freqtrade.io/en/stable/backtesting/#assumptions-made-by-backtesting)

Trades that trigger trailing stops within their entry candle deserve particular attention. Freqtrade 2026.8's `_get_close_rate_for_stoploss()` applies special pricing when `trade_dur == 0`. With 5m detail, evaluations 5 or 10 minutes after entry no longer have zero-minute holding time, and they see different candle bounds. Detail mode can therefore change more than the minute component of an exit timestamp. [Source for the tested version](https://github.com/freqtrade/freqtrade/blob/2026.8/freqtrade/optimize/backtesting.py)

### Leverage Makes the Underlying Price Thresholds Smaller

Return-based thresholds apply to leveraged positions. Ignoring trading fees, funding and price discretization, their approximate underlying price distances are:

| Leverage | 6% fixed stoploss | 5% trailing activation | 1.5% trailing distance | 15% ROI |
| --- | ---: | ---: | ---: | ---: |
| 2x | 3.00% | 2.50% | 0.75% | 7.50% |
| 3x | 2.00% | 1.67% | 0.50% | 5.00% |
| 4x | 1.50% | 1.25% | 0.375% | 3.75% |
| 5x | 1.20% | 1.00% | 0.30% | 3.00% |

For BTC, for example, the trailing distance is approximately 0.3% of price, so an intrahour retracement can end a trade early. This table illustrates scale only: exact activation conditions include costs and other factors, and reported fills follow the engine's exported results. [Stoploss and leverage](https://www.freqtrade.io/en/stable/stoploss/#stoploss-and-leverage)

### Earlier Exits Change Which Later Signals Can Be Filled

Both runs allow at most 5 concurrent positions while monitoring 14 pairs. An exit inside a 5m interval may release margin and a position slot earlier, allowing another pair to enter within the same hour. A delayed exit may instead block a later opportunity. Identical 1h signals therefore do not imply identical trade counts, entry times or pair allocations. The configured pair order also affects competition for slots. [Detailed backtesting](https://www.freqtrade.io/en/stable/backtesting/#improved-backtest-accuracy)

## Data Validation and Consistent Source Candles

The original local dataset began on 2023-09-01. Earlier futures candles, mark prices and funding rates were downloaded before the experiment. This avoids presenting a run that actually starts on 2023-09-11 as if it covered all of 2023.

Within the audited interval `[2023-01-01, 2026-09-01)`, every pair has 32,136 hourly candles and 385,632 five-minute candles, with no missing or duplicate timestamps. Each pair also has the full 240-hour warmup. The largest interval between adjacent funding-rate records is 8 hours.

Complete timestamps do not guarantee consistent prices. Aggregating 5m candles to 1h reveals **44 pair-hour observations** whose OHLC differs from the original hourly files, approximately 0.0098% of 449,904 pair-hour records. Each pair's 5m file also contains 24 zero-volume candles. Inconsistencies are concentrated around periods including 2024-10-28. Rerunning the audit writes detailed mismatch records only under the ignored `analysis_outputs/` directory.

The main comparison therefore aggregates 5m data into hourly candles in a separate directory, and both runs use that internally consistent dataset. The original downloaded hourly files are not replaced. Aggregation does not repair zero-volume observations in the 5m source itself. Coverage and column-level aggregation checks are recorded in [data_audit.json](data_audit.json); input hashes for the main comparison are in [aligned_data_manifest.json](aligned_data_manifest.json).

A separate baseline run on the originally downloaded hourly candles checks the effect of this data preparation:

| Source for the 1h baseline | Trades | Net profit, USDT |
| --- | ---: | ---: |
| Originally downloaded 1h candles | 21,074 | 11,966.75 |
| The same 5m source aggregated into 1h candles | 21,074 | 11,967.01 |

Net profit differs by **0.26 USDT**. Data alignment did not materially change the baseline return in this sample. Consistent source data is nevertheless used for the main comparison to avoid mixing source-data discrepancies with simulation-resolution effects. [Original hourly reference results](original_1h_reference.json)

## Reproduction and Result Files

The backtesting image is pinned to:

```text
freqtradeorg/freqtrade@sha256:7031bca43ed7668ebf421725dd5016acade6ef88b0771db3e08c96e6d19a42db
```

Run the following from the repository root. The download script retrieves public 1h and 5m futures data, mark prices and funding rates. If older local data exists, first check that it includes the warmup from 2022-12-22. The research script runs the two backtests sequentially; raw data and backtest ZIPs remain in Git-ignored directories.

```bash
bash scripts/download_data.sh
# Use an existing crypto-research:latest image, or build it as described in the root README.
bash reports/my_strategy_1h_detail_5m/run_comparison.sh
```

The public version exports aggregate statistics by default. To inspect simulated trade details locally, explicitly run `analyze_results.py --aligned --include-trades` after the backtests. These outputs go to the ignored `analysis_outputs/backtest_analysis/` directory. Original simulation archives, full trade tables and the private runtime environment are not distributed. Fresh downloads and exchange metadata can change, so the published aggregates record this historical experiment rather than guarantee byte-for-byte reproduction. Original input hashes are retained for comparison.

The core backtest commands differ only in detail resolution:

```bash
# Baseline backtest
freqtrade backtesting --strategy MyStrategy --timeframe 1h \
  --config configs/research.example.json \
  --datadir user_data/data/binance_aligned \
  --timerange 20230101-20260901 --fee 0.0005 --cache none

# Detailed backtest: the primary signal timeframe remains 1h
freqtrade backtesting --strategy MyStrategy --timeframe 1h --timeframe-detail 5m \
  --config configs/research.example.json \
  --datadir user_data/data/binance_aligned \
  --timerange 20230101-20260901 --fee 0.0005 --cache none
```

See [run_comparison.sh](run_comparison.sh) for complete commands, configuration mounts and output paths. The main review artifacts are [summary.json](summary.json), [exit-reason statistics](by_exit_reason.csv), [annual statistics](by_year.csv), [pair statistics](by_pair.csv) and [exit-reason transitions for shared entries](matched_exit_transitions.csv). Original Freqtrade ZIPs, runtime logs and full trade records are not distributed; they can be regenerated from independently downloaded data.

All reported returns include entry and exit trading fees and the funding costs accounted for by the engine. Fills are simulated from candle price ranges without reconstructing historical order books, queue position or slippage. The strategy's exchange limit-stop settings do not guarantee real-world execution. Each 5m candle still requires intrabar path assumptions, so the detailed result remains a finer-resolution historical simulation.
