from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xau.scripts.engines.volatility_breakout.v1 import (  # noqa: E402
    EngineConfig,
    VolatilityBreakoutV1Engine,
    resolve_input_files,
)

DATA_ROOT = REPO_ROOT / "xau" / "data" / "optimizatons" / "vb"


class VBExperimentEngine(VolatilityBreakoutV1Engine):
    experiment_name = "base"
    experiment_description = "Base VB v1 behavior."

    def signal_extra_filter(self, row: pd.Series, signal: str) -> tuple[bool, str | None]:
        return True, None

    def entry_extra_filter(
        self, signal_row: pd.Series, entry_row: pd.Series, signal: str
    ) -> tuple[bool, str | None]:
        return True, None

    def early_exit_raw_price(
        self, position: dict[str, Any], row: pd.Series, idx: int
    ) -> tuple[str, float] | None:
        return None

    def calc_signal(self, row: pd.Series) -> tuple[str | None, str | None]:
        signal, reason = super().calc_signal(row)
        if signal is None:
            return signal, reason
        ok, extra_reason = self.signal_extra_filter(row, signal)
        if not ok:
            return None, extra_reason or "experiment_signal_filter"
        return signal, None

    def run(self) -> dict[str, Any]:
        if self.df is None:
            raise RuntimeError("Data not loaded. Call load_data() first.")

        balance = float(self.config.initial_balance)
        trades: list[dict[str, Any]] = []
        equity_series: list[dict[str, Any]] = []
        position: dict[str, Any] | None = None

        total_swap = 0.0
        total_commission = 0.0

        session_reject_count = 0
        atr_ratio_filter_reject_count = 0
        spread_filter_reject_count = 0
        adx_filter_reject_count = 0
        both_breakout_reject_count = 0
        trail_move_count = 0
        experiment_reject_counts: dict[str, int] = {}
        early_exit_count = 0

        for i in range(len(self.df)):
            row = self.df.iloc[i]
            bar_time = row["time"]

            if position is not None and i >= int(position["entry_idx"]):
                side = str(position["side"])
                high_bid = float(row["high"])
                low_bid = float(row["low"])
                spread_px = self.points_to_price(float(row["spread"]))

                exit_reason = None
                raw_exit = None

                early_exit = self.early_exit_raw_price(position, row, i)
                if early_exit is not None:
                    exit_reason, raw_exit = early_exit
                    early_exit_count += 1

                if exit_reason is None:
                    if side == "long":
                        if low_bid <= float(position["sl"]):
                            exit_reason = "SL"
                            raw_exit = float(position["sl"])
                    else:
                        high_ask = high_bid + spread_px
                        if high_ask >= float(position["sl"]):
                            exit_reason = "SL"
                            raw_exit = float(position["sl"])

                if exit_reason is None and self.config.trail_mode == "donchian":
                    if side == "long":
                        dc_exit = float(row["donchian_exit_low_m"])
                        if low_bid <= dc_exit:
                            exit_reason = "DONCHIAN_EXIT"
                            raw_exit = dc_exit
                    else:
                        dc_exit = float(row["donchian_exit_high_m"])
                        high_ask = high_bid + spread_px
                        if high_ask >= dc_exit:
                            exit_reason = "DONCHIAN_EXIT"
                            raw_exit = dc_exit

                if exit_reason is not None and raw_exit is not None:
                    slip = self.ticks_to_price(self.config.slippage_ticks)
                    exit_price = raw_exit - slip if side == "long" else raw_exit + slip

                    gross_pnl = self.calc_pnl(float(position["entry_price"]), float(exit_price), side)
                    swap_total = self.accrued_swap(
                        entry_time=position["entry_time"], current_time=bar_time, side=side
                    )
                    exit_commission = self.commission_one_side()
                    balance += gross_pnl + swap_total - exit_commission
                    trade_net_pnl = (
                        gross_pnl
                        + swap_total
                        - float(position["entry_commission"])
                        - float(exit_commission)
                    )
                    total_swap += swap_total
                    total_commission += float(exit_commission)

                    trades.append(
                        {
                            "side": side,
                            "signal_time": position["signal_time"].isoformat(),
                            "entry_time": position["entry_time"].isoformat(),
                            "exit_time": bar_time.isoformat(),
                            "entry_price": float(position["entry_price"]),
                            "exit_price": float(exit_price),
                            "initial_sl": float(position["initial_sl"]),
                            "sl": float(position["sl"]),
                            "entry_atr": float(position["entry_atr"]),
                            "entry_atr_ratio": float(position["entry_atr_ratio"]),
                            "entry_h1_adx": float(position["entry_h1_adx"]),
                            "entry_spread_points": float(position["entry_spread_points"]),
                            "exit_reason": exit_reason,
                            "gross_pnl": float(gross_pnl),
                            "swap_total": float(swap_total),
                            "entry_commission": float(position["entry_commission"]),
                            "exit_commission": float(exit_commission),
                            "net_pnl": float(trade_net_pnl),
                            "pnl_result": self.pnl_result(float(trade_net_pnl)),
                            "equity_after": float(balance),
                            "holding_bars": int(i - int(position["entry_idx"]) + 1),
                            "initial_risk_price": float(position["initial_risk_price"]),
                            "initial_risk_money": float(position["initial_risk_money"]),
                            "r_multiple": float(
                                trade_net_pnl / float(position["initial_risk_money"])
                                if float(position["initial_risk_money"]) > 0.0
                                else 0.0
                            ),
                            "sl_update_count": int(position["sl_update_count"]),
                            "trail_updates": list(position["trail_updates"]),
                        }
                    )
                    position = None
                else:
                    if side == "long":
                        position["highest_since_entry"] = max(
                            float(position["highest_since_entry"]), high_bid
                        )
                    else:
                        position["lowest_since_entry"] = min(
                            float(position["lowest_since_entry"]), low_bid
                        )
                    if self.config.trail_mode == "chandelier":
                        atr_now = float(row["atr"])
                        old_sl = float(position["sl"])
                        if side == "long":
                            new_sl = (
                                float(position["highest_since_entry"])
                                - self.config.trail_atr_mult * atr_now
                            )
                            position["sl"] = float(max(old_sl, new_sl))
                        else:
                            new_sl = (
                                float(position["lowest_since_entry"])
                                + self.config.trail_atr_mult * atr_now
                            )
                            position["sl"] = float(min(old_sl, new_sl))
                        if float(position["sl"]) != old_sl:
                            trail_move_count += 1
                            position["sl_update_count"] = int(position["sl_update_count"]) + 1
                            position["trail_updates"].append(
                                {
                                    "time": bar_time.isoformat(),
                                    "old_sl": float(old_sl),
                                    "new_sl": float(position["sl"]),
                                    "atr": float(atr_now),
                                    "highest_since_entry": float(
                                        position["highest_since_entry"]
                                    ),
                                    "lowest_since_entry": float(
                                        position["lowest_since_entry"]
                                    ),
                                }
                            )

            if position is None and i + 1 < len(self.df):
                signal, reject_reason = self.calc_signal(row)
                if signal is None:
                    if reject_reason == "atr_ratio_filter":
                        atr_ratio_filter_reject_count += 1
                    elif reject_reason == "spread_filter":
                        spread_filter_reject_count += 1
                    elif reject_reason == "adx_filter":
                        adx_filter_reject_count += 1
                    elif reject_reason == "both_breakout_same_bar":
                        both_breakout_reject_count += 1
                    elif reject_reason:
                        experiment_reject_counts[reject_reason] = (
                            experiment_reject_counts.get(reject_reason, 0) + 1
                        )
                else:
                    entry_row = self.df.iloc[i + 1]
                    ok, reject_reason = self.entry_extra_filter(row, entry_row, signal)
                    if not ok:
                        reason = reject_reason or "experiment_entry_filter"
                        experiment_reject_counts[reason] = experiment_reject_counts.get(reason, 0) + 1
                    elif not self._is_in_session(entry_row["time"]):
                        session_reject_count += 1
                    elif float(entry_row["spread"]) > self.config.spread_max_points:
                        spread_filter_reject_count += 1
                    else:
                        entry_price = self.entry_fill_price(entry_row, signal)
                        atr = float(entry_row["atr"])
                        if signal == "long":
                            sl = entry_price - self.config.sl_atr_mult * atr
                        else:
                            sl = entry_price + self.config.sl_atr_mult * atr
                        initial_risk_price = abs(entry_price - sl)
                        initial_risk_money = initial_risk_price * self.side_units()

                        entry_commission = self.commission_one_side()
                        balance -= entry_commission
                        total_commission += float(entry_commission)

                        position = {
                            "side": signal,
                            "signal_time": row["time"],
                            "entry_idx": i + 1,
                            "entry_time": entry_row["time"],
                            "entry_price": float(entry_price),
                            "initial_sl": float(sl),
                            "sl": float(sl),
                            "entry_atr": float(atr),
                            "entry_atr_ratio": float(entry_row["atr_ratio"]),
                            "entry_h1_adx": float(entry_row["h1_adx"]),
                            "entry_spread_points": float(entry_row["spread"]),
                            "highest_since_entry": float(entry_row["high"]),
                            "lowest_since_entry": float(entry_row["low"]),
                            "entry_commission": float(entry_commission),
                            "initial_risk_price": float(initial_risk_price),
                            "initial_risk_money": float(initial_risk_money),
                            "sl_update_count": 0,
                            "trail_updates": [],
                        }

            floating = 0.0
            if position is not None and i >= int(position["entry_idx"]):
                mtm_exit = self.mark_to_market_exit_price(row, str(position["side"]))
                floating = self.calc_pnl(
                    float(position["entry_price"]), float(mtm_exit), str(position["side"])
                )
                floating += self.accrued_swap(
                    entry_time=position["entry_time"],
                    current_time=bar_time,
                    side=str(position["side"]),
                )

            equity_series.append(
                {
                    "time": bar_time.isoformat(),
                    "balance": float(balance),
                    "equity": float(balance + floating),
                    "open_position": int(position is not None),
                }
            )

        final_equity = float(equity_series[-1]["equity"]) if equity_series else float(balance)
        performance = self.compute_performance_metrics(
            trades=trades,
            initial_balance=float(self.config.initial_balance),
            final_balance=final_equity,
            equity_values=[float(p["equity"]) for p in equity_series],
        )
        wins = sum(1 for t in trades if t["net_pnl"] > 0)

        report = {
            "engine": "volatility_breakout_v1_experiment",
            "experiment": {
                "name": self.experiment_name,
                "description": self.experiment_description,
            },
            "input_file": str(self.config.input_file),
            "bars": int(len(self.df)),
            "time_start_utc": self.df.iloc[0]["time"].isoformat(),
            "time_end_utc": self.df.iloc[-1]["time"].isoformat(),
            "initial_balance": float(self.config.initial_balance),
            "final_balance": float(balance),
            "final_equity": final_equity,
            "trades": int(len(trades)),
            "win_rate": float((wins / len(trades)) if trades else 0.0),
            "performance": performance,
            "costs": {
                "point_value": float(self.config.point_value),
                "pip_value": float(self.config.pip_value),
                "slippage_ticks": float(self.config.slippage_ticks),
                "commission_per_trade": float(self.config.commission_per_trade),
                "swap_long_per_lot_per_night": float(self.config.swap_long_per_lot_per_night),
                "swap_short_per_lot_per_night": float(self.config.swap_short_per_lot_per_night),
                "total_realized_swap": float(total_swap),
                "total_commission": float(total_commission),
                "spread_mean_points": float(self.df["spread"].mean()),
                "spread_mean_price": float(self.df["spread"].mean() * self.config.point_value),
            },
            "filters": {
                "session_utc": f"{self.config.session_start_hour_utc:02d}:00-{self.config.session_end_hour_utc:02d}:00",
                "atr_ratio_min": float(self.config.atr_ratio_min),
                "spread_max_points": float(self.config.spread_max_points),
                "enable_h1_adx_filter": bool(self.config.enable_h1_adx_filter),
                "h1_adx_min": float(self.config.h1_adx_min),
                "session_reject_count": int(session_reject_count),
                "atr_ratio_filter_reject_count": int(atr_ratio_filter_reject_count),
                "spread_filter_reject_count": int(spread_filter_reject_count),
                "adx_filter_reject_count": int(adx_filter_reject_count),
                "both_breakout_reject_count": int(both_breakout_reject_count),
                "trail_move_count": int(trail_move_count),
                "early_exit_count": int(early_exit_count),
                "experiment_reject_counts": experiment_reject_counts,
            },
            "params": {
                "donchian_breakout_period": int(self.config.donchian_breakout_period),
                "donchian_exit_period": int(self.config.donchian_exit_period),
                "atr_period": int(self.config.atr_period),
                "atr_ratio_lookback": int(self.config.atr_ratio_lookback),
                "sl_atr_mult": float(self.config.sl_atr_mult),
                "trail_mode": str(self.config.trail_mode),
                "trail_atr_mult": float(self.config.trail_atr_mult),
                "entry_logic": "experiment-specific VB v1 signal, next bar market entry",
                "exit_logic": "SL + chandelier trailing plus optional experiment early exit",
                "position_mode": "single_position_no_pyramiding",
            },
            "equity_series": equity_series,
            "trade_details": trades,
            "sample_trades": trades[:30],
        }
        if position is not None:
            report["open_position_at_end"] = {
                "side": str(position["side"]),
                "entry_time": position["entry_time"].isoformat(),
                "entry_price": float(position["entry_price"]),
                "sl": float(position["sl"]),
            }
        return report


def default_config(input_file: Path) -> EngineConfig:
    return EngineConfig(input_file=input_file)


def year_from_report(report: dict[str, Any]) -> str:
    stem = Path(str(report["input_file"])).stem
    return stem.split("_")[-1]


def summarize_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for report in reports:
        perf = report["performance"]
        rows.append(
            {
                "year": year_from_report(report),
                "return_pct": float(perf["return_pct"]),
                "profit_factor": float(perf["profit_factor"]),
                "max_drawdown_pct": float(perf["max_drawdown_pct"]),
                "trades": int(report["trades"]),
                "win_rate": float(report["win_rate"]),
                "early_exit_count": int(report["filters"].get("early_exit_count", 0)),
            }
        )

    if not rows:
        return {"years": 0, "rows": []}

    return {
        "years": len(rows),
        "avg_return_pct": float(np.mean([r["return_pct"] for r in rows])),
        "avg_profit_factor": float(np.mean([r["profit_factor"] for r in rows])),
        "avg_max_drawdown_pct": float(np.mean([r["max_drawdown_pct"] for r in rows])),
        "positive_years": int(sum(1 for r in rows if r["return_pct"] > 0.0)),
        "avg_trades": float(np.mean([r["trades"] for r in rows])),
        "avg_win_rate": float(np.mean([r["win_rate"] for r in rows])),
        "total_early_exits": int(sum(r["early_exit_count"] for r in rows)),
        "worst_year": min(rows, key=lambda r: r["return_pct"]),
        "best_year": max(rows, key=lambda r: r["return_pct"]),
        "rows": rows,
    }


def write_summary(output_dir: Path, summary: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    rows = summary.get("rows", [])
    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(output_dir / "summary.csv", index=False)


UNIFIED_TRADE_COLUMNS = [
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


def _bucket_adx(value: float | None) -> str:
    if value is None or pd.isna(value):
        return ""
    if value < 20:
        return "adx_lt20"
    if value < 25:
        return "adx_20_25"
    if value < 30:
        return "adx_25_30"
    return "adx_ge30"


def _bucket_atr_ratio(value: float | None) -> str:
    if value is None or pd.isna(value):
        return ""
    if value < 1.1:
        return "atrr_lt1_1"
    if value < 1.25:
        return "atrr_1_1_1_25"
    if value < 1.5:
        return "atrr_1_25_1_5"
    return "atrr_ge1_5"


def _bucket_spread(value: float | None) -> str:
    if value is None or pd.isna(value):
        return ""
    if value <= 15:
        return "spread_le15"
    if value <= 30:
        return "spread_15_30"
    return "spread_gt30"


def _bucket_holding(holding_bars: int) -> str:
    if holding_bars < 8:
        return "hold_1_7"
    if holding_bars < 25:
        return "hold_8_24"
    return "hold_25_plus"


def report_to_unified_rows(
    report: dict[str, Any],
    *,
    output_name: str,
    strategy: str = "VB",
    engine_version: str = "volatility_breakout_v1",
    symbol: str = "XAUUSD",
    timeframe: str = "H4",
) -> list[dict[str, Any]]:
    rows = []
    year = year_from_report(report)
    initial_balance = float(report["initial_balance"])
    for idx, trade in enumerate(report["trade_details"], start=1):
        commission = float(trade.get("entry_commission", 0.0)) + float(
            trade.get("exit_commission", 0.0)
        )
        net_pnl = float(trade["net_pnl"])
        entry_time = pd.Timestamp(trade["entry_time"])
        exit_time = pd.Timestamp(trade["exit_time"])
        holding_bars = int(trade["holding_bars"])
        entry_h1_adx = float(trade.get("entry_h1_adx", np.nan))
        entry_atr_ratio = float(trade.get("entry_atr_ratio", np.nan))
        entry_spread = float(trade.get("entry_spread_points", np.nan))
        row = {
            "trade_id": f"{strategy}_{engine_version}_{output_name}_{year}_{idx:04d}",
            "strategy": strategy,
            "engine_version": engine_version,
            "symbol": symbol,
            "timeframe": timeframe,
            "side": trade["side"],
            "signal_time_utc": trade["signal_time"],
            "entry_time_utc": trade["entry_time"],
            "exit_time_utc": trade["exit_time"],
            "entry_price": float(trade["entry_price"]),
            "exit_price": float(trade["exit_price"]),
            "initial_sl": float(trade.get("initial_sl", trade.get("sl", np.nan))),
            "final_sl": float(trade.get("sl", np.nan)),
            "exit_reason": trade["exit_reason"],
            "gross_pnl": float(trade["gross_pnl"]),
            "commission": commission,
            "swap": float(trade.get("swap_total", 0.0)),
            "net_pnl": net_pnl,
            "pnl_result": trade.get("pnl_result", VBExperimentEngine.pnl_result(net_pnl)),
            "initial_risk_price": float(trade.get("initial_risk_price", np.nan)),
            "initial_risk_money": float(trade.get("initial_risk_money", np.nan)),
            "r_multiple": float(trade.get("r_multiple", np.nan)),
            "holding_bars": holding_bars,
            "holding_hours": float((exit_time - entry_time).total_seconds() / 3600.0),
            "entry_atr": float(trade.get("entry_atr", np.nan)),
            "entry_atr_ratio": entry_atr_ratio,
            "entry_spread_points": entry_spread,
            "entry_adx": "",
            "entry_h1_adx": entry_h1_adx,
            "entry_h1_adx_slope": "",
            "entry_ema_fast": "",
            "entry_ema_slow": "",
            "entry_ema_slope": "",
            "entry_donchian_high": "",
            "entry_donchian_low": "",
            "entry_donchian_width_atr": "",
            "entry_bb_width_atr": "",
            "entry_close_to_ema_atr": "",
            "entry_range_efficiency": "",
            "regime_trend_strength": "",
            "regime_volatility": "",
            "regime_direction": "",
            "regime_strategy_fit": "",
            "adx_bucket": _bucket_adx(entry_h1_adx),
            "atr_ratio_bucket": _bucket_atr_ratio(entry_atr_ratio),
            "spread_bucket": _bucket_spread(entry_spread),
            "session_utc": f"{entry_time.hour:02d}:00",
            "weekday": int(entry_time.weekday()),
            "is_win": bool(net_pnl > 0.0),
            "return_pct_on_initial_balance": float(
                (net_pnl / initial_balance) * 100.0 if initial_balance else 0.0
            ),
            "max_favorable_excursion_r": "",
            "max_adverse_excursion_r": "",
            "post_entry_holding_bucket": _bucket_holding(holding_bars),
            "sl_update_count": int(trade.get("sl_update_count", 0)),
            "trail_updates_json": json.dumps(
                trade.get("trail_updates", []),
                separators=(",", ":"),
            ),
        }
        rows.append(row)
    return rows


def write_unified_trades(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    for col in UNIFIED_TRADE_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[UNIFIED_TRADE_COLUMNS]
    df.to_csv(output_dir / "unified_trades.csv", index=False)


def run_experiment(engine_cls: type[VBExperimentEngine], output_name: str) -> dict[str, Any]:
    output_dir = DATA_ROOT / output_name

    reports = []
    unified_rows = []
    input_files = resolve_input_files(None, ["H4"])
    for input_file in input_files:
        engine = engine_cls(default_config(input_file))
        engine.load_data()
        report = engine.run()
        year = year_from_report(report)
        reports.append(report)
        unified_rows.extend(report_to_unified_rows(report, output_name=output_name))
        print(f"{engine_cls.experiment_name}: {year} done")

    summary = summarize_reports(reports)
    summary["experiment"] = {
        "name": engine_cls.experiment_name,
        "description": engine_cls.experiment_description,
        "output_dir": str(output_dir),
    }
    write_unified_trades(output_dir, unified_rows)
    write_summary(output_dir, summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
    return summary
