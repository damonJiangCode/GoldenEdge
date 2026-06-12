from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xau.mr.v1.engine import (  # noqa: E402
    EngineConfig as MRConfig,
    MeanReversionV1Engine,
)
from xau.vb.v1.engine import (  # noqa: E402
    EngineConfig as VBConfig,
    VolatilityBreakoutV1Engine,
)

MARKET_ROOT = REPO_ROOT / "xau" / "marketdata"
REPORT_ROOT = REPO_ROOT / "xau" / "reports" / "regime_baseline"
YEARS = list(range(2015, 2026))
ACCOUNT_INITIAL_BALANCE = 2000.0
STRATEGY_SIMULATION_INITIAL_BALANCE = ACCOUNT_INITIAL_BALANCE
PORTFOLIO_INITIAL_BALANCE = ACCOUNT_INITIAL_BALANCE
DEFAULT_SIDE_UNITS = 0.01 * 100
DEFAULT_LEVERAGE = 100.0

UNIFIED_COLUMNS = [
    "trade_id",
    "strategy",
    "engine_version",
    "symbol",
    "timeframe",
    "side",
    "signal_time_utc",
    "entry_time_utc",
    "exit_time_utc",
    "entry_price",
    "exit_price",
    "initial_sl",
    "final_sl",
    "exit_reason",
    "gross_pnl",
    "commission",
    "swap",
    "net_pnl",
    "pnl_result",
    "initial_risk_price",
    "initial_risk_money",
    "r_multiple",
    "holding_bars",
    "holding_hours",
    "entry_atr",
    "entry_atr_ratio",
    "entry_spread_points",
    "entry_adx",
    "entry_h1_adx",
    "entry_h1_adx_slope",
    "entry_ema_fast",
    "entry_ema_slow",
    "entry_ema_slope",
    "entry_donchian_high",
    "entry_donchian_low",
    "entry_donchian_width_atr",
    "entry_bb_width_atr",
    "entry_close_to_ema_atr",
    "entry_range_efficiency",
    "regime_trend_strength",
    "regime_volatility",
    "regime_direction",
    "regime_strategy_fit",
    "adx_bucket",
    "atr_ratio_bucket",
    "spread_bucket",
    "session_utc",
    "weekday",
    "is_win",
    "return_pct_on_initial_balance",
    "max_favorable_excursion_r",
    "max_adverse_excursion_r",
    "post_entry_holding_bucket",
    "sl_update_count",
    "trail_updates_json",
]


def finite(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def bucket_adx(value: Any) -> str:
    adx = finite(value, float("nan"))
    if math.isnan(adx):
        return ""
    if adx < 20.0:
        return "adx_lt20"
    if adx < 25.0:
        return "adx_20_25"
    if adx < 30.0:
        return "adx_25_30"
    return "adx_ge30"


def bucket_atr_ratio(value: Any) -> str:
    ratio = finite(value, float("nan"))
    if math.isnan(ratio):
        return ""
    if ratio < 0.8:
        return "atrr_lt0_8"
    if ratio < 1.0:
        return "atrr_0_8_1_0"
    if ratio < 1.2:
        return "atrr_1_0_1_2"
    return "atrr_ge1_2"


def bucket_spread(value: Any) -> str:
    spread = finite(value, float("nan"))
    if math.isnan(spread):
        return ""
    if spread <= 15.0:
        return "spread_le15"
    if spread <= 30.0:
        return "spread_15_30"
    return "spread_gt30"


def holding_bucket(bars: int) -> str:
    if bars < 8:
        return "hold_1_7"
    if bars < 25:
        return "hold_8_24"
    return "hold_25_plus"


def blank_unified_row() -> dict[str, Any]:
    return {column: "" for column in UNIFIED_COLUMNS}


def vb_unified_rows(report: dict[str, Any], year: int) -> list[dict[str, Any]]:
    rows = []
    sl_mult = finite(report["params"]["sl_atr_mult"])
    units = DEFAULT_SIDE_UNITS
    for idx, trade in enumerate(report["trade_details"], start=1):
        row = blank_unified_row()
        entry = pd.Timestamp(trade["entry_time"])
        exit_time = pd.Timestamp(trade["exit_time"])
        side = str(trade["side"])
        entry_price = finite(trade["entry_price"])
        initial_risk_price = finite(trade["entry_atr"]) * sl_mult
        initial_sl = (
            entry_price - initial_risk_price
            if side == "long"
            else entry_price + initial_risk_price
        )
        initial_risk_money = initial_risk_price * units
        commission = finite(trade["entry_commission"]) + finite(
            trade["exit_commission"]
        )
        row.update(
            {
                "trade_id": f"VB_volatility_breakout_v1_{year}_{idx:04d}",
                "strategy": "VB",
                "engine_version": "volatility_breakout_v1",
                "symbol": "XAUUSD",
                "timeframe": "H4",
                "side": side,
                "signal_time_utc": trade["signal_time"],
                "entry_time_utc": trade["entry_time"],
                "exit_time_utc": trade["exit_time"],
                "entry_price": entry_price,
                "exit_price": trade["exit_price"],
                "initial_sl": initial_sl,
                "final_sl": trade["sl"],
                "exit_reason": trade["exit_reason"],
                "gross_pnl": trade["gross_pnl"],
                "commission": commission,
                "swap": trade["swap_total"],
                "net_pnl": trade["net_pnl"],
                "pnl_result": trade["pnl_result"],
                "initial_risk_price": initial_risk_price,
                "initial_risk_money": initial_risk_money,
                "r_multiple": finite(trade["net_pnl"]) / initial_risk_money
                if initial_risk_money > 0.0
                else 0.0,
                "holding_bars": trade["holding_bars"],
                "holding_hours": (exit_time - entry).total_seconds() / 3600.0,
                "entry_atr": trade["entry_atr"],
                "entry_atr_ratio": trade["entry_atr_ratio"],
                "entry_h1_adx": trade["entry_h1_adx"],
                "adx_bucket": bucket_adx(trade["entry_h1_adx"]),
                "atr_ratio_bucket": bucket_atr_ratio(trade["entry_atr_ratio"]),
                "session_utc": f"{entry.hour:02d}:00",
                "weekday": entry.weekday(),
                "is_win": finite(trade["net_pnl"]) > 0.0,
                "return_pct_on_initial_balance": finite(trade["net_pnl"])
                / ACCOUNT_INITIAL_BALANCE
                * 100.0,
                "post_entry_holding_bucket": holding_bucket(
                    int(trade["holding_bars"])
                ),
                "sl_update_count": trade["sl_update_count"],
                "trail_updates_json": json.dumps(
                    trade.get("trail_updates", []), separators=(",", ":")
                ),
            }
        )
        rows.append(row)
    return rows


def mr_unified_rows(report: dict[str, Any], year: int) -> list[dict[str, Any]]:
    rows = []
    for idx, trade in enumerate(report["trade_details"], start=1):
        row = blank_unified_row()
        entry = pd.Timestamp(trade["entry_time"])
        exit_time = pd.Timestamp(trade["exit_time"])
        commission = finite(trade["entry_commission"]) + finite(
            trade["exit_commission"]
        )
        spread = trade["entry_spread_points"]
        row.update(
            {
                "trade_id": f"MR_mean_reversion_v1_{year}_{idx:04d}",
                "strategy": "MR",
                "engine_version": "mean_reversion_v1",
                "symbol": "XAUUSD",
                "timeframe": "M15",
                "side": trade["side"],
                "signal_time_utc": trade["signal_time"],
                "entry_time_utc": trade["entry_time"],
                "exit_time_utc": trade["exit_time"],
                "entry_price": trade["entry_price"],
                "exit_price": trade["exit_price"],
                "initial_sl": trade["initial_sl"],
                "final_sl": trade["sl"],
                "exit_reason": trade["exit_reason"],
                "gross_pnl": trade["gross_pnl"],
                "commission": commission,
                "swap": trade["swap_total"],
                "net_pnl": trade["net_pnl"],
                "pnl_result": trade["pnl_result"],
                "initial_risk_price": trade["initial_risk_price"],
                "initial_risk_money": trade["initial_risk_money"],
                "r_multiple": trade["r_multiple"],
                "holding_bars": trade["holding_bars"],
                "holding_hours": (exit_time - entry).total_seconds() / 3600.0,
                "entry_atr": trade["entry_atr"],
                "entry_atr_ratio": trade["entry_atr_ratio"],
                "entry_spread_points": spread,
                "entry_h1_adx": trade["entry_h1_adx"],
                "adx_bucket": bucket_adx(trade["entry_h1_adx"]),
                "atr_ratio_bucket": bucket_atr_ratio(trade["entry_atr_ratio"]),
                "spread_bucket": bucket_spread(spread),
                "session_utc": f"{entry.hour:02d}:00",
                "weekday": entry.weekday(),
                "is_win": finite(trade["net_pnl"]) > 0.0,
                "return_pct_on_initial_balance": finite(trade["net_pnl"])
                / ACCOUNT_INITIAL_BALANCE
                * 100.0,
                "post_entry_holding_bucket": holding_bucket(
                    int(trade["holding_bars"])
                ),
                "sl_update_count": trade["sl_update_count"],
                "trail_updates_json": "[]",
            }
        )
        rows.append(row)
    return rows


def combine_equity(
    vb_report: dict[str, Any], mr_report: dict[str, Any]
) -> list[dict[str, Any]]:
    sleeves = []
    for strategy, report in (("VB", vb_report), ("MR", mr_report)):
        frame = pd.DataFrame(report["equity_series"])
        frame["time"] = pd.to_datetime(frame["time"], utc=True)
        frame.set_index("time", inplace=True)
        frame = frame[
            [
                "balance",
                "equity",
                "open_position",
                "used_margin",
                "free_margin",
                "margin_level_pct",
            ]
        ].rename(
            columns={
                "balance": f"{strategy.lower()}_balance",
                "equity": f"{strategy.lower()}_equity",
                "open_position": f"{strategy.lower()}_open_position",
                "used_margin": f"{strategy.lower()}_used_margin",
                "free_margin": f"{strategy.lower()}_free_margin",
                "margin_level_pct": f"{strategy.lower()}_margin_level_pct",
            }
        )
        sleeves.append(frame)
    combined = pd.concat(sleeves, axis=1).sort_index()
    for strategy in ("vb", "mr"):
        combined[f"{strategy}_balance"] = combined[f"{strategy}_balance"].ffill().fillna(
            STRATEGY_SIMULATION_INITIAL_BALANCE
        )
        combined[f"{strategy}_equity"] = combined[f"{strategy}_equity"].ffill().fillna(
            STRATEGY_SIMULATION_INITIAL_BALANCE
        )
        combined[f"{strategy}_open_position"] = (
            combined[f"{strategy}_open_position"].ffill().fillna(0).astype(int)
        )
        combined[f"{strategy}_used_margin"] = (
            combined[f"{strategy}_used_margin"].ffill().fillna(0.0)
        )
        combined[f"{strategy}_free_margin"] = (
            combined[f"{strategy}_free_margin"]
            .ffill()
            .fillna(STRATEGY_SIMULATION_INITIAL_BALANCE)
        )
    combined["vb_realized_pnl"] = (
        combined["vb_balance"] - STRATEGY_SIMULATION_INITIAL_BALANCE
    )
    combined["mr_realized_pnl"] = (
        combined["mr_balance"] - STRATEGY_SIMULATION_INITIAL_BALANCE
    )
    combined["vb_equity_pnl"] = (
        combined["vb_equity"] - STRATEGY_SIMULATION_INITIAL_BALANCE
    )
    combined["mr_equity_pnl"] = (
        combined["mr_equity"] - STRATEGY_SIMULATION_INITIAL_BALANCE
    )
    combined["balance"] = (
        ACCOUNT_INITIAL_BALANCE
        + combined["vb_realized_pnl"]
        + combined["mr_realized_pnl"]
    )
    combined["equity"] = (
        ACCOUNT_INITIAL_BALANCE
        + combined["vb_equity_pnl"]
        + combined["mr_equity_pnl"]
    )
    combined["open_positions"] = (
        combined["vb_open_position"] + combined["mr_open_position"]
    )
    combined["used_margin"] = combined["vb_used_margin"] + combined["mr_used_margin"]
    combined["free_margin"] = combined["equity"] - combined["used_margin"]
    combined["margin_level_pct"] = np.where(
        combined["used_margin"] > 0.0,
        combined["equity"] / combined["used_margin"] * 100.0,
        np.nan,
    )
    combined.reset_index(inplace=True)
    combined["time"] = combined["time"].map(lambda value: value.isoformat())
    records = combined.to_dict(orient="records")
    for record in records:
        if not math.isfinite(finite(record["margin_level_pct"], float("nan"))):
            record["margin_level_pct"] = None
    return records


def position_state_report(
    vb_report: dict[str, Any],
    mr_report: dict[str, Any],
    time_end_utc: str,
) -> dict[str, Any]:
    events: dict[pd.Timestamp, dict[str, list[dict[str, Any]]]] = {}

    def add_event(
        timestamp: Any, action: str, position: dict[str, Any]
    ) -> None:
        time = pd.Timestamp(timestamp)
        events.setdefault(time, {"opened": [], "closed": []})[action].append(position)

    for strategy, report in (("VB", vb_report), ("MR", mr_report)):
        leverage = finite(report["costs"]["leverage"], DEFAULT_LEVERAGE)
        for idx, trade in enumerate(report["trade_details"], start=1):
            position = {
                "position_id": f"{strategy}_{idx:04d}",
                "strategy": strategy,
                "side": trade["side"],
                "entry_time_utc": trade["entry_time"],
                "entry_price": finite(trade["entry_price"]),
                "required_margin_at_entry": finite(trade["entry_price"])
                * DEFAULT_SIDE_UNITS
                / leverage,
            }
            add_event(trade["entry_time"], "opened", position)
            add_event(trade["exit_time"], "closed", position)

        open_position = report.get("open_position_at_end")
        if open_position:
            position = {
                "position_id": f"{strategy}_OPEN_AT_END",
                "strategy": strategy,
                "side": open_position["side"],
                "entry_time_utc": open_position["entry_time"],
                "entry_price": finite(open_position["entry_price"]),
                "required_margin_at_entry": finite(
                    open_position["required_margin_at_entry"]
                ),
            }
            add_event(open_position["entry_time"], "opened", position)

    active: dict[str, dict[str, Any]] = {}
    timeline = []
    simultaneous_periods = []
    maximum_by_strategy = {"VB": 0, "MR": 0}
    position_limit_violations = 0
    times = sorted(events)
    for index, time in enumerate(times):
        event = events[time]
        closed_ids = {position["position_id"] for position in event["closed"]}
        for position in event["closed"]:
            active.pop(position["position_id"], None)
        for position in event["opened"]:
            if position["position_id"] not in closed_ids:
                active[position["position_id"]] = position
        current_positions = sorted(
            active.values(), key=lambda position: position["position_id"]
        )
        strategy_counts = {
            strategy: sum(
                position["strategy"] == strategy for position in current_positions
            )
            for strategy in ("VB", "MR")
        }
        for strategy, count in strategy_counts.items():
            maximum_by_strategy[strategy] = max(maximum_by_strategy[strategy], count)
        if len(current_positions) > 2 or any(
            count > 1 for count in strategy_counts.values()
        ):
            position_limit_violations += 1
        next_time = times[index + 1] if index + 1 < len(times) else pd.Timestamp(time_end_utc)
        timeline.append(
            {
                "time_utc": time.isoformat(),
                "opened": event["opened"],
                "closed": event["closed"],
                "current_position_count": len(current_positions),
                "current_position_count_by_strategy": strategy_counts,
                "current_positions": current_positions,
            }
        )
        if len(current_positions) == 2 and next_time > time:
            simultaneous_periods.append(
                {
                    "start_time_utc": time.isoformat(),
                    "end_time_utc": next_time.isoformat(),
                    "duration_hours": (next_time - time).total_seconds() / 3600.0,
                    "positions": current_positions,
                }
            )

    return {
        "rule": "maximum one open position per strategy; maximum two portfolio positions",
        "maximum_open_positions": max(
            (event["current_position_count"] for event in timeline), default=0
        ),
        "maximum_open_positions_by_strategy": maximum_by_strategy,
        "position_limit_violation_events": position_limit_violations,
        "position_events": timeline,
        "simultaneous_position_periods": simultaneous_periods,
        "simultaneous_position_period_count": len(simultaneous_periods),
        "simultaneous_position_hours": sum(
            period["duration_hours"] for period in simultaneous_periods
        ),
        "same_direction_simultaneous_hours": sum(
            period["duration_hours"]
            for period in simultaneous_periods
            if len({position["side"] for position in period["positions"]}) == 1
        ),
        "opposite_direction_simultaneous_hours": sum(
            period["duration_hours"]
            for period in simultaneous_periods
            if len({position["side"] for position in period["positions"]}) == 2
        ),
    }


def margin_summary(equity_series: list[dict[str, Any]]) -> dict[str, Any]:
    used = [finite(point["used_margin"]) for point in equity_series]
    free = [finite(point["free_margin"]) for point in equity_series]
    levels = [
        finite(point["margin_level_pct"], float("nan"))
        for point in equity_series
        if point["margin_level_pct"] is not None
    ]
    return {
        "leverage": DEFAULT_LEVERAGE,
        "formula": "price * lot_size * contract_size / leverage",
        "shared_portfolio_margin_monitoring": True,
        "account_model": "single_shared_account",
        "peak_used_margin": max(used, default=0.0),
        "minimum_free_margin": min(free, default=PORTFOLIO_INITIAL_BALANCE),
        "minimum_margin_level_pct": min(levels) if levels else None,
        "insufficient_shared_margin_observations": sum(value < 0.0 for value in free),
    }


def write_year_markdown(report: dict[str, Any]) -> None:
    position = report["position_management"]
    margin = report["costs"]["margin"]
    lines = [
        f"# Regime Baseline Report: {report['year']}",
        "",
        "No Regime selector is applied. VB and MR retain their original engine logic.",
        "",
        "## Portfolio Rules",
        "",
        "- VB maximum open positions: `1`",
        "- MR maximum open positions: `1`",
        "- Portfolio maximum open positions: `2`",
        f"- Leverage: `1:{margin['leverage']:.0f}`",
        "- Single shared account initial balance: `2000`",
        "",
        "## Result",
        "",
        f"- Final balance / equity: `{report['final_balance']:.2f}` / `{report['final_equity']:.2f}`",
        f"- Return: `{report['performance']['return_pct']:.2f}%`",
        f"- Profit factor: `{report['performance']['profit_factor']:.3f}`",
        f"- Maximum drawdown: `{report['performance']['max_drawdown_pct']:.2f}%`",
        f"- Trades: `{report['trades']}`",
        "",
        "## Margin",
        "",
        f"- Peak used margin: `{margin['peak_used_margin']:.2f}`",
        f"- Minimum free margin: `{margin['minimum_free_margin']:.2f}`",
        f"- Minimum margin level: `{margin['minimum_margin_level_pct']:.2f}%`",
        f"- Insufficient shared-margin observations: `{margin['insufficient_shared_margin_observations']}`",
        "",
        "## Position Validation",
        "",
        f"- Maximum simultaneous positions: `{position['maximum_open_positions']}`",
        f"- Maximum VB / MR positions: `{position['maximum_open_positions_by_strategy']['VB']}` / "
        f"`{position['maximum_open_positions_by_strategy']['MR']}`",
        f"- Position-limit violation events: `{position['position_limit_violation_events']}`",
        f"- Simultaneous-position periods: `{position['simultaneous_position_period_count']}`",
        f"- Total simultaneous-position hours: `{position['simultaneous_position_hours']:.2f}`",
        f"- Same / opposite direction simultaneous hours: "
        f"`{position['same_direction_simultaneous_hours']:.2f}` / "
        f"`{position['opposite_direction_simultaneous_hours']:.2f}`",
        "",
        "## Example Simultaneous Positions",
        "",
    ]
    for event in [
        event
        for event in position["position_events"]
        if event["current_position_count"] == 2
    ][:10]:
        current = " | ".join(
            f"{item['strategy']} {item['side']} @ {item['entry_price']:.2f} "
            f"(margin {item['required_margin_at_entry']:.2f})"
            for item in event["current_positions"]
        )
        lines.append(f"- `{event['time_utc']}`: {current}")
    lines.extend(["", "## Positions At End", ""])
    end_positions = [
        f"{strategy}: {details['side']} @ {details['entry_price']:.2f}"
        for strategy, details in report["open_positions_at_end"].items()
        if details
    ]
    lines.extend(f"- {value}" for value in end_positions or ["No open positions."])
    (REPORT_ROOT / f"report_{report['year']}.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def performance(
    trades: list[dict[str, Any]], equity_series: list[dict[str, Any]]
) -> dict[str, float]:
    pnls = np.array([finite(trade["net_pnl"]) for trade in trades], dtype=float)
    gross_profit = float(np.sum(pnls[pnls > 0.0]))
    gross_loss_abs = float(-np.sum(pnls[pnls < 0.0]))
    equity = np.array([finite(point["equity"]) for point in equity_series], dtype=float)
    running_peak = np.maximum.accumulate(equity)
    drawdowns = running_peak - equity
    drawdown_pct = np.divide(
        drawdowns,
        running_peak,
        out=np.zeros_like(drawdowns),
        where=running_peak > 0.0,
    )
    final_equity = finite(equity[-1]) if len(equity) else PORTFOLIO_INITIAL_BALANCE
    return {
        "net_pnl": final_equity - PORTFOLIO_INITIAL_BALANCE,
        "return_pct": (final_equity / PORTFOLIO_INITIAL_BALANCE - 1.0) * 100.0,
        "gross_profit": gross_profit,
        "gross_loss_abs": gross_loss_abs,
        "profit_factor": gross_profit / gross_loss_abs if gross_loss_abs > 0.0 else 0.0,
        "expectancy_per_trade": float(np.mean(pnls)) if len(pnls) else 0.0,
        "sharpe_per_trade": float(np.mean(pnls) / np.std(pnls, ddof=1))
        if len(pnls) > 1 and np.std(pnls, ddof=1) > 0.0
        else 0.0,
        "max_drawdown_abs": float(np.max(drawdowns)) if len(drawdowns) else 0.0,
        "max_drawdown_pct": float(np.max(drawdown_pct) * 100.0)
        if len(drawdown_pct)
        else 0.0,
    }


def child_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "account_role": "attribution_ledger_using_shared_account_initial_balance",
        "engine": report["engine"],
        "input_file": report["input_file"],
        "timeframe": Path(report["input_file"]).parent.name,
        "initial_balance": report["initial_balance"],
        "final_balance": report["final_balance"],
        "final_equity": report["final_equity"],
        "trades": report["trades"],
        "win_rate": report["win_rate"],
        "performance": report["performance"],
        "costs": report["costs"],
        "filters": report["filters"],
        "params": report["params"],
        "open_position_at_end": report.get("open_position_at_end"),
    }


def run_year(year: int) -> tuple[dict[str, Any], pd.DataFrame]:
    vb_engine = VolatilityBreakoutV1Engine(
        VBConfig(
            input_file=MARKET_ROOT / "H4" / f"H4_{year}.csv",
            initial_balance=STRATEGY_SIMULATION_INITIAL_BALANCE,
        )
    )
    mr_engine = MeanReversionV1Engine(
        MRConfig(
            input_file=MARKET_ROOT / "M15" / f"M15_{year}.csv",
            initial_balance=STRATEGY_SIMULATION_INITIAL_BALANCE,
        )
    )
    vb_engine.load_data()
    mr_engine.load_data()
    vb_report = vb_engine.run()
    mr_report = mr_engine.run()

    unified = vb_unified_rows(vb_report, year) + mr_unified_rows(mr_report, year)
    unified.sort(key=lambda row: (row["exit_time_utc"], row["trade_id"]))
    unified_df = pd.DataFrame(unified, columns=UNIFIED_COLUMNS)
    equity_series = combine_equity(vb_report, mr_report)
    position_state = position_state_report(
        vb_report, mr_report, equity_series[-1]["time"]
    )
    shared_margin = margin_summary(equity_series)
    if shared_margin["insufficient_shared_margin_observations"] > 0:
        raise RuntimeError(
            f"Shared {ACCOUNT_INITIAL_BALANCE:.0f} account has negative free margin "
            f"in {year}; result is not executable."
        )
    perf = performance(unified, equity_series)
    final_balance = finite(equity_series[-1]["balance"], ACCOUNT_INITIAL_BALANCE)
    final_equity = finite(equity_series[-1]["equity"], ACCOUNT_INITIAL_BALANCE)
    wins = sum(finite(trade["net_pnl"]) > 0.0 for trade in unified)
    report = {
        "engine": "regime_baseline_vb_mr_fixed",
        "description": "No-regime fixed combination: VB v1 H4 + MR v1 M15",
        "year": year,
        "allocation": {
            "mode": "single_shared_account",
            "account_initial_balance": ACCOUNT_INITIAL_BALANCE,
            "shared_margin": True,
            "leverage": DEFAULT_LEVERAGE,
            "maximum_positions_per_strategy": 1,
            "maximum_portfolio_positions": 2,
            "regime_filter": False,
            "conflict_resolution": False,
        },
        "time_start_utc": equity_series[0]["time"],
        "time_end_utc": equity_series[-1]["time"],
        "initial_balance": PORTFOLIO_INITIAL_BALANCE,
        "final_balance": final_balance,
        "final_equity": final_equity,
        "trades": len(unified),
        "win_rate": wins / len(unified) if unified else 0.0,
        "performance": perf,
        "costs": {
            "total_commission": finite(vb_report["costs"]["total_commission"])
            + finite(mr_report["costs"]["total_commission"]),
            "total_realized_swap": finite(vb_report["costs"]["total_realized_swap"])
            + finite(mr_report["costs"]["total_realized_swap"]),
            "margin": shared_margin,
        },
        "strategy_contributions": {
            "VB": child_summary(vb_report),
            "MR": child_summary(mr_report),
        },
        "open_positions_at_end": {
            "VB": vb_report.get("open_position_at_end"),
            "MR": mr_report.get("open_position_at_end"),
        },
        "position_management": position_state,
        "equity_series": equity_series,
        "sample_trades": unified[:30],
        "unified_trade_file": str(REPORT_ROOT / f"trades_{year}.csv"),
    }
    return report, unified_df


def pooled_stats(trades: pd.DataFrame) -> dict[str, Any]:
    pnls = pd.to_numeric(trades["net_pnl"], errors="coerce").fillna(0.0)
    gross_profit = float(pnls[pnls > 0.0].sum())
    gross_loss_abs = float(-pnls[pnls < 0.0].sum())
    return {
        "trades": int(len(trades)),
        "wins": int((pnls > 0.0).sum()),
        "losses": int((pnls < 0.0).sum()),
        "win_rate_pct": float((pnls > 0.0).mean() * 100.0),
        "net_pnl": float(pnls.sum()),
        "profit_factor": gross_profit / gross_loss_abs if gross_loss_abs > 0.0 else 0.0,
        "expectancy_per_trade": float(pnls.mean()),
    }


def write_summary(reports: list[dict[str, Any]], trades: pd.DataFrame) -> None:
    annual = []
    for report in reports:
        perf = report["performance"]
        annual.append(
            {
                "year": report["year"],
                "trades": report["trades"],
                "win_rate_pct": report["win_rate"] * 100.0,
                "final_balance": report["final_balance"],
                "final_equity": report["final_equity"],
                "net_pnl": perf["net_pnl"],
                "return_pct": perf["return_pct"],
                "profit_factor": perf["profit_factor"],
                "expectancy_per_trade": perf["expectancy_per_trade"],
                "max_drawdown_pct": perf["max_drawdown_pct"],
                "commission": report["costs"]["total_commission"],
                "vb_return_pct": report["strategy_contributions"]["VB"]["performance"][
                    "return_pct"
                ],
                "mr_return_pct": report["strategy_contributions"]["MR"]["performance"][
                    "return_pct"
                ],
                "vb_max_drawdown_pct": report["strategy_contributions"]["VB"][
                    "performance"
                ]["max_drawdown_pct"],
                "mr_max_drawdown_pct": report["strategy_contributions"]["MR"][
                    "performance"
                ]["max_drawdown_pct"],
            }
        )
    annual_df = pd.DataFrame(annual)
    returns = annual_df["return_pct"]
    grouped = {
        strategy: pooled_stats(group)
        for strategy, group in trades.groupby("strategy", sort=True)
    }
    summary = {
        "engine": "regime_baseline_vb_mr_fixed",
        "description": "No-regime fixed combination: VB v1 H4 + MR v1 M15",
        "allocation": reports[0]["allocation"],
        "coverage": {"year_start": YEARS[0], "year_end": YEARS[-1], "years": len(YEARS)},
        "overview": {
            "positive_years": int((returns > 0.0).sum()),
            "avg_annual_return_pct": float(returns.mean()),
            "median_annual_return_pct": float(returns.median()),
            "worst_annual_return_pct": float(returns.min()),
            "best_annual_return_pct": float(returns.max()),
            "simple_sum_return_pct": float(returns.sum()),
            "hypothetical_compounded_return_pct": float(
                ((1.0 + returns / 100.0).prod() - 1.0) * 100.0
            ),
            "avg_annual_profit_factor": float(annual_df["profit_factor"].mean()),
            "avg_annual_max_drawdown_pct": float(
                annual_df["max_drawdown_pct"].mean()
            ),
            "worst_annual_max_drawdown_pct": float(
                annual_df["max_drawdown_pct"].max()
            ),
            "pooled": pooled_stats(trades),
        },
        "strategy_contributions": grouped,
        "annual": annual,
        "notes": [
            "No regime filter, selector, conflict handling, or dynamic weight is applied.",
            "VB and MR trade one shared 2000 account; child engine balances are attribution ledgers only.",
            "Account equity equals 2000 plus the timestamp-aligned VB and MR equity PnL.",
            "The single account resets to 2000 at the start of each annual report.",
            "Return and drawdown use portfolio equity; pooled trade statistics use closed trades only.",
            "Historical results are research data, not pristine OOS.",
        ],
    }
    (REPORT_ROOT / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    annual_df.to_csv(REPORT_ROOT / "summary.csv", index=False)
    lines = [
        "# Regime Baseline: VB + MR Fixed Combination",
        "",
        "No Regime filter or strategy selector is applied.",
        "",
        "## Allocation",
        "",
        "- Single shared account initial balance: `2000`",
        "- Both strategies retain original defaults, costs, positions, and exits.",
        "- Account equity is `2000 + VB equity PnL + MR equity PnL`.",
        "- All current positions consume margin from the same account.",
        "",
        "## Executive Summary",
        "",
        f"- Positive years: `{summary['overview']['positive_years']}/{len(YEARS)}`",
        f"- Average / median annual return: `{summary['overview']['avg_annual_return_pct']:.2f}%` / "
        f"`{summary['overview']['median_annual_return_pct']:.2f}%`",
        f"- Worst / best annual return: `{summary['overview']['worst_annual_return_pct']:.2f}%` / "
        f"`{summary['overview']['best_annual_return_pct']:.2f}%`",
        f"- Average / worst annual max drawdown: "
        f"`{summary['overview']['avg_annual_max_drawdown_pct']:.2f}%` / "
        f"`{summary['overview']['worst_annual_max_drawdown_pct']:.2f}%`",
        f"- Pooled trades / PF / expectancy: "
        f"`{summary['overview']['pooled']['trades']}` / "
        f"`{summary['overview']['pooled']['profit_factor']:.3f}` / "
        f"`{summary['overview']['pooled']['expectancy_per_trade']:.3f}`",
        "",
        "## Annual Performance",
        "",
        "| Year | Return % | PF | Max DD % | Trades | VB Return % | MR Return % |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    lines.extend(
        f"| {row['year']} | {row['return_pct']:.2f} | {row['profit_factor']:.2f} | "
        f"{row['max_drawdown_pct']:.2f} | {row['trades']} | "
        f"{row['vb_return_pct']:.2f} | {row['mr_return_pct']:.2f} |"
        for row in annual
    )
    lines.extend(
        [
            "",
            "## Strategy Contributions",
            "",
            "| Strategy | Trades | Win % | Net PnL | PF | Expectancy |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    lines.extend(
        f"| {strategy} | {stats['trades']} | {stats['win_rate_pct']:.2f} | "
        f"{stats['net_pnl']:.2f} | {stats['profit_factor']:.2f} | "
        f"{stats['expectancy_per_trade']:.3f} |"
        for strategy, stats in grouped.items()
    )
    lines.extend(["", "## Reading Notes", ""])
    lines.extend(f"- {note}" for note in summary["notes"])
    (REPORT_ROOT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="No-Regime baseline: independently run and combine VB v1 + MR v1"
    )
    parser.add_argument("--year", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    years = [args.year] if args.year is not None else YEARS
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    reports = []
    all_trades = []
    for year in years:
        print(f"running regime baseline year={year}", flush=True)
        report, trades = run_year(year)
        (REPORT_ROOT / f"report_{year}.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        write_year_markdown(report)
        trades.to_csv(REPORT_ROOT / f"trades_{year}.csv", index=False)
        reports.append(report)
        all_trades.append(trades)
    if args.year is None:
        trades_all = pd.concat(all_trades, ignore_index=True)
        trades_all.sort_values(
            by=["exit_time_utc", "trade_id"], inplace=True, ignore_index=True
        )
        trades_all.to_csv(REPORT_ROOT / "trades_all.csv", index=False)
        write_summary(reports, trades_all)
    print(f"wrote reports to {REPORT_ROOT}", flush=True)


if __name__ == "__main__":
    main()
