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
RESULT_DIR = PROJECT_ROOT / "data" / "engines" / "engine_1"

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
    stop_out_level_pct: float = 50.0
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
    """Simple EURUSD M15 backtest with multiple concurrent positions."""

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
        out["atr"] = (
            out["tr"].ewm(alpha=1 / self.config.atr_period, adjust=False).mean()
        )

        # ADX
        up_move = out["high"].diff()
        down_move = -out["low"].diff()
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

        atr_for_adx = (
            out["tr"].ewm(alpha=1 / self.config.adx_period, adjust=False).mean()
        )
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
            100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
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
        signal_open = float(signal_row["open"])
        signal_close = float(signal_row["close"])
        confirm_close = float(confirm_row["close"])
        signal_rsi = float(signal_row["rsi"])
        confirm_rsi = float(confirm_row["rsi"])

        if side == "short":
            back_inside_band = confirm_close < float(confirm_row["bb_up"])
            price_reverting = confirm_close < signal_close
            signal_mid = (signal_open + signal_close) / 2.0
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
        signal_mid = (signal_open + signal_close) / 2.0
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

    def mark_to_market_exit_price(self, row: pd.Series, side: str) -> float:
        bid = float(row["close"])
        ask = bid + self.points_to_price(float(row["spread"]))
        if side == "long":
            return bid
        return ask

    def floating_pnl(self, position: dict[str, Any], row: pd.Series, bar_idx: int) -> float:
        if bar_idx < int(position["entry_idx"]):
            return 0.0
        side = str(position["side"])
        mtm_exit = self.mark_to_market_exit_price(row, side)
        return float(self.calc_pnl(float(position["entry_price"]), mtm_exit, side))

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
            "gross_loss_abs": -float(gross_loss_abs),
            "profit_factor": float(profit_factor),
            "expectancy_per_trade": float(expectancy),
            "sharpe_per_trade": float(sharpe_per_trade),
            "max_drawdown_abs": float(max_drawdown_abs),
            "max_drawdown_pct": float(max_drawdown_pct * 100.0),
        }

    def run(self) -> dict[str, Any]:
        if self.df is None:
            raise RuntimeError("Data not loaded. Call load_data() first.")
        if self.config.leverage <= 0:
            raise ValueError("leverage must be > 0")
        if self.config.stop_out_level_pct < 0:
            raise ValueError("stop_out_level_pct must be >= 0")

        balance = self.config.initial_balance
        margin_used = 0.0
        trades: list[dict[str, Any]] = []
        open_positions: list[dict[str, Any]] = []
        pending_entries: list[dict[str, Any]] = []
        stop_out_count = 0
        equity_series: list[dict[str, Any]] = []

        def close_position(
            position: dict[str, Any],
            exit_price: float,
            exit_reason: str,
            exit_time: pd.Timestamp,
        ) -> None:
            nonlocal balance, margin_used, stop_out_count
            side = str(position["side"])
            gross_pnl = self.calc_pnl(float(position["entry_price"]), float(exit_price), side)
            exit_commission = self.commission_one_side()
            pnl_after_exit_commission = gross_pnl - exit_commission
            balance += pnl_after_exit_commission
            margin_used -= float(position["margin_required"])
            if margin_used < 0:
                margin_used = 0.0
            trade_net_pnl = pnl_after_exit_commission - float(position["entry_commission"])

            trades.append(
                {
                    "side": side,
                    "signal_time": position["signal_time"].isoformat(),
                    "confirm_time": position["confirm_time"].isoformat(),
                    "entry_time": position["entry_time"].isoformat(),
                    "exit_time": exit_time.isoformat(),
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
            if exit_reason == "STOP_OUT":
                stop_out_count += 1

        for i in range(len(self.df)):
            row = self.df.iloc[i]
            bar_time = row["time"]
            next_bar_time = self.df.iloc[i + 1]["time"] if i + 1 < len(self.df) else None
            is_last_bar = i == len(self.df) - 1
            is_friday_last_bar = bar_time.weekday() == 4 and (
                next_bar_time is None or next_bar_time.weekday() != 4
            )

            # Activate pending entries when their entry bar arrives.
            if pending_entries:
                next_pending: list[dict[str, Any]] = []
                for pending in pending_entries:
                    if int(pending["entry_idx"]) != i:
                        next_pending.append(pending)
                        continue

                    side = str(pending["side"])

                    # Enforce one-direction exposure: close opposite side first.
                    if open_positions and str(open_positions[0]["side"]) != side:
                        for position in open_positions:
                            exit_px = self.exit_fill_price(row, str(position["side"]))
                            close_position(position, exit_px, "REVERSE_SIGNAL", bar_time)
                        open_positions = []

                    # Recalculate after potential reverse-close because balance/margin changed.
                    floating_now = sum(
                        self.floating_pnl(pos, row, i) for pos in open_positions
                    )
                    equity_now = balance + floating_now
                    free_margin = equity_now - margin_used

                    entry_price = self.entry_fill_price(row, side)
                    notional = entry_price * self.side_units()
                    margin_required = notional / self.config.leverage
                    entry_commission = self.commission_one_side()

                    if margin_required + entry_commission > free_margin:
                        continue

                    # Use the actual entry bar ATR for SL/TP sizing.
                    entry_row = self.df.iloc[int(pending["entry_idx"])]
                    atr = float(entry_row["atr"])
                    if side == "long":
                        sl = entry_price - self.config.atr_sl_mult * atr
                        tp = entry_price + self.config.atr_tp_mult * atr
                    else:
                        sl = entry_price + self.config.atr_sl_mult * atr
                        tp = entry_price - self.config.atr_tp_mult * atr

                    balance -= entry_commission
                    margin_used += margin_required
                    pending["sl"] = sl
                    pending["tp"] = tp
                    pending["entry_price"] = entry_price
                    pending["entry_commission"] = entry_commission
                    pending["margin_required"] = margin_required
                    open_positions.append(pending)
                pending_entries = next_pending

            # Stop-out check based on floating equity and margin level.
            if open_positions and margin_used > 0:
                while open_positions and margin_used > 0:
                    floating_now = sum(
                        self.floating_pnl(pos, row, i) for pos in open_positions
                    )
                    equity_now = balance + floating_now
                    margin_level_pct = (
                        (equity_now / margin_used) * 100.0
                        if margin_used > 0
                        else float("inf")
                    )
                    if margin_level_pct > self.config.stop_out_level_pct:
                        break

                    active_positions = [
                        pos for pos in open_positions if i >= int(pos["entry_idx"])
                    ]
                    if not active_positions:
                        break

                    # Stop-out should close the worst floating loss first, one by one.
                    worst_pos = min(
                        active_positions, key=lambda pos: self.floating_pnl(pos, row, i)
                    )
                    side = str(worst_pos["side"])
                    exit_price = self.exit_fill_price(row, side)
                    close_position(worst_pos, exit_price, "STOP_OUT", bar_time)
                    open_positions = [
                        pos for pos in open_positions if pos is not worst_pos
                    ]

            # Manage open position with intrabar SL/TP checks.
            if not open_positions:
                pass
            else:
                high_bid = float(row["high"])
                low_bid = float(row["low"])
                spread_px = self.points_to_price(float(row["spread"]))

                still_open: list[dict[str, Any]] = []
                for position in open_positions:
                    side = str(position["side"])
                    if i < int(position["entry_idx"]):
                        still_open.append(position)
                        continue

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

                    exit_now = hit_sl or hit_tp or is_friday_last_bar or is_last_bar
                    if not exit_now:
                        still_open.append(position)
                        continue

                    # If SL and TP both touched in same bar, assume SL first (conservative).
                    if hit_sl:
                        raw_exit = float(position["sl"])
                        exit_reason = "SL"
                    elif hit_tp:
                        raw_exit = float(position["tp"])
                        exit_reason = "TP"
                    elif is_friday_last_bar:
                        raw_exit = self.exit_fill_price(row, side)
                        exit_reason = "FRIDAY_FORCE_CLOSE"
                    else:
                        raw_exit = self.exit_fill_price(row, side)
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

                    close_position(position, float(exit_price), exit_reason, bar_time)
                open_positions = still_open

            # Generate new signals and queue entries for bar i+2.
            if i + 2 < len(self.df):
                signal = self.calc_signal(row)
                if signal is not None:
                    confirm_row = self.df.iloc[i + 1]
                    if self.confirm_reversion(row, confirm_row, signal):
                        # Enforce one-direction exposure: reverse immediately on opposite signal.
                        if open_positions and str(open_positions[0]["side"]) != signal:
                            for position in open_positions:
                                exit_px = self.exit_fill_price(row, str(position["side"]))
                                close_position(position, exit_px, "REVERSE_SIGNAL", bar_time)
                            open_positions = []

                        # Keep pending entries only for the current direction.
                        pending_entries = [
                            p for p in pending_entries if str(p["side"]) == signal
                        ]

                        entry_row = self.df.iloc[i + 2]

                        pending_entries.append(
                            {
                                "side": signal,
                                "signal_time": row["time"],
                                "confirm_time": confirm_row["time"],
                                "entry_idx": i + 2,
                                "entry_time": entry_row["time"],
                            }
                        )

            floating_now = sum(self.floating_pnl(pos, row, i) for pos in open_positions)
            equity_now = float(balance + floating_now)
            free_margin = float(equity_now - margin_used)
            margin_level_pct = (
                float((equity_now / margin_used) * 100.0) if margin_used > 0 else None
            )
            equity_series.append(
                {
                    "time": bar_time.isoformat(),
                    "balance": float(balance),
                    "equity": equity_now,
                    "margin_used": float(margin_used),
                    "free_margin": free_margin,
                    "margin_level_pct": margin_level_pct,
                    "open_positions": int(len(open_positions)),
                    "pending_entries": int(len(pending_entries)),
                }
            )

        wins = sum(1 for t in trades if t["net_pnl"] > 0)
        final_equity = (
            float(equity_series[-1]["equity"]) if equity_series else float(balance)
        )
        performance = self.compute_performance_metrics(
            trades=trades,
            initial_balance=float(self.config.initial_balance),
            final_balance=final_equity,
            equity_values=[float(point["equity"]) for point in equity_series],
        )
        report = {
            "engine": "eur_simple_adx_bb_rsi_atr",
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
            "risk": {
                "stop_out_level_pct": float(self.config.stop_out_level_pct),
                "stop_out_count": int(stop_out_count),
            },
            "equity_series": equity_series,
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

    def _default_report_filename(self, report: dict[str, Any]) -> str:
        # Prefer year from input filename, e.g. M15_2017.csv -> report_2017.json
        year_match = re.search(r"(19|20)\d{2}", self.config.input_file.stem)
        if year_match:
            return f"report_{year_match.group(0)}.json"

        # Fallback to report start year.
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
        description="Simple EURUSD M15 backtest: ADX<20 + BB touch + RSI with ATR SL/TP."
    )
    parser.add_argument("--input", default=None)
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output JSON path. Defaults to data/engines/engine_1/report_YEAR.json (YEAR inferred from input file).",
    )
    parser.add_argument("--initial-balance", type=float, default=1000.0)
    parser.add_argument("--lot-size", type=float, default=0.005)
    parser.add_argument("--contract-size", type=int, default=100000)
    parser.add_argument("--leverage", type=float, default=100.0)
    parser.add_argument(
        "--stop-out-level-pct",
        type=float,
        default=50.0,
        help="Force close when equity/margin_used*100 is <= this threshold.",
    )
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
        leverage=args.leverage,
        stop_out_level_pct=args.stop_out_level_pct,
        slippage_pips=args.slippage_pips,
        commission_per_lot_per_side=args.commission_per_lot_per_side,
        confirm_use_rsi=args.confirm_use_rsi,
    )

    engine = EURSimpleBacktestEngine(config)
    engine.load_data()
    report = engine.run()
    output_path = None
    if args.output:
        output_path = Path(args.output).expanduser()
        if not output_path.is_absolute():
            output_path = (Path.cwd() / output_path).resolve()

    report_path = engine.save_report(report, output_path=output_path)

    print("Simple EUR backtest finished.")
    print(json.dumps(report, indent=2))
    print(f"Saved report: {report_path}")


if __name__ == "__main__":
    main()
