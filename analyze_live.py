"""Analyze closed Freqtrade trades without modifying the input database.

The demo is entirely synthetic and is not a strategy performance sample.
Only explicitly selected columns are read; individual trades are never printed.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import statistics
import sys
from collections import defaultdict
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

FIELDS = ("id", "pair", "is_open", "open_date", "close_date", "close_profit", "close_profit_abs", "is_short")


class AnalysisError(ValueError):
    """A safe user-facing validation error without database contents or paths."""


def utc_time(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise AnalysisError("A trade contains an invalid timestamp.") from exc
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def normalize(rows):
    result = []
    for raw in rows:
        row = dict(raw)
        if not set(FIELDS).issubset(row):
            raise AnalysisError("The input is missing required trade columns; see examples/trades_schema.sql.")
        if row["is_open"] not in (0, 1, False, True) or row["is_short"] not in (0, 1, False, True):
            raise AnalysisError("Trade direction and open flags must be 0 or 1.")
        if row["is_open"]:
            continue
        for field in ("close_profit", "close_profit_abs"):
            try:
                row[field] = float(row[field])
            except (ValueError, TypeError) as exc:
                raise AnalysisError("A closed trade contains an invalid profit value.") from exc
            if not math.isfinite(row[field]):
                raise AnalysisError("Profit values must be finite numbers.")
        row["open_date"], row["close_date"] = utc_time(row["open_date"]), utc_time(row["close_date"])
        if row["close_date"] < row["open_date"] or not isinstance(row["pair"], str) or not row["pair"]:
            raise AnalysisError("A trade has invalid dates or a missing pair.")
        result.append(row)
    return sorted(result, key=lambda r: (r["close_date"], r["id"]))


def read_closed_trades(db_path):
    """Use SQLite mode=ro and one SELECT snapshot; never copy or update a database."""
    try:
        path = Path(db_path).expanduser().resolve(strict=True)
        if not path.is_file():
            raise OSError
    except (OSError, RuntimeError, ValueError) as exc:
        raise AnalysisError("Input database does not exist or is not a regular file.") from exc
    try:
        uri = "file:" + quote(path.as_posix(), safe="/") + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True, timeout=5)) as conn:
            conn.execute("PRAGMA query_only = ON")
            columns = {r[1] for r in conn.execute("PRAGMA table_info(trades)")}
            if not set(FIELDS).issubset(columns):
                raise AnalysisError("The trades table lacks required columns; see examples/trades_schema.sql.")
            conn.row_factory = sqlite3.Row
            selected = ", ".join('"' + name + '"' for name in FIELDS)
            rows = conn.execute(f"SELECT {selected} FROM trades WHERE is_open = 0 ORDER BY close_date, id").fetchall()
    except sqlite3.Error as exc:
        raise AnalysisError("Could not read the SQLite trades table. Check access, schema and lock state.") from exc
    return normalize(rows)


def demo_trades():
    """Handmade fixtures; no values or records originate from any account."""
    profits = [12, -8, 5, -4, 18, -6, 9, -3, 2, -5, 0, 7]
    rows = []
    for index, pnl in enumerate(profits):
        opened = datetime(2024, 1, 2, 8, tzinfo=timezone.utc) + timedelta(days=index * 2)
        rows.append(dict(id=index + 1, pair=f"DEMO_{'A' if index % 3 else 'B'}/USDT:USDT",
                         is_open=0, open_date=opened.isoformat(),
                         close_date=(opened + timedelta(hours=4)).isoformat(),
                         close_profit=pnl / 100, close_profit_abs=pnl, is_short=index % 2))
    return rows


def mean(values):
    return statistics.fmean(values) if values else None


def safe_ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def trade_metrics(rows):
    wins = [r for r in rows if r["close_profit_abs"] > 0]
    losses = [r for r in rows if r["close_profit_abs"] < 0]
    avg_win = mean([r["close_profit_abs"] for r in wins])
    avg_loss = mean([r["close_profit_abs"] for r in losses])
    gross_win = math.fsum(r["close_profit_abs"] for r in wins)
    gross_loss = -math.fsum(r["close_profit_abs"] for r in losses)
    return dict(trades=len(rows), wins=len(wins), losses=len(losses), draws=len(rows) - len(wins) - len(losses),
                net_pnl=math.fsum(r["close_profit_abs"] for r in rows),
                win_rate=safe_ratio(len(wins), len(rows)),
                average_profit_ratio=mean([r["close_profit"] for r in rows]),
                average_win=avg_win, average_loss=avg_loss,
                average_win_ratio=mean([r["close_profit"] for r in wins]),
                average_loss_ratio=mean([r["close_profit"] for r in losses]),
                expectancy=safe_ratio(gross_win - gross_loss, len(rows)),
                profit_factor=safe_ratio(gross_win, gross_loss),
                payoff_ratio=safe_ratio(avg_win, abs(avg_loss)) if avg_win is not None and avg_loss is not None else None,
                breakeven_win_rate=safe_ratio(abs(avg_loss), avg_win + abs(avg_loss)) if avg_win is not None and avg_loss is not None else None)


def attribution(rows, field):
    groups = defaultdict(list)
    for row in rows:
        key = ("SHORT" if row["is_short"] else "LONG") if field == "side" else row[field]
        groups[key].append(row)
    return {key: trade_metrics(group) for key, group in sorted(groups.items())}


def analyze(rows, initial_capital, start=None, end=None, synthetic=False):
    if not math.isfinite(initial_capital) or initial_capital <= 0:
        raise AnalysisError("Initial capital must be a finite positive number.")
    if start and end and start > end:
        raise AnalysisError("Start date must not be after end date.")
    rows = normalize(rows)
    rows = [r for r in rows if (start is None or r["close_date"].date() >= start)
            and (end is None or r["close_date"].date() <= end)]
    first = start or (rows[0]["close_date"].date() if rows else None)
    last = end or (rows[-1]["close_date"].date() if rows else None)
    buckets = defaultdict(list)
    for row in rows:
        buckets[row["close_date"].date()].append(row["close_profit_abs"])
    daily, equity, peak = [], initial_capital, initial_capital
    current = first
    while current is not None and last is not None and current <= last:
        pnl = math.fsum(buckets[current])
        day_return = pnl / equity if equity > 0 else None
        equity += pnl
        peak = max(peak, equity)
        daily.append(dict(date=current.isoformat(), pnl=pnl, equity=equity,
                          return_ratio=day_return, drawdown=equity / peak - 1))
        current += timedelta(days=1)
    returns = [r["return_ratio"] for r in daily if r["return_ratio"] is not None]
    valid_returns = len(returns) == len(daily) and all(r["equity"] > 0 for r in daily)
    volatility = statistics.stdev(returns) if len(returns) >= 2 else None
    downside = math.sqrt(statistics.fmean(min(r, 0) ** 2 for r in returns)) if returns else None
    mean_return = mean(returns)
    metrics = trade_metrics(rows)
    metrics.update(initial_capital=initial_capital, final_realized_equity=equity,
                   total_return=metrics["net_pnl"] / initial_capital,
                   observation_days=len(daily), mean_daily_return=mean_return,
                   daily_volatility=volatility,
                   annualized_sharpe=mean_return / volatility * math.sqrt(365) if valid_returns and volatility else None,
                   annualized_sortino=mean_return / downside * math.sqrt(365) if valid_returns and downside else None,
                   max_daily_realized_drawdown=min((r["drawdown"] for r in daily), default=0),
                   best_daily_return=max(returns, default=None), worst_daily_return=min(returns, default=None))
    concentration, stress = {}, {}
    ranked = sorted(daily, key=lambda r: r["pnl"], reverse=True)
    for n in (1, 3, 5):
        amount = math.fsum(r["pnl"] for r in ranked[:n])
        concentration[str(n)] = dict(actual_days=min(n, len(daily)), pnl=amount,
                                     share_of_net_profit=amount / metrics["net_pnl"] if metrics["net_pnl"] > 0 else None)
    for n in (0, 1, 3, 5):
        stressed = metrics["net_pnl"] - math.fsum(r["pnl"] for r in ranked[:n])
        stress[str(n)] = dict(actual_days_removed=min(n, len(daily)), pnl=stressed, return_ratio=stressed / initial_capital)
    best = ranked[0]["date"] if ranked else None
    best_rows = [r for r in rows if r["close_date"].date().isoformat() == best]
    return dict(metadata=dict(source="synthetic_demo" if synthetic else "user_supplied_sqlite",
                              synthetic=True if synthetic else None, timezone="UTC", start=first.isoformat() if first else None,
                              end_inclusive=last.isoformat() if last else None,
                              equity_basis="closed trades only; excludes open PnL and cash flows",
                              annualization_days=365,
                              undefined_metrics="null; profit factor is null when there are no losses"),
                metrics=metrics, daily=daily, by_pair=attribution(rows, "pair"), by_side=attribution(rows, "side"),
                profit_concentration=concentration, remove_best_days=stress,
                best_day=dict(date=best, by_pair=attribution(best_rows, "pair"), by_side=attribution(best_rows, "side")))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--db", help="SQLite input path; fallback: FREQTRADE_ANALYSIS_DB")
    source.add_argument("--demo", action="store_true", help="Use handmade synthetic trades in memory")
    parser.add_argument("--synthetic-input", action="store_true", help="Explicitly label a known synthetic SQLite input; does not anonymize data")
    parser.add_argument("--initial-capital", type=float, help="Capital at the beginning of the selected period")
    parser.add_argument("--start", type=date.fromisoformat, help="Inclusive UTC date YYYY-MM-DD")
    parser.add_argument("--end", type=date.fromisoformat, help="Inclusive UTC date YYYY-MM-DD")
    parser.add_argument("--output", type=Path, help="Explicit JSON output; use ignored analysis_outputs/")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--show-daily", action="store_true", help="Include daily aggregates in text output")
    args = parser.parse_args(argv)
    try:
        db = args.db or (None if args.demo else os.environ.get("FREQTRADE_ANALYSIS_DB"))
        if not args.demo and not db:
            raise AnalysisError("Specify --demo, --db, or FREQTRADE_ANALYSIS_DB.")
        capital = args.initial_capital
        if capital is None and args.demo:
            capital = 1000.0
        if capital is None:
            value = os.environ.get("FREQTRADE_INITIAL_CAPITAL")
            try:
                capital = float(value) if value is not None else None
            except ValueError as exc:
                raise AnalysisError("FREQTRADE_INITIAL_CAPITAL must be numeric.") from exc
        if capital is None:
            raise AnalysisError("Specify --initial-capital or FREQTRADE_INITIAL_CAPITAL for SQLite analysis.")
        rows = demo_trades() if args.demo else read_closed_trades(db)
        report = analyze(rows, capital, args.start, args.end, synthetic=args.demo or args.synthetic_input)
        if db and args.synthetic_input:
            report["metadata"]["source"] = "synthetic_sqlite"
        encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
        if args.output:
            try:
                target = args.output.expanduser().resolve()
                if db and target == Path(db).expanduser().resolve():
                    raise AnalysisError("Output must not overwrite the input database.")
                target.parent.mkdir(parents=True, exist_ok=True)
                # Refuse to replace any existing file, including linked databases.
                with target.open("x") as output:
                    output.write(encoded)
            except OSError as exc:
                raise AnalysisError("Could not create output; choose a writable, unused output file.") from exc
        if args.format == "json":
            print(encoded, end="")
        else:
            print("SYNTHETIC DATA — not strategy performance" if args.demo or args.synthetic_input else "USER-SUPPLIED DATABASE — private analysis")
            for name, value in report["metrics"].items():
                print(f"{name}: {value if value is not None else 'N/A'}")
            for name in ("by_pair", "by_side", "profit_concentration", "remove_best_days", "best_day"):
                print(name + ": " + json.dumps(report[name], allow_nan=False))
            if args.show_daily:
                print("daily: " + json.dumps(report["daily"], allow_nan=False))
        return 0
    except AnalysisError as exc:
        print("Analysis error: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
