from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
XAU_DATA_DIR = PROJECT_ROOT / "data" / "historical"
RESULT_DIR = PROJECT_ROOT / "data" / "reports" / "trend_pullback" / "v1"

REQUIRED_COLUMNS = [
    "time",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "spread",
]


@dataclass
class EngineConfig:
    input_file: Path
    initial_balance: float = 1000.0
    lot_size: float = 0.01
    contract_size: int = 100
    leverage: float = 100.0
    ema_fast_period: int = 50
    ema_slow_period: int = 200
    atr_period: int = 14
    pullback_depth_atr_mult: float = 0.3
    atr_sl_mult: float = 2.0
    tp_rr: float = 3.0
    point_value: float = 0.01
    pip_value: float = 0.01
    slippage_ticks: float = 1.0
    commission_per_lot_per_side: float = 3.5
    swap_long_per_lot_per_night: float = 0.0
    swap_short_per_lot_per_night: float = 0.0


class TrendPullbackVolFilterV1Engine:
    def __init__(self, config: EngineConfig) -> None:
        self.config = config
        self.df: pd.DataFrame | None = None

    def points_to_price(self, points: float) -> float:
        return points * self.config.point_value

    def pips_to_price(self, pips: float) -> float:
        return pips * self.config.pip_value

    def ticks_to_price(self, ticks: float) -> float:
        return ticks * self.config.point_value

    def side_units(self) -> float:
        return self.config.lot_size * self.config.contract_size

    def commission_one_side(self) -> float:
        return self.config.lot_size * self.config.commission_per_lot_per_side

    def timeframe_label(self) -> str:
        parent_name = self.config.input_file.parent.name.upper()
        if re.fullmatch(r"[MHDW]\d+", parent_name):
            return parent_name
        stem = self.config.input_file.stem.upper()
        for token in stem.split("_"):
            if re.fullmatch(r"[MHDW]\d+", token):
                return token
        return "UNKNOWN_TF"

    def calc_pnl(self, entry_price: float, exit_price: float, side: str) -> float:
        units = self.side_units()
        if side == "long":
            return (exit_price - entry_price) * units
        return (entry_price - exit_price) * units

    def entry_fill_price(self, row: pd.Series, side: str) -> float:
        bid = float(row["open"])
        ask = bid + self.points_to_price(float(row["spread"]))
        slip = self.ticks_to_price(self.config.slippage_ticks)
        if side == "long":
            return ask + slip
        return bid - slip

    def exit_fill_price(self, row: pd.Series, side: str) -> float:
        bid = float(row["close"])
        ask = bid + self.points_to_price(float(row["spread"]))
        slip = self.ticks_to_price(self.config.slippage_ticks)
        if side == "long":
            return bid - slip
        return ask + slip

    def mark_to_market_exit_price(self, row: pd.Series, side: str) -> float:
        bid = float(row["close"])
        ask = bid + self.points_to_price(float(row["spread"]))
        if side == "long":
            return bid
        return ask

    def load_data(self) -> pd.DataFrame:
        df = pd.read_csv(self.config.input_file)
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"Input CSV missing columns: {missing}. Required: {REQUIRED_COLUMNS}"
            )

        for col in ["open", "high", "low", "close", "tick_volume", "spread"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["time"] = pd.to_datetime(df["time"], utc=True)
        df.sort_values("time", inplace=True)
        df.drop_duplicates(subset=["time"], inplace=True)
        df.dropna(
            subset=["time", "open", "high", "low", "close", "spread"], inplace=True
        )
        df.reset_index(drop=True, inplace=True)
        if df.empty:
            raise ValueError("Input CSV has no rows after cleaning.")

        self.df = self.compute_indicators(df)
        return self.df

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["ema_fast"] = out["close"].ewm(
            span=self.config.ema_fast_period, adjust=False
        ).mean()
        out["ema_slow"] = out["close"].ewm(
            span=self.config.ema_slow_period, adjust=False
        ).mean()
        out["ema_slow_slope"] = out["ema_slow"].diff()

        high_low = out["high"] - out["low"]
        high_prev_close = (out["high"] - out["close"].shift(1)).abs()
        low_prev_close = (out["low"] - out["close"].shift(1)).abs()
        out["tr"] = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(
            axis=1
        )
        out["atr"] = (
            out["tr"].ewm(alpha=1 / self.config.atr_period, adjust=False).mean()
        )

        out.dropna(inplace=True)
        out.reset_index(drop=True, inplace=True)
        return out

    def calc_signal(self, row: pd.Series) -> str | None:
        ema_fast = float(row["ema_fast"])
        ema_slow = float(row["ema_slow"])
        ema_slow_slope = float(row["ema_slow_slope"])
        atr = float(row["atr"])
        low = float(row["low"])
        high = float(row["high"])
        close = float(row["close"])

        long_trend = ema_fast > ema_slow and ema_slow_slope > 0.0 and close > ema_slow
        short_trend = ema_fast < ema_slow and ema_slow_slope < 0.0 and close < ema_slow

        long_pullback = low <= ema_fast and close > ema_fast
        short_pullback = high >= ema_fast and close < ema_fast

        long_depth_ok = (ema_fast - low) >= (self.config.pullback_depth_atr_mult * atr)
        short_depth_ok = (high - ema_fast) >= (
            self.config.pullback_depth_atr_mult * atr
        )

        if long_trend and long_pullback and long_depth_ok:
            return "long"
        if short_trend and short_pullback and short_depth_ok:
            return "short"
        return None

    def accrued_swap(
        self, entry_time: pd.Timestamp, current_time: pd.Timestamp, side: str
    ) -> float:
        nights = max((current_time.date() - entry_time.date()).days, 0)
        if nights == 0:
            return 0.0
        per_lot = (
            self.config.swap_long_per_lot_per_night
            if side == "long"
            else self.config.swap_short_per_lot_per_night
        )
        return float(self.config.lot_size * per_lot * nights)

    @staticmethod
    def compute_performance_metrics(
        trades: list[dict[str, Any]],
        initial_balance: float,
        final_balance: float,
        equity_values: list[float] | None = None,
    ) -> dict[str, float]:
        net_pnl = final_balance - initial_balance
        trade_pnls = [float(t["net_pnl"]) for t in trades]
        gross_profit = sum(p for p in trade_pnls if p > 0)
        gross_loss_abs = -sum(p for p in trade_pnls if p < 0)
        if gross_loss_abs > 0:
            profit_factor = gross_profit / gross_loss_abs
        elif gross_profit > 0:
            profit_factor = float("inf")
        else:
            profit_factor = 0.0

        expectancy = float(np.mean(trade_pnls)) if trade_pnls else 0.0
        if len(trade_pnls) >= 2:
            pnl_std = float(np.std(trade_pnls, ddof=1))
            sharpe_per_trade = expectancy / pnl_std if pnl_std > 0 else 0.0
            sqn = (np.sqrt(len(trade_pnls)) * expectancy / pnl_std) if pnl_std > 0 else 0.0
        else:
            sharpe_per_trade = 0.0
            sqn = 0.0

        dd_curve = (
            equity_values
            if equity_values
            else [initial_balance] + [float(t["equity_after"]) for t in trades]
        )
        peak = float(dd_curve[0]) if dd_curve else float(initial_balance)
        max_drawdown_abs = 0.0
        max_drawdown_pct = 0.0
        for eq in dd_curve:
            if eq > peak:
                peak = eq
            dd_abs = peak - eq
            dd_pct = (dd_abs / peak) if peak > 0 else 0.0
            if dd_abs > max_drawdown_abs:
                max_drawdown_abs = dd_abs
            if dd_pct > max_drawdown_pct:
                max_drawdown_pct = dd_pct

        wins = [p for p in trade_pnls if p > 0]
        losses = [p for p in trade_pnls if p < 0]
        avg_win = float(np.mean(wins)) if wins else 0.0
        avg_loss_abs = float(abs(np.mean(losses))) if losses else 0.0
        payoff_ratio = (avg_win / avg_loss_abs) if avg_loss_abs > 0 else 0.0
        recovery_factor = (net_pnl / max_drawdown_abs) if max_drawdown_abs > 0 else 0.0

        return {
            "trades": int(len(trade_pnls)),
            "wins": int(len(wins)),
            "losses": int(len(losses)),
            "breakeven": int(len(trade_pnls) - len(wins) - len(losses)),
            "win_rate": float((len(wins) / len(trade_pnls)) if trade_pnls else 0.0),
            "net_pnl": float(net_pnl),
            "return_pct": (
                float((net_pnl / initial_balance) * 100.0) if initial_balance else 0.0
            ),
            "gross_profit": float(gross_profit),
            "gross_loss_abs": float(gross_loss_abs),
            "profit_factor": float(profit_factor),
            "avg_win": float(avg_win),
            "avg_loss_abs": float(avg_loss_abs),
            "payoff_ratio": float(payoff_ratio),
            "largest_win": float(max(wins) if wins else 0.0),
            "largest_loss": float(min(losses) if losses else 0.0),
            "expectancy_per_trade": float(expectancy),
            "sharpe_per_trade": float(sharpe_per_trade),
            "sqn": float(sqn),
            "max_drawdown_abs": float(max_drawdown_abs),
            "max_drawdown_pct": float(max_drawdown_pct * 100.0),
            "recovery_factor": float(recovery_factor),
        }

    def run(self) -> dict[str, Any]:
        if self.df is None:
            raise RuntimeError("Data not loaded. Call load_data() first.")

        balance = float(self.config.initial_balance)
        trades: list[dict[str, Any]] = []
        equity_series: list[dict[str, Any]] = []
        position: dict[str, Any] | None = None
        total_swap = 0.0
        total_commission = 0.0

        for i in range(len(self.df)):
            row = self.df.iloc[i]
            bar_time = row["time"]

            # One position at a time (no pyramiding / no opposite overlap).
            if position is not None and i >= int(position["entry_idx"]):
                side = str(position["side"])
                high_bid = float(row["high"])
                low_bid = float(row["low"])
                spread_px = self.points_to_price(float(row["spread"]))

                if side == "long":
                    hit_sl = low_bid <= float(position["sl"])
                    hit_tp = high_bid >= float(position["tp"])
                else:
                    high_ask = high_bid + spread_px
                    low_ask = low_bid + spread_px
                    hit_sl = high_ask >= float(position["sl"])
                    hit_tp = low_ask <= float(position["tp"])

                exit_reason = None
                raw_exit = None
                if hit_sl:
                    exit_reason = "SL"
                    raw_exit = float(position["sl"])
                elif hit_tp:
                    exit_reason = "TP"
                    raw_exit = float(position["tp"])

                if exit_reason is not None and raw_exit is not None:
                    slip = self.ticks_to_price(self.config.slippage_ticks)
                    if exit_reason in {"SL", "TP"}:
                        exit_price = raw_exit - slip if side == "long" else raw_exit + slip
                    else:
                        exit_price = raw_exit

                    gross_pnl = self.calc_pnl(
                        float(position["entry_price"]), float(exit_price), side
                    )
                    swap_total = self.accrued_swap(
                        entry_time=position["entry_time"],
                        current_time=bar_time,
                        side=side,
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
                            "sl": float(position["sl"]),
                            "tp": float(position["tp"]),
                            "exit_reason": exit_reason,
                            "gross_pnl": float(gross_pnl),
                            "swap_total": float(swap_total),
                            "entry_commission": float(position["entry_commission"]),
                            "exit_commission": float(exit_commission),
                            "net_pnl": float(trade_net_pnl),
                            "equity_after": float(balance),
                            "holding_bars": int(i - int(position["entry_idx"]) + 1),
                        }
                    )
                    position = None

            if position is None and i + 1 < len(self.df):
                signal = self.calc_signal(row)
                if signal is not None:
                    entry_row = self.df.iloc[i + 1]
                    entry_price = self.entry_fill_price(entry_row, signal)
                    atr = float(entry_row["atr"])
                    sl_distance = self.config.atr_sl_mult * atr
                    tp_distance = self.config.tp_rr * sl_distance

                    if signal == "long":
                        sl = entry_price - sl_distance
                        tp = entry_price + tp_distance
                    else:
                        sl = entry_price + sl_distance
                        tp = entry_price - tp_distance

                    entry_commission = self.commission_one_side()
                    balance -= entry_commission
                    total_commission += float(entry_commission)
                    position = {
                        "side": signal,
                        "signal_time": row["time"],
                        "entry_idx": i + 1,
                        "entry_time": entry_row["time"],
                        "entry_price": float(entry_price),
                        "sl": float(sl),
                        "tp": float(tp),
                        "entry_commission": float(entry_commission),
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
            equity_values=[float(point["equity"]) for point in equity_series],
        )
        wins = sum(1 for t in trades if t["net_pnl"] > 0)
        start_ts = self.df.iloc[0]["time"]
        end_ts = self.df.iloc[-1]["time"]
        duration_days = max((end_ts - start_ts).total_seconds() / 86400.0, 0.0)
        duration_years = duration_days / 365.25 if duration_days > 0 else 0.0
        annualized_return_pct = 0.0
        if (
            duration_years > 0
            and self.config.initial_balance > 0
            and final_equity > 0
        ):
            annualized_return_pct = (
                (final_equity / self.config.initial_balance) ** (1.0 / duration_years)
                - 1.0
            ) * 100.0

        max_dd_pct = float(performance["max_drawdown_pct"])
        performance["annualized_return_pct"] = float(annualized_return_pct)
        performance["calmar_ratio"] = (
            float(annualized_return_pct / max_dd_pct) if max_dd_pct > 0 else 0.0
        )
        holding_bars = [int(t["holding_bars"]) for t in trades]
        performance["avg_holding_bars"] = (
            float(np.mean(holding_bars)) if holding_bars else 0.0
        )
        performance["median_holding_bars"] = (
            float(np.median(holding_bars)) if holding_bars else 0.0
        )
        report = {
            "engine": "trend_pullback_v1",
            "input_file": str(self.config.input_file),
            "bars": int(len(self.df)),
            "time_start_utc": start_ts.isoformat(),
            "time_end_utc": end_ts.isoformat(),
            "period_days": float(duration_days),
            "initial_balance": float(self.config.initial_balance),
            "final_balance": float(balance),
            "final_equity": final_equity,
            "trades": int(len(trades)),
            "win_rate": float((wins / len(trades)) if trades else 0.0),
            "performance": performance,
            "lot_size": float(self.config.lot_size),
            "contract_size": int(self.config.contract_size),
            "leverage": float(self.config.leverage),
            "costs": {
                "point_value": float(self.config.point_value),
                "pip_value": float(self.config.pip_value),
                "slippage_ticks": float(self.config.slippage_ticks),
                "commission_per_lot_per_side": float(
                    self.config.commission_per_lot_per_side
                ),
                "swap_long_per_lot_per_night": float(
                    self.config.swap_long_per_lot_per_night
                ),
                "swap_short_per_lot_per_night": float(
                    self.config.swap_short_per_lot_per_night
                ),
                "total_realized_swap": float(total_swap),
                "total_commission": float(total_commission),
                "spread_mean_points": float(self.df["spread"].mean()),
                "spread_mean_price": float(
                    self.df["spread"].mean() * self.config.point_value
                ),
            },
            "params": {
                "ema_fast_period": int(self.config.ema_fast_period),
                "ema_slow_period": int(self.config.ema_slow_period),
                "trend_filter": "EMA50>EMA200 and EMA200 slope>0 and close>EMA200",
                "short_trend_filter": "EMA50<EMA200 and EMA200 slope<0 and close<EMA200",
                "pullback_depth_atr_mult": float(self.config.pullback_depth_atr_mult),
                "atr_period": int(self.config.atr_period),
                "atr_sl_mult": float(self.config.atr_sl_mult),
                "tp_rr": float(self.config.tp_rr),
                "position_mode": "single_position_no_pyramiding",
                "force_close_policy": "none",
            },
            "equity_series": equity_series,
            "sample_trades": trades[:30],
        }
        if position is not None:
            report["open_position_at_end"] = {
                "side": str(position["side"]),
                "entry_time": position["entry_time"].isoformat(),
                "entry_price": float(position["entry_price"]),
                "sl": float(position["sl"]),
                "tp": float(position["tp"]),
            }
        return report

    def _default_report_filename(self, report: dict[str, Any]) -> str:
        year_match = re.search(r"(19|20)\d{2}", self.config.input_file.stem)
        if year_match:
            return f"report_{year_match.group(0)}.json"
        start_utc = str(report.get("time_start_utc", ""))
        if len(start_utc) >= 4 and start_utc[:4].isdigit():
            return f"report_{start_utc[:4]}.json"
        return "report_UNKNOWN_YEAR.json"

    def save_report(
        self, report: dict[str, Any], output_path: Path | None = None
    ) -> Path:
        if output_path is None:
            tf_dir = RESULT_DIR / self.timeframe_label()
            tf_dir.mkdir(parents=True, exist_ok=True)
            output_path = tf_dir / self._default_report_filename(report)
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return output_path


def resolve_input_files(cli_input: str | None) -> list[Path]:
    if cli_input:
        path = Path(cli_input).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        return [path]

    candidates = sorted(XAU_DATA_DIR.rglob("*.csv"))
    if not candidates:
        raise FileNotFoundError(
            f"No XAU CSV found under {XAU_DATA_DIR}. "
            "Please place your XAU data there first."
        )
    return candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "XAU Trend Pullback Vol Filter V1: EMA200 trend filter + EMA50 pullback "
            "with ATR depth filter, SL=2*ATR, TP=3R."
        )
    )
    parser.add_argument("--input", default=None)
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Optional output JSON path. Defaults to "
            "data/reports/trend_pullback/v1/<TF>/report_YEAR.json."
        ),
    )
    parser.add_argument("--initial-balance", type=float, default=1000.0)
    parser.add_argument("--lot-size", type=float, default=0.01)
    parser.add_argument("--contract-size", type=int, default=100)
    parser.add_argument("--leverage", type=float, default=100.0)
    parser.add_argument("--ema-fast-period", type=int, default=50)
    parser.add_argument("--ema-slow-period", type=int, default=200)
    parser.add_argument("--atr-period", type=int, default=14)
    parser.add_argument("--pullback-depth-atr-mult", type=float, default=0.3)
    parser.add_argument("--atr-sl-mult", type=float, default=2.0)
    parser.add_argument("--tp-rr", type=float, default=3.0)
    parser.add_argument("--point-value", type=float, default=0.01)
    parser.add_argument("--pip-value", type=float, default=0.01)
    parser.add_argument("--slippage-ticks", type=float, default=1.0)
    parser.add_argument("--commission-per-lot-per-side", type=float, default=3.5)
    parser.add_argument("--swap-long-per-lot-per-night", type=float, default=0.0)
    parser.add_argument("--swap-short-per-lot-per-night", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_files = resolve_input_files(args.input)
    report_paths: list[Path] = []
    reports: list[dict[str, Any]] = []
    explicit_output = None
    if args.output:
        explicit_output = Path(args.output).expanduser()
        if not explicit_output.is_absolute():
            explicit_output = (Path.cwd() / explicit_output).resolve()
        if len(input_files) > 1:
            raise ValueError("--output is only allowed when using a single input file.")

    for idx, input_file in enumerate(input_files, start=1):
        config = EngineConfig(
            input_file=input_file,
            initial_balance=args.initial_balance,
            lot_size=args.lot_size,
            contract_size=args.contract_size,
            leverage=args.leverage,
            ema_fast_period=args.ema_fast_period,
            ema_slow_period=args.ema_slow_period,
            atr_period=args.atr_period,
            pullback_depth_atr_mult=args.pullback_depth_atr_mult,
            atr_sl_mult=args.atr_sl_mult,
            tp_rr=args.tp_rr,
            point_value=args.point_value,
            pip_value=args.pip_value,
            slippage_ticks=args.slippage_ticks,
            commission_per_lot_per_side=args.commission_per_lot_per_side,
            swap_long_per_lot_per_night=args.swap_long_per_lot_per_night,
            swap_short_per_lot_per_night=args.swap_short_per_lot_per_night,
        )

        engine = TrendPullbackVolFilterV1Engine(config)
        engine.load_data()
        report = engine.run()
        report_path = engine.save_report(report, output_path=explicit_output)
        report_paths.append(report_path)
        reports.append(report)
        print(
            f"[{idx}/{len(input_files)}] finished {input_file.name} -> {report_path}"
        )

    print("Trend Pullback Vol Filter V1 backtest finished.")
    if len(reports) == 1:
        print(json.dumps(reports[0], indent=2))
    print("Saved reports:")
    for path in report_paths:
        print(path)


if __name__ == "__main__":
    main()
