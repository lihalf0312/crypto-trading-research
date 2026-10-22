"""Analyze fresh Freqtrade exports; all deltas are detail minus baseline."""
import argparse
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
METRICS = ["total_trades", "starting_balance", "final_balance", "profit_total_abs",
           "profit_total", "winrate", "profit_factor", "profit_mean", "holding_avg_s",
           "max_drawdown_account", "max_relative_drawdown", "max_drawdown_abs", "sharpe", "sortino", "cagr",
           "trade_count_long", "trade_count_short", "rejected_signals",
           "timedout_entry_orders", "timedout_exit_orders", "canceled_trade_entries",
           "backtest_start", "backtest_end", "timeframe", "timeframe_detail"]


def load(mode):
    files = sorted((ROOT / f"user_data/backtest_results/comparison_{mode}").glob("*.zip"))
    if not files:
        raise FileNotFoundError(mode)
    path = files[-1]
    with zipfile.ZipFile(path) as archive:
        name = next(n for n in archive.namelist()
                    if n.endswith(".json") and not n.endswith("_config.json"))
        result = json.loads(archive.read(name))["strategy"]["MyStrategy"]
    trades = pd.DataFrame(result["trades"])
    for col in ["open_date", "close_date"]:
        trades[col] = pd.to_datetime(trades[col], utc=True)
    trades["fees_estimated"] = trades.amount * (
        trades.open_rate * trades.fee_open + trades.close_rate * trades.fee_close)
    trades["price_pnl"] = (trades.close_rate - trades.open_rate) * trades.amount * np.where(trades.is_short, -1, 1)
    # Funding is signed: positive = received by this position.
    residual = trades.profit_abs - (trades.price_pnl - trades.fees_estimated + trades.funding_fees)
    if residual.abs().max() > 1e-5:
        raise ValueError(f"PnL reconciliation failed: {residual.abs().max()}")
    metrics = {key: result.get(key) for key in METRICS}
    metrics.update(fees_estimated=float(trades.fees_estimated.sum()),
                   funding_fees=float(trades.funding_fees.sum()), price_pnl=float(trades.price_pnl.sum()),
                   intrahour_entries=int((trades.open_date.dt.minute != 0).sum()),
                   intrahour_exits=int((trades.close_date.dt.minute != 0).sum()),
                   avg_win_ratio=float(trades.loc[trades.profit_abs > 0, "profit_ratio"].mean()),
                   avg_loss_ratio=float(trades.loc[trades.profit_abs < 0, "profit_ratio"].mean()),
                   zero_duration_trades=int((trades.trade_duration == 0).sum()),
                   zero_duration_trailing_count=int(((trades.trade_duration == 0) &
                                                     (trades.exit_reason == "trailing_stop_loss")).sum()),
                   zero_duration_trailing_pnl=float(trades.loc[(trades.trade_duration == 0) &
                                                   (trades.exit_reason == "trailing_stop_loss"), "profit_abs"].sum()),
                   last_trade_close=str(trades.close_date.max()))
    return metrics, trades


def grouped(trades, column):
    return trades.groupby(column, dropna=False).agg(
        trades=("profit_abs", "size"), net_pnl=("profit_abs", "sum"),
        mean_ratio=("profit_ratio", "mean"), wins=("profit_abs", lambda s: int((s > 0).sum())),
        fees=("fees_estimated", "sum"), funding=("funding_fees", "sum"))


def main(aligned=False, export_trades=False):
    private_output = ROOT / "analysis_outputs/backtest_analysis"
    if export_trades:
        private_output.mkdir(parents=True, exist_ok=True)
    summary = {}
    frames = {}
    for mode in ["1h", "5m"]:
        summary[mode], frames[mode] = load(("aligned_" if aligned else "") + mode)
        if export_trades:
            frames[mode].drop(columns="orders").to_csv(private_output / f"trades_{mode}.csv", index=False)
    for field in ["exit_reason", "pair", "is_short"]:
        table = grouped(frames["1h"], field).add_suffix("_1h").join(
            grouped(frames["5m"], field).add_suffix("_5m"), how="outer").fillna(0)
        table["delta_net_pnl"] = table.net_pnl_5m - table.net_pnl_1h
        table.to_csv(HERE / f"by_{field}.csv")
    for period in ["year", "month"]:
        for trades in frames.values():
            trades[period] = trades.close_date.dt.strftime("%Y" if period == "year" else "%Y-%m")
        table = grouped(frames["1h"], period).add_suffix("_1h").join(
            grouped(frames["5m"], period).add_suffix("_5m"), how="outer").fillna(0)
        table["delta_net_pnl"] = table.net_pnl_5m - table.net_pnl_1h
        table.to_csv(HERE / f"by_{period}.csv")
    keys = ["pair", "is_short", "open_date"]
    for trades in frames.values():
        if trades.duplicated(keys).any():
            raise ValueError("Ambiguous entry match")
    matched = frames["1h"].merge(frames["5m"], on=keys, how="outer", suffixes=("_1h", "_5m"), indicator=True)
    both = matched[matched._merge == "both"].copy()
    both["delta_net_pnl"] = both.profit_abs_5m - both.profit_abs_1h
    both["delta_ratio"] = both.profit_ratio_5m - both.profit_ratio_1h
    shared_delta = float(both.delta_net_pnl.sum())
    only_1h = float(matched.loc[matched._merge == "left_only", "profit_abs_1h"].sum())
    only_5m = float(matched.loc[matched._merge == "right_only", "profit_abs_5m"].sum())
    summary["matching"] = dict(
        common_entries=len(both), only_1h=int((matched._merge == "left_only").sum()),
        only_5m=int((matched._merge == "right_only").sum()),
        common_entry_pnl_delta=shared_delta, only_1h_pnl=only_1h, only_5m_pnl=only_5m,
        unmatched_delta=only_5m - only_1h,
        changed_exit_reason=int((both.exit_reason_1h != both.exit_reason_5m).sum()),
        changed_exit_rate=int((~np.isclose(both.close_rate_1h, both.close_rate_5m, rtol=1e-10, atol=1e-8)).sum()),
        changed_open_rate=int((~np.isclose(both.open_rate_1h, both.open_rate_5m, rtol=1e-10, atol=1e-8)).sum()),
        changed_stake=int((~np.isclose(both.stake_amount_1h, both.stake_amount_5m, rtol=1e-10, atol=1e-8)).sum()),
        detail_better=int((both.delta_net_pnl > 1e-6).sum()),
        baseline_better=int((both.delta_net_pnl < -1e-6).sum()))
    expected = summary["5m"]["profit_total_abs"] - summary["1h"]["profit_total_abs"]
    assert abs(shared_delta + only_5m - only_1h - expected) < 1e-5
    transitions = both.groupby(["exit_reason_1h", "exit_reason_5m"]).agg(
        trades=("delta_net_pnl", "size"), delta_net_pnl=("delta_net_pnl", "sum"),
        mean_delta_ratio=("delta_ratio", "mean"))
    transitions.to_csv(HERE / "matched_exit_transitions.csv")
    if export_trades:
        both.drop(columns=[c for c in both if c.startswith("orders_")]).sort_values("delta_net_pnl").to_csv(
            private_output / "matched_trades.csv", index=False)
        sample_columns = keys + [f"{name}_{mode}" for name in ["open_rate", "close_rate", "close_date", "exit_reason", "profit_abs", "profit_ratio"] for mode in ["1h", "5m"]] + ["delta_net_pnl"]
        pd.concat([both.nsmallest(10, "delta_net_pnl"), both.nlargest(10, "delta_net_pnl")]).drop_duplicates(keys)[sample_columns].to_csv(
            private_output / "matched_examples.csv", index=False)
    summary["pnl_delta"] = expected
    summary["data_variant"] = "1h aggregated from the same 5m data" if aligned else "original downloaded 1h and 5m"
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    plot(frames, summary)


def plot(frames, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(3, 1, figsize=(12, 12), constrained_layout=True)
    days = pd.date_range("2023-01-01", "2026-09-01", tz="UTC", freq="D")
    for mode, color in [("1h", "#2563eb"), ("5m", "#e56b23")]:
        trades = frames[mode]
        daily = trades.set_index("close_date").profit_abs.resample("D").sum().reindex(days, fill_value=0)
        equity = summary[mode]["starting_balance"] + daily.cumsum()
        axes[0].plot(days, equity, label=f"1h signals / {mode} execution", color=color)
        # Include starting capital in the running peak.
        peak = equity.cummax().clip(lower=summary[mode]["starting_balance"])
        axes[1].plot(days, (equity / peak - 1) * 100, color=color, label=mode)
    axes[0].set_yscale("log")
    axes[0].set(title="Realized equity at daily close (not mark-to-market)", ylabel="USDT (log scale)")
    axes[0].legend()
    axes[1].set(title="Drawdown of daily realized equity", ylabel="%")
    table = pd.read_csv(HERE / "by_exit_reason.csv", index_col=0)
    table[["net_pnl_1h", "net_pnl_5m"]].rename(columns={"net_pnl_1h": "1h", "net_pnl_5m": "5m"}).plot.bar(
        ax=axes[2], color=["#2563eb", "#e56b23"], rot=0)
    axes[2].set(title="Net PnL by exit reason", ylabel="USDT", xlabel="")
    fig.savefig(HERE / "comparison.png", dpi=170)
    plt.close(fig)
    case_path = HERE / "case_btc_20240228.csv"
    if case_path.exists():
        case = pd.read_csv(case_path, parse_dates=["date"])
        fig, ax = plt.subplots(figsize=(12, 4.5), constrained_layout=True)
        ax.vlines(case.date, case.low, case.high, color="#64748b", alpha=0.65, label="5m high-low range")
        ax.plot(case.date, case.close, color="#64748b", linewidth=1, label="5m close")
        for date, rate, color, label in [
            ("2024-02-28 16:30", 61659.5, "#e56b23", "5m trailing exit: 61,659.5 (+4.63%)"),
            ("2024-02-28 17:00", 62925.5, "#2563eb", "1h ROI exit: 62,925.5 (+15.00%)"),
        ]:
            time = pd.Timestamp(date, tz="UTC")
            ax.scatter([time], [rate], color=color, s=65, label=label, zorder=3)
            ax.axvline(time, color=color, linestyle="--", alpha=0.5)
        import matplotlib.dates as mdates
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=case.date.dt.tz))
        ax.set(title="BTC long opened at 61,000 on 2024-02-28 16:00 UTC", xlabel="UTC (exit markers use candle start times)", ylabel="USDT")
        ax.legend(loc="lower left", fontsize=9)
        fig.savefig(HERE / "case_btc_20240228.png", dpi=170)
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--aligned", action="store_true", help="Use internally consistent 1h/5m source data")
    parser.add_argument("--include-trades", action="store_true", help="Write optional simulated trade details only under ignored analysis_outputs/")
    args = parser.parse_args()
    main(args.aligned, args.include_trades)
