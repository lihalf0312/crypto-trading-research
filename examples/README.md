# Synthetic analysis examples

The example trades are handmade fixtures with `DEMO_A` and `DEMO_B` symbols.
They do not come from an exchange, an account, `MyStrategy`, or `TrendFollowingCTA`.
They demonstrate the analysis interface and test arithmetic; their statistics are
not investment or strategy performance results.

The analyzer needs only the eight columns defined in [trades_schema.sql](trades_schema.sql).
Timestamps use UTC. `close_profit` is a net return ratio and `close_profit_abs` is
net realized PnL in the quote currency; the analyzer does not subtract fees again.
Closed trades have `is_open = 0`. Other columns in an existing Freqtrade database
are ignored. No database file is committed.

From the repository root, with Python 3.10 or later:

```bash
python3 analyze_live.py --demo
python3 scripts/generate_demo_trades.py --output analysis_outputs/synthetic.sqlite
python3 analyze_live.py --db analysis_outputs/synthetic.sqlite \
  --synthetic-input --initial-capital 1000 --start 2024-01-01 --end 2024-01-31 \
  --output analysis_outputs/synthetic_summary.json
python3 -m unittest discover -s tests -v
```

`--db` can instead be supplied with `FREQTRADE_ANALYSIS_DB`; initial capital can
be supplied with `FREQTRADE_INITIAL_CAPITAL`. Environment values and input paths
are not echoed by the analyzer. `--demo` ignores database environment settings.
Initial capital is mandatory for database input; it means capital at the start
of the selected analysis window. The demo alone defaults to fictional 1,000 USDT.
`--synthetic-input` labels a known synthetic SQLite fixture; it does not anonymize
actual records. Without that label, SQLite input provenance is unknown
(`synthetic: null`), rather than asserted to be live or synthetic.

SQLite is opened with `mode=ro` and `query_only`. One SELECT reads only the
required closed-trade columns. No backup database or per-trade export is created.
Output files require an explicit path and must not already exist. Store runtime
outputs under ignored `analysis_outputs/`; reports from a real database remain
private even if they contain only aggregates. For an active WAL-mode database,
normal SQLite reader access to its WAL/SHM state is still required.

Daily equity is initial capital plus cumulative closed-trade PnL. It does not
include floating PnL, deposits or withdrawals. Days without closes are included
between the selected start and end dates. Without explicit dates, the window
runs from the first to the last selected close. Maximum drawdown includes initial
capital as the first peak. Sharpe uses sample daily standard deviation and
365-day annualization; Sortino uses the RMS of negative daily returns, with zero
for nonnegative days. These ratios are disabled for nonpositive equity.

Undefined ratios are JSON `null`, including profit factor when there are no
losing trades. Profit-concentration percentages are undefined for nonpositive
total PnL. Removing the best days is a mechanical concentration stress check,
not a portfolio simulation with trades rerun after removing those days.
