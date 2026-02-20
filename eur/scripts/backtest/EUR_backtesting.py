from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EUR_DATA_DIR = PROJECT_ROOT / "data" / "historical"
RESULT_DIR = PROJECT_ROOT / "data" / "backtest_results"

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
    adx_period: int = 14
    rsi_period: int = 14
    bb_period: int = 20
    bb_std: float = 2.0
    atr_period: int = 14
    adx_range_threshold: float = 20.0
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    atr_sl_mult: float = 1.0
    atr_tp_mult: float = 2.0
    slippage_pips: float = 0.2
    commission_per_lot_per_side: float = 3.5
    confirm_use_rsi: bool = False


class EURSimpleBacktestEngine:
    """Simple EURUSD M15 backtest with one position at a time."""

    def __init__(self, config: EngineConfig) -> None:
        self.config = config
        self.df: pd.DataFrame | None = None

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
        df.dropna(subset=["time", "open", "high", "low", "close", "spread"], inplace=True)
        df.reset_index(drop=True, inplace=True)

        if df.empty:
            raise ValueError("Input CSV has no rows after cleaning.")

        self.df = self.compute_indicators(df)
        return self.df

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()

        # Bollinger Bands
        out["bb_mid"] = out["close"].rolling(self.config.bb_period).mean()
        bb_std = out["close"].rolling(self.config.bb_period).std(ddof=0)
        out["bb_up"] = out["bb_mid"] + self.config.bb_std * bb_std
        out["bb_dn"] = out["bb_mid"] - self.config.bb_std * bb_std

        # RSI (Wilder style via EWM)
        delta = out["close"].diff()
        gain = delta.clip(lower=0.0)
        loss = -delta.clip(upper=0.0)
        avg_gain = gain.ewm(alpha=1 / self.config.rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / self.config.rsi_period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0.0, np.nan)
        out["rsi"] = 100 - (100 / (1 + rs))

        # TR / ATR
        high_low = out["high"] - out["low"]
        high_prev_close = (out["high"] - out["close"].shift(1)).abs()
        low_prev_close = (out["low"] - out["close"].shift(1)).abs()
        out["tr"] = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(
            axis=1
        )
        out["atr"] = out["tr"].ewm(alpha=1 / self.config.atr_period, adjust=False).mean()

        # ADX
        up_move = out["high"].diff()
        down_move = -out["low"].diff()
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

        atr_for_adx = out["tr"].ewm(alpha=1 / self.config.adx_period, adjust=False).mean()
        plus_di = (
            100
            * plus_dm.ewm(alpha=1 / self.config.adx_period, adjust=False).mean()
            / atr_for_adx.replace(0.0, np.nan)
        )
        minus_di = (
            100
            * minus_dm.ewm(alpha=1 / self.config.adx_period, adjust=False).mean()
            / atr_for_adx.replace(0.0, np.nan)
        )
        dx = (
            100
            * (plus_di - minus_di).abs()
            / (plus_di + minus_di).replace(0.0, np.nan)
        )
        out["adx"] = dx.ewm(alpha=1 / self.config.adx_period, adjust=False).mean()

        out.dropna(inplace=True)
        out.reset_index(drop=True, inplace=True)
        return out

    def calc_signal(self, row: pd.Series) -> str | None:
        if float(row["adx"]) >= self.config.adx_range_threshold:
            return None

        touch_upper = float(row["close"]) >= float(row["bb_up"])
        touch_lower = float(row["close"]) <= float(row["bb_dn"])
        overbought = float(row["rsi"]) >= self.config.rsi_overbought
        oversold = float(row["rsi"]) <= self.config.rsi_oversold

        if touch_upper and overbought:
            return "short"
        if touch_lower and oversold:
            return "long"
        return None

    def confirm_reversion(
        self, signal_row: pd.Series, confirm_row: pd.Series, side: str
    ) -> bool:
        # Confirmation bar should show a move back toward the BB middle.
        signal_close = float(signal_row["close"])
        confirm_close = float(confirm_row["close"])
        confirm_rsi = float(confirm_row["rsi"])
        signal_rsi = float(signal_row["rsi"])

        if side == "short":
            back_inside_band = confirm_close < float(confirm_row["bb_up"])
            price_reverting = confirm_close < signal_close
            signal_mid = (float(signal_row["open"]) + signal_close) / 2.0
            deep_reversion = confirm_close <= signal_mid
            # Stronger RSI confirmation: move back inside from overbought zone.
            rsi_reverting = (
                signal_rsi >= self.config.rsi_overbought
                and confirm_rsi < self.config.rsi_overbought
            )
            if self.config.confirm_use_rsi:
                return (
                    back_inside_band
                    and price_reverting
                    and deep_reversion
                    and rsi_reverting
                )
            return back_inside_band and price_reverting and deep_reversion

        back_inside_band = confirm_close > float(confirm_row["bb_dn"])
        price_reverting = confirm_close > signal_close
        signal_mid = (float(signal_row["open"]) + signal_close) / 2.0
        deep_reversion = confirm_close >= signal_mid
        # Stronger RSI confirmation: move back inside from oversold zone.
        rsi_reverting = (
            signal_rsi <= self.config.rsi_oversold
            and confirm_rsi > self.config.rsi_oversold
        )
        if self.config.confirm_use_rsi:
            return (
                back_inside_band
                and price_reverting
                and deep_reversion
                and rsi_reverting
            )
        return back_inside_band and price_reverting and deep_reversion

    @staticmethod
    def points_to_price(points: float) -> float:
        # EURUSD in MT style: 1 point = 0.00001
        return points * 0.00001

    @staticmethod
    def pips_to_price(pips: float) -> float:
        return pips * 0.0001

    def side_units(self) -> float:
        return self.config.lot_size * self.config.contract_size

    def commission_one_side(self) -> float:
        return self.config.lot_size * self.config.commission_per_lot_per_side

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

    def calc_pnl(self, entry_price: float, exit_price: float, side: str) -> float:
        units = self.side_units()
        if side == "long":
            return (exit_price - entry_price) * units
        return (entry_price - exit_price) * units

    def run(self) -> dict[str, Any]:
        if self.df is None:
            raise RuntimeError("Data not loaded. Call load_data() first.")

        equity = self.config.initial_balance
        trades: list[dict[str, Any]] = []
        position: dict[str, Any] | None = None

        for i in range(len(self.df) - 1):
            row = self.df.iloc[i]

            if position is None:
                if i + 2 >= len(self.df):
                    continue
                signal = self.calc_signal(row)
                if signal is None:
                    continue

                confirm_row = self.df.iloc[i + 1]
                if not self.confirm_reversion(row, confirm_row, signal):
                    continue

                entry_row = self.df.iloc[i + 2]
                entry_price = self.entry_fill_price(entry_row, signal)
                notional = entry_price * self.side_units()
                entry_commission = self.commission_one_side()

                # No leverage: require notional + entry commission <= current equity.
                if notional + entry_commission > equity:
                    continue

                equity -= entry_commission
                atr = float(row["atr"])
                if signal == "long":
                    sl = entry_price - self.config.atr_sl_mult * atr
                    tp = entry_price + self.config.atr_tp_mult * atr
                else:
                    sl = entry_price + self.config.atr_sl_mult * atr
                    tp = entry_price - self.config.atr_tp_mult * atr

                position = {
                    "side": signal,
                    "signal_time": row["time"],
                    "confirm_time": confirm_row["time"],
                    "entry_idx": i + 2,
                    "entry_time": entry_row["time"],
                    "entry_price": entry_price,
                    "sl": sl,
                    "tp": tp,
                    "entry_commission": entry_commission,
                }
                continue

            # Manage open position with intrabar SL/TP checks.
            bar = self.df.iloc[i]
            side = str(position["side"])
            if i < int(position["entry_idx"]):
                continue
            bar_time = bar["time"]
            next_bar_time = self.df.iloc[i + 1]["time"]

            high_bid = float(bar["high"])
            low_bid = float(bar["low"])
            spread_px = self.points_to_price(float(bar["spread"]))

            if side == "long":
                # Long exits are on bid.
                hit_sl = low_bid <= float(position["sl"])
                hit_tp = high_bid >= float(position["tp"])
            else:
                # Short exits are on ask = bid + spread.
                high_ask = high_bid + spread_px
                low_ask = low_bid + spread_px
                hit_sl = high_ask >= float(position["sl"])
                hit_tp = low_ask <= float(position["tp"])

            is_friday_last_bar = (
                bar_time.weekday() == 4 and next_bar_time.weekday() != 4
            )
            exit_now = hit_sl or hit_tp or is_friday_last_bar
            if not exit_now and i < len(self.df) - 2:
                continue

            # If SL and TP both touched in same bar, assume SL first (conservative).
            if hit_sl:
                raw_exit = float(position["sl"])
                exit_reason = "SL"
            elif hit_tp:
                raw_exit = float(position["tp"])
                exit_reason = "TP"
            elif is_friday_last_bar:
                raw_exit = self.exit_fill_price(bar, side)
                exit_reason = "FRIDAY_FORCE_CLOSE"
            else:
                raw_exit = self.exit_fill_price(bar, side)
                exit_reason = "EOD"

            # Add slippage to exit trigger fills too.
            slip = self.pips_to_price(self.config.slippage_pips)
            if exit_reason in {"SL", "TP"}:
                if side == "long":
                    exit_price = raw_exit - slip
                else:
                    exit_price = raw_exit + slip
            else:
                exit_price = raw_exit

            gross_pnl = self.calc_pnl(float(position["entry_price"]), exit_price, side)
            exit_commission = self.commission_one_side()
            pnl_after_exit_commission = gross_pnl - exit_commission
            equity += pnl_after_exit_commission
            trade_net_pnl = pnl_after_exit_commission - float(position["entry_commission"])

            trades.append(
                {
                    "side": side,
                    "signal_time": position["signal_time"].isoformat(),
                    "confirm_time": position["confirm_time"].isoformat(),
                    "entry_time": position["entry_time"].isoformat(),
                    "exit_time": bar["time"].isoformat(),
                    "entry_price": float(position["entry_price"]),
                    "exit_price": float(exit_price),
                    "sl": float(position["sl"]),
                    "tp": float(position["tp"]),
                    "exit_reason": exit_reason,
                    "gross_pnl": float(gross_pnl),
                    "entry_commission": float(position["entry_commission"]),
                    "exit_commission": float(exit_commission),
                    "net_pnl": float(trade_net_pnl),
                    "equity_after": float(equity),
                }
            )
            position = None

        wins = sum(1 for t in trades if t["net_pnl"] > 0)
        report = {
            "engine": "eur_simple_adx_bb_rsi_atr",
            "input_file": str(self.config.input_file),
            "bars": int(len(self.df)),
            "time_start_utc": self.df.iloc[0]["time"].isoformat(),
            "time_end_utc": self.df.iloc[-1]["time"].isoformat(),
            "initial_balance": float(self.config.initial_balance),
            "final_balance": float(equity),
            "trades": int(len(trades)),
            "win_rate": float((wins / len(trades)) if trades else 0.0),
            "lot_size": float(self.config.lot_size),
            "contract_size": int(self.config.contract_size),
            "costs": {
                "slippage_pips": float(self.config.slippage_pips),
                "commission_per_lot_per_side": float(
                    self.config.commission_per_lot_per_side
                ),
                "spread_mean_points": float(self.df["spread"].mean()),
            },
            "params": {
                "adx_range_threshold": float(self.config.adx_range_threshold),
                "rsi_overbought": float(self.config.rsi_overbought),
                "rsi_oversold": float(self.config.rsi_oversold),
                "atr_sl_mult": float(self.config.atr_sl_mult),
                "atr_tp_mult": float(self.config.atr_tp_mult),
                "confirm_use_rsi": bool(self.config.confirm_use_rsi),
            },
            "sample_trades": trades[:30],
        }
        return report

    def save_report(self, report: dict[str, Any]) -> Path:
        RESULT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = RESULT_DIR / "EUR_simple_backtest_report.json"
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
        description="Simple EURUSD M15 backtest: ADX<20 + BB touch + RSI with ATR SL/TP."
    )
    parser.add_argument("--input", default=None)
    parser.add_argument("--initial-balance", type=float, default=1000.0)
    parser.add_argument("--lot-size", type=float, default=0.005)
    parser.add_argument("--contract-size", type=int, default=100000)
    parser.add_argument("--slippage-pips", type=float, default=0.2)
    parser.add_argument("--commission-per-lot-per-side", type=float, default=3.5)
    parser.add_argument(
        "--confirm-use-rsi",
        action="store_true",
        help="Use RSI direction as an extra confirmation filter.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = EngineConfig(
        input_file=resolve_input_file(args.input),
        initial_balance=args.initial_balance,
        lot_size=args.lot_size,
        contract_size=args.contract_size,
        slippage_pips=args.slippage_pips,
        commission_per_lot_per_side=args.commission_per_lot_per_side,
        confirm_use_rsi=args.confirm_use_rsi,
    )

    engine = EURSimpleBacktestEngine(config)
    engine.load_data()
    report = engine.run()
    report_path = engine.save_report(report)

    print("Simple EUR backtest finished.")
    print(json.dumps(report, indent=2))
    print(f"Saved report: {report_path}")


if __name__ == "__main__":
    main()
