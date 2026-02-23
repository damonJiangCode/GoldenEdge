from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EUR_DATA_DIR = PROJECT_ROOT / "data" / "historical"
RESULT_DIR = PROJECT_ROOT / "data" / "engines" / "ema_pullback_trend_v1"

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
    lot_size: float = 0.005
    contract_size: int = 100000
    leverage: float = 100.0
    ema_fast_period: int = 50
    ema_slow_period: int = 200
    atr_period: int = 14
    pullback_depth_atr_mult: float = 0.3
    atr_sl_mult: float = 1.5
    tp_rr: float = 2.0
    slippage_pips: float = 0.2
    commission_per_lot_per_side: float = 3.5


class EMAPullbackTrendV1Engine:
    def __init__(self, config: EngineConfig) -> None:
        self.config = config
        self.df: pd.DataFrame | None = None

    @staticmethod
    def points_to_price(points: float) -> float:
        return points * 0.00001

    @staticmethod
    def pips_to_price(pips: float) -> float:
        return pips * 0.0001

    def side_units(self) -> float:
        return self.config.lot_size * self.config.contract_size

    def commission_one_side(self) -> float:
        return self.config.lot_size * self.config.commission_per_lot_per_side

    def calc_pnl(self, entry_price: float, exit_price: float, side: str) -> float:
        units = self.side_units()
        if side == "long":
            return (exit_price - entry_price) * units
        return (entry_price - exit_price) * units

    def entry_fill_price(self, row: pd.Series, side: str) -> float:
        bid = float(row["open"])
        ask = bid + self.points_to_price(float(row["spread"]))
        slip = self.pips_to_price(self.config.slippage_pips)
        if side == "long":
            return ask + slip
        return bid - slip

    def exit_fill_price(self, row: pd.Series, side: str) -> float:
        bid = float(row["close"])
        ask = bid + self.points_to_price(float(row["spread"]))
        slip = self.pips_to_price(self.config.slippage_pips)
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
        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
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

        long_depth_ok = (ema_fast - low) >= (self.config.pullback_depth_atr_mult * atr)
        short_depth_ok = (high - ema_fast) >= (
            self.config.pullback_depth_atr_mult * atr
        )
        long_signal = (
            ema_fast > ema_slow
            and ema_slow_slope > 0.0
            and close > ema_fast
            and long_depth_ok
        )
        short_signal = (
            ema_fast < ema_slow
            and ema_slow_slope < 0.0
            and close < ema_fast
            and short_depth_ok
        )

        if long_signal:
            return "long"
        if short_signal:
            return "short"
        return None

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
        else:
            sharpe_per_trade = 0.0

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

        return {
            "net_pnl": float(net_pnl),
            "return_pct": (
                float((net_pnl / initial_balance) * 100.0) if initial_balance else 0.0
            ),
            "gross_profit": float(gross_profit),
            "gross_loss_abs": float(gross_loss_abs),
            "profit_factor": float(profit_factor),
            "expectancy_per_trade": float(expectancy),
            "sharpe_per_trade": float(sharpe_per_trade),
            "max_drawdown_abs": float(max_drawdown_abs),
            "max_drawdown_pct": float(max_drawdown_pct * 100.0),
        }

    def run(self) -> dict[str, Any]:
        if self.df is None:
            raise RuntimeError("Data not loaded. Call load_data() first.")

        balance = float(self.config.initial_balance)
        trades: list[dict[str, Any]] = []
        equity_series: list[dict[str, Any]] = []
        position: dict[str, Any] | None = None

        for i in range(len(self.df)):
            row = self.df.iloc[i]
            bar_time = row["time"]
            next_bar_time = self.df.iloc[i + 1]["time"] if i + 1 < len(self.df) else None
            is_last_bar = i == len(self.df) - 1
            is_friday_last_bar = bar_time.weekday() == 4 and (
                next_bar_time is None or next_bar_time.weekday() != 4
            )

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
                elif is_friday_last_bar:
                    exit_reason = "FRIDAY_FORCE_CLOSE"
                    raw_exit = self.exit_fill_price(row, side)
                elif is_last_bar:
                    exit_reason = "EOD"
                    raw_exit = self.exit_fill_price(row, side)

                if exit_reason is not None and raw_exit is not None:
                    slip = self.pips_to_price(self.config.slippage_pips)
                    if exit_reason in {"SL", "TP"}:
                        exit_price = raw_exit - slip if side == "long" else raw_exit + slip
                    else:
                        exit_price = raw_exit

                    gross_pnl = self.calc_pnl(
                        float(position["entry_price"]), float(exit_price), side
                    )
                    exit_commission = self.commission_one_side()
                    balance += gross_pnl - exit_commission
                    trade_net_pnl = (
                        gross_pnl
                        - float(position["entry_commission"])
                        - float(exit_commission)
                    )

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
                            "entry_commission": float(position["entry_commission"]),
                            "exit_commission": float(exit_commission),
                            "net_pnl": float(trade_net_pnl),
                            "equity_after": float(balance),
                        }
                    )
                    position = None

            if position is None and i + 1 < len(self.df):
                signal = self.calc_signal(row)
                if signal is not None:
                    entry_row = self.df.iloc[i + 1]
                    entry_price = self.entry_fill_price(entry_row, signal)
                    atr = float(row["atr"])
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
        report = {
            "engine": "ema_pullback_trend_v1_1",
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
            "lot_size": float(self.config.lot_size),
            "contract_size": int(self.config.contract_size),
            "leverage": float(self.config.leverage),
            "costs": {
                "slippage_pips": float(self.config.slippage_pips),
                "commission_per_lot_per_side": float(
                    self.config.commission_per_lot_per_side
                ),
                "spread_mean_points": float(self.df["spread"].mean()),
            },
            "params": {
                "ema_fast_period": int(self.config.ema_fast_period),
                "ema_slow_period": int(self.config.ema_slow_period),
                "atr_period": int(self.config.atr_period),
                "ema_slow_slope_filter": "long > 0 / short < 0",
                "pullback_depth_atr_mult": float(self.config.pullback_depth_atr_mult),
                "atr_sl_mult": float(self.config.atr_sl_mult),
                "tp_rr": float(self.config.tp_rr),
            },
            "equity_series": equity_series,
            "sample_trades": trades[:30],
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
            RESULT_DIR.mkdir(parents=True, exist_ok=True)
            output_path = RESULT_DIR / self._default_report_filename(report)
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return output_path


def resolve_input_file(cli_input: str | None) -> Path:
    if cli_input:
        path = Path(cli_input).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        return path

    candidates = sorted(EUR_DATA_DIR.glob("*.csv"))
    if not candidates:
        raise FileNotFoundError(
            f"No EUR CSV found in {EUR_DATA_DIR}. "
            "Please place your EURUSD M15 CSV there first."
        )
    return candidates[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "EMA Pullback Trend V1.1: EMA50/EMA200 trend + EMA200 slope filter + "
            "EMA50 pullback depth filter, ATR-based SL/TP."
        )
    )
    parser.add_argument("--input", default=None)
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Optional output JSON path. Defaults to "
            "data/engines/ema_pullback_trend_v1/report_YEAR.json."
        ),
    )
    parser.add_argument("--initial-balance", type=float, default=1000.0)
    parser.add_argument("--lot-size", type=float, default=0.005)
    parser.add_argument("--contract-size", type=int, default=100000)
    parser.add_argument("--leverage", type=float, default=100.0)
    parser.add_argument("--ema-fast-period", type=int, default=50)
    parser.add_argument("--ema-slow-period", type=int, default=200)
    parser.add_argument("--atr-period", type=int, default=14)
    parser.add_argument("--pullback-depth-atr-mult", type=float, default=0.3)
    parser.add_argument("--atr-sl-mult", type=float, default=1.5)
    parser.add_argument("--tp-rr", type=float, default=2.0)
    parser.add_argument("--slippage-pips", type=float, default=0.2)
    parser.add_argument("--commission-per-lot-per-side", type=float, default=3.5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = EngineConfig(
        input_file=resolve_input_file(args.input),
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
        slippage_pips=args.slippage_pips,
        commission_per_lot_per_side=args.commission_per_lot_per_side,
    )

    engine = EMAPullbackTrendV1Engine(config)
    engine.load_data()
    report = engine.run()

    output_path = None
    if args.output:
        output_path = Path(args.output).expanduser()
        if not output_path.is_absolute():
            output_path = (Path.cwd() / output_path).resolve()

    report_path = engine.save_report(report, output_path=output_path)
    print("EMA Pullback Trend V1.1 backtest finished.")
    print(json.dumps(report, indent=2))
    print(f"Saved report: {report_path}")


if __name__ == "__main__":
    main()
