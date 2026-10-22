# Cryptocurrency Trading Research

This repository publishes the complete **MyStrategy** source from my Freqtrade
project, together with a historical execution-resolution study, public market
research, and a SQLite trade-analysis tool. The trading signals, leverage map,
risk parameters and exit rules are included in full. Credentials, account
records and private deployment configuration are excluded.

The main research finding is that a strong hourly backtest did not survive
five-minute execution refinement. The report examines exit pricing, trailing
stops, ROI, portfolio-slot reuse and the resulting capital path, including the
negative result.

## Strategies and evidence

| Artifact | Purpose | Published result |
| --- | --- | --- |
| [MyStrategy source](user_data/strategies/my_strategy.py) | Complete strategy implementation | SMA240 and EMA10 trend filters; long and short futures |
| [MyStrategy study](reports/my_strategy_1h_detail_5m/README.md) | Same 1h signals, 1h versus 5m execution simulation | +2393.40% versus −80.19%; maximum relative drawdown 33.96% versus 87.18% |
| [TrendFollowingCTA](user_data/strategies/trend_following_cta.py) and [baseline report](results/cta_backtest_summary.md) | Separate illustrative EMA/ATR baseline | 921 trades, −6.05%, 13.22% maximum relative drawdown |
| [Market research notebook](user_data/notebooks/backtest_research.ipynb) | Data quality, log returns, tails and realized volatility | Descriptive BTC market statistics |
| [Analysis demo](examples/README.md) | Reproducible interface and arithmetic checks | Entirely synthetic fixtures; no strategy performance claim |

All performance figures above are **historical simulations**, not live account
returns. The MyStrategy study covers 14 USDT perpetual pairs from 2023-01-01 to
2026-09-01 UTC with 240 hours of warmup, 500 USDT simulated initial capital and
a 100 USDT target stake. Both runs use the same 1h candles aggregated from the
same 5m source. The detailed run stopped opening trades after 2024-03-08 when
its remaining simulated balance fell below the configured entry requirement.
The CTA baseline covers BTC alone from 2023-09-11 to 2026-09-01 with a different
capital and portfolio setup. These are separate experiments, not a controlled
ranking of the two strategies. The notebook figures describe the market only.

## MyStrategy rules

Indicators are computed on **1h** candles. A positive-volume candle enters long
when its close is above both SMA240 and EMA10, and short when below both. This is
a persistent trend condition, not only a moving-average crossing signal.
The strategy produces no indicator-based exits: fixed stoploss, trailing stop
and minimal ROI control exits.

| Setting | Source value |
| --- | --- |
| Minimal ROI | 15% from minute zero |
| Stoploss | −6% |
| Trailing | Enabled after 5% profit; 1.5% trailing distance |
| Warmup | 240 candles |
| Leverage targets | BTC 5x, ETH 4x, SOL/XRP/BNB 3x, other pairs 2x; capped by exchange maximum |
| Orders | Limit entry/exit; exchange stoploss settings retained |

The source is copied without modifying its logic or parameters. Its legacy
comment next to `trailing_stop_positive_offset` says “Disabled / not configured”;
the actual flags enable trailing. Profit and loss thresholds are affected by
leverage, fees and framework pricing rules. Configuration overrides remain a
Freqtrade feature; [research.example.json](configs/research.example.json) fixes
the published experiment's noncredential settings without private account data.

## Layout

```text
analyze_live.py                         Read-only SQLite analysis and in-memory demo
configs/research.example.json           Credential-free historical research settings
examples/                              Minimal SQL schema and synthetic usage
scripts/                               Public data download and synthetic fixture generation
tests/                                 Analysis arithmetic and input-safety checks
user_data/strategies/my_strategy.py     Complete real strategy
user_data/strategies/trend_following_cta.py  Separate illustrative baseline
user_data/notebooks/                   Public market-data notebook
reports/my_strategy_1h_detail_5m/        Simulation study, aggregate evidence and research code
results/                               Existing CTA summary and market figures
```

## Run the analysis demo

The analyzer and its tests use only the Python standard library, Python 3.10+:

```bash
git clone https://github.com/lihalf0312/crypto-trading-research.git
cd crypto-trading-research
python3 analyze_live.py --demo
python3 -m unittest discover -s tests -v
```

To exercise SQLite input with **synthetic** data:

```bash
python3 scripts/generate_demo_trades.py --output analysis_outputs/synthetic.sqlite
python3 analyze_live.py --db analysis_outputs/synthetic.sqlite \
  --synthetic-input --initial-capital 1000 --start 2024-01-01 --end 2024-01-31 \
  --output analysis_outputs/synthetic_summary.json
```

The analyzer supports realized equity, daily drawdown and returns, Sharpe and
Sortino, win/loss statistics, profit factor, payoff, expectancy, profit
concentration, removal of the best days, and attribution by pair and direction.
It reads only closed trades in one SQLite SELECT using `mode=ro` and `query_only`;
it does not back up the input or export individual records. Input can also be
provided through `FREQTRADE_ANALYSIS_DB` and `FREQTRADE_INITIAL_CAPITAL`.
Database analysis requires an explicitly supplied initial capital.

The schema, timezone, observation-window and metric conventions are described
in [examples/README.md](examples/README.md). Equity excludes open PnL and cash
flows. A private database's analysis output remains private even when aggregated;
runtime reports belong in ignored `analysis_outputs/`.

## Independent research environment

The Dockerfile pins the Freqtrade base by digest and adds Matplotlib. It does
not embed project files, private configuration or credentials. The Compose
service mounts this repository read-only and defaults to the synthetic demo.

```bash
# Use an existing crypto-research:latest image, or build this research image.
docker build -f Dockerfile.research -t crypto-research:latest .
docker compose run --rm --no-deps research analyze_live.py --demo
docker compose run --rm --no-deps research -m unittest discover -s tests -v
docker compose run --rm --no-deps research scripts/validate_strategy.py
```

Validation details are recorded in [VALIDATION.md](VALIDATION.md). The research
commands do not require exchange credentials or a running trading service.

## Reproduce the historical study

```bash
# Downloads public 1h/5m futures candles plus mark/funding data required by Freqtrade.
bash scripts/download_data.sh
# Sequential backtests, data audit, aggregate analysis and native pricing-rule check.
bash reports/my_strategy_1h_detail_5m/run_comparison.sh
```

The study uses Freqtrade 2026.8, `MyStrategy`, `--timeframe 1h`, a 0.05% fee per
side and `--cache none`. Only the second run adds `--timeframe-detail 5m`.
The report distinguishes maximum relative drawdown from the relative drawdown
associated with the largest absolute loss interval. It also separates matched
entry PnL changes from the different trade sets and later inactivity.

Market files, original ZIPs, logs and full trade tables are not distributed.
Public artifacts retain historical simulation aggregates and input hashes.
Fresh downloads and current exchange precision/limits can change results; the
recorded historical figures are not a promise of exact reproduction.
See the [full report](reports/my_strategy_1h_detail_5m/README.md) for assumptions,
the BTC pricing example and the shared-entry accounting identity.

The existing notebook uses separately downloaded BTC 5m public candles at
`user_data/data/futures/BTC_USDT_USDT-5m-futures.feather`. To prepare that optional
market-only input, run the download script with
`--pairs BTC/USDT:USDT --datadir /freqtrade/user_data/data`; then run the notebook
from the repository root in the research environment. Existing market figures
are [return distribution](results/return_distribution.png) and
[realized volatility](results/realized_volatility.png).

## Publication boundary

The strategy Alpha is public. The following remain excluded at any directory
depth: API keys, tokens, passwords and private keys; private configuration and
backups; real databases and WAL/SHM files; account balances and real execution
records; logs; raw market datasets and private backtest archives. The only
database fixture is generated from explicitly synthetic code at runtime.

`.gitignore` protects common sensitive paths, and `.dockerignore` excludes runtime
material from the build context. Ignoring a file does not remove it from existing
Git history. Repository review must inspect tracked files, the index and history
before publication; do not add runtime outputs with `git add -f`.
