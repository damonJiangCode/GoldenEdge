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
XAU_DATA_DIR = PROJECT_ROOT / "xau" / "marketdata"
RESULT_DIR = Path(__file__).resolve().parent / "reports"

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

    donchian_breakout_period: int = 18
    donchian_exit_period: int = 10
    atr_period: int = 14
    atr_ratio_lookback: int = 100
    atr_ratio_min: float = 1.0

    enable_h1_adx_filter: bool = True
    adx_period: int = 14
    h1_adx_min: float = 18.0

    spread_max_points: float = 30.0
    session_start_hour_utc: int = 0
    session_end_hour_utc: int = 24

    sl_atr_mult: float = 2.2
    trail_mode: str = "chandelier"  # chandelier | donchian
    trail_atr_mult: float = 3.2

    point_value: float = 0.01
    pip_value: float = 0.01
    slippage_ticks: float = 1.0
    commission_per_trade: float = 0.05
    swap_long_per_lot_per_night: float = 0.0
    swap_short_per_lot_per_night: float = 0.0


class VolatilityBreakoutV1Engine:
    def __init__(self, config: EngineConfig) -> None:
        self.config = config
        self.df: pd.DataFrame | None = None

    def points_to_price(self, points: float) -> float:
        return points * self.config.point_value

    def ticks_to_price(self, ticks: float) -> float:
        return ticks * self.config.point_value

    def side_units(self) -> float:
        return self.config.lot_size * self.config.contract_size

    def commission_one_side(self) -> float:
        return self.config.commission_per_trade / 2.0

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

    def mark_to_market_exit_price(self, row: pd.Series, side: str) -> float:
        bid = float(row["close"])
        ask = bid + self.points_to_price(float(row["spread"]))
        if side == "long":
            return bid
        return ask

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
    def _calc_adx(df: pd.DataFrame, period: int) -> pd.Series:
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = pd.Series(
            np.where((up_move > down_move) & (up_move > 0.0), up_move, 0.0), index=df.index
        )
        minus_dm = pd.Series(
            np.where((down_move > up_move) & (down_move > 0.0), down_move, 0.0), index=df.index
        )

        tr_smoothed = tr.ewm(alpha=1 / period, adjust=False).mean()
        plus_dm_smoothed = plus_dm.ewm(alpha=1 / period, adjust=False).mean()
        minus_dm_smoothed = minus_dm.ewm(alpha=1 / period, adjust=False).mean()

        plus_di = 100.0 * plus_dm_smoothed / tr_smoothed.replace(0.0, np.nan)
        minus_di = 100.0 * minus_dm_smoothed / tr_smoothed.replace(0.0, np.nan)
        dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
        adx = dx.ewm(alpha=1 / period, adjust=False).mean()
        return adx

    def _build_h1_adx_map(self, df: pd.DataFrame) -> pd.Series:
        h1 = (
            df.set_index("time")
            .resample("1h")
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "tick_volume": "sum",
                    "spread": "mean",
                }
            )
            .dropna(subset=["open", "high", "low", "close"])
        )
        if h1.empty:
            return pd.Series(dtype=float)
        h1["adx"] = self._calc_adx(h1, self.config.adx_period)
        return h1["adx"]

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
        df.dropna(subset=["time", "open", "high", "low", "close", "spread"], inplace=True)
        df.reset_index(drop=True, inplace=True)
        if df.empty:
            raise ValueError("Input CSV has no rows after cleaning.")

        out = df.copy()
        high_low = out["high"] - out["low"]
        high_prev_close = (out["high"] - out["close"].shift(1)).abs()
        low_prev_close = (out["low"] - out["close"].shift(1)).abs()
        out["tr"] = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
        out["atr"] = out["tr"].ewm(alpha=1 / self.config.atr_period, adjust=False).mean()
        atr_slow = out["atr"].rolling(
            window=self.config.atr_ratio_lookback,
            min_periods=self.config.atr_ratio_lookback,
        ).mean()
        out["atr_ratio"] = out["atr"] / atr_slow.replace(0.0, np.nan)

        n = self.config.donchian_breakout_period
        m = self.config.donchian_exit_period
        out["donchian_high_n"] = out["high"].rolling(window=n, min_periods=n).max().shift(1)
        out["donchian_low_n"] = out["low"].rolling(window=n, min_periods=n).min().shift(1)
        out["donchian_exit_high_m"] = out["high"].rolling(window=m, min_periods=m).max().shift(1)
        out["donchian_exit_low_m"] = out["low"].rolling(window=m, min_periods=m).min().shift(1)

        h1_adx = self._build_h1_adx_map(out)
        out["h1_time"] = out["time"].dt.floor("h")
        out["h1_adx"] = out["h1_time"].map(h1_adx)

        out.dropna(
            subset=[
                "atr",
                "atr_ratio",
                "donchian_high_n",
                "donchian_low_n",
                "donchian_exit_high_m",
                "donchian_exit_low_m",
                "h1_adx",
            ],
            inplace=True,
        )
        out.reset_index(drop=True, inplace=True)
        self.df = out
        return out

    def _is_in_session(self, ts: pd.Timestamp) -> bool:
        hour = int(ts.hour)
        return self.config.session_start_hour_utc <= hour < self.config.session_end_hour_utc

    def _filter_ok(self, row: pd.Series) -> tuple[bool, str | None]:
        if float(row["atr_ratio"]) < self.config.atr_ratio_min:
            return False, "atr_ratio_filter"
        if float(row["spread"]) > self.config.spread_max_points:
            return False, "spread_filter"
        if self.config.enable_h1_adx_filter and float(row["h1_adx"]) < self.config.h1_adx_min:
            return False, "adx_filter"
        return True, None

    def calc_signal(self, row: pd.Series) -> tuple[str | None, str | None]:
        ok, reason = self._filter_ok(row)
        if not ok:
            return None, reason
        hit_up = float(row["high"]) >= float(row["donchian_high_n"])
        hit_dn = float(row["low"]) <= float(row["donchian_low_n"])
        if hit_up and hit_dn:
            return None, "both_breakout_same_bar"
        if hit_up:
            return "long", None
        if hit_dn:
            return "short", None
        return None, None

    @staticmethod
    def pnl_result(net_pnl: float, epsilon: float = 1e-9) -> str:
        if net_pnl > epsilon:
            return "profit"
        if net_pnl < -epsilon:
            return "loss"
        return "flat"

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
            max_drawdown_abs = max(max_drawdown_abs, dd_abs)
            max_drawdown_pct = max(max_drawdown_pct, dd_pct)

        return {
            "net_pnl": float(net_pnl),
            "return_pct": float((net_pnl / initial_balance) * 100.0) if initial_balance else 0.0,
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

        total_swap = 0.0
        total_commission = 0.0

        session_reject_count = 0
        atr_ratio_filter_reject_count = 0
        spread_filter_reject_count = 0
        adx_filter_reject_count = 0
        both_breakout_reject_count = 0
        trail_move_count = 0

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
                            "sl": float(position["sl"]),
                            "entry_atr": float(position["entry_atr"]),
                            "entry_atr_ratio": float(position["entry_atr_ratio"]),
                            "entry_h1_adx": float(position["entry_h1_adx"]),
                            "exit_reason": exit_reason,
                            "gross_pnl": float(gross_pnl),
                            "swap_total": float(swap_total),
                            "entry_commission": float(position["entry_commission"]),
                            "exit_commission": float(exit_commission),
                            "net_pnl": float(trade_net_pnl),
                            "pnl_result": self.pnl_result(float(trade_net_pnl)),
                            "equity_after": float(balance),
                            "holding_bars": int(i - int(position["entry_idx"]) + 1),
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
                else:
                    entry_row = self.df.iloc[i + 1]
                    if not self._is_in_session(entry_row["time"]):
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
                            "entry_atr": float(atr),
                            "entry_atr_ratio": float(entry_row["atr_ratio"]),
                            "entry_h1_adx": float(entry_row["h1_adx"]),
                            "highest_since_entry": float(entry_row["high"]),
                            "lowest_since_entry": float(entry_row["low"]),
                            "entry_commission": float(entry_commission),
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
            "engine": "volatility_breakout_v1",
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
            },
            "params": {
                "donchian_breakout_period": int(self.config.donchian_breakout_period),
                "donchian_exit_period": int(self.config.donchian_exit_period),
                "atr_period": int(self.config.atr_period),
                "atr_ratio_lookback": int(self.config.atr_ratio_lookback),
                "sl_atr_mult": float(self.config.sl_atr_mult),
                "trail_mode": str(self.config.trail_mode),
                "trail_atr_mult": float(self.config.trail_atr_mult),
                "entry_logic": "intrabar donchian breakout (high/low trigger), next bar market entry",
                "exit_logic": "SL + trailing stop (chandelier/donchian)",
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

    def _default_report_filename(self) -> str:
        year_match = re.search(r"(19|20)\d{2}", self.config.input_file.stem)
        if year_match:
            return f"report_{year_match.group(0)}.json"
        return "report_UNKNOWN_YEAR.json"

    def save_report(self, report: dict[str, Any], output_path: Path | None = None) -> Path:
        if output_path is None:
            tf_dir = RESULT_DIR / self.timeframe_label()
            tf_dir.mkdir(parents=True, exist_ok=True)
            output_path = tf_dir / self._default_report_filename()
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return output_path


def resolve_input_files(cli_input: str | None, timeframes: list[str]) -> list[Path]:
    if cli_input:
        path = Path(cli_input).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        return [path]

    allowed = {tf.upper() for tf in timeframes}
    candidates = sorted(XAU_DATA_DIR.rglob("*.csv"))
    candidates = [p for p in candidates if p.parent.name.upper() in allowed]
    if not candidates:
        raise FileNotFoundError(
            f"No XAU CSV found under {XAU_DATA_DIR} for timeframes={sorted(allowed)}."
        )
    return candidates


def parse_timeframes(raw: str) -> list[str]:
    vals = [x.strip().upper() for x in raw.split(",") if x.strip()]
    if not vals:
        raise ValueError("--timeframes cannot be empty.")
    for tf in vals:
        if not re.fullmatch(r"[MHDW]\d+", tf):
            raise ValueError(f"Invalid timeframe token: {tf}")
    return vals


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "XAU Volatility Breakout V1: Donchian breakout + ATR expansion + "
            "spread/adx filters + trailing stop."
        )
    )
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--timeframes",
        default="H4",
        help="Comma separated list when --input is not provided. Default: H4",
    )

    parser.add_argument("--initial-balance", type=float, default=1000.0)
    parser.add_argument("--lot-size", type=float, default=0.01)
    parser.add_argument("--contract-size", type=int, default=100)
    parser.add_argument("--leverage", type=float, default=100.0)

    parser.add_argument("--donchian-breakout-period", type=int, default=18)
    parser.add_argument("--donchian-exit-period", type=int, default=10)
    parser.add_argument("--atr-period", type=int, default=14)
    parser.add_argument("--atr-ratio-lookback", type=int, default=100)
    parser.add_argument("--atr-ratio-min", type=float, default=1.0)

    parser.add_argument("--enable-h1-adx-filter", action="store_true")
    parser.add_argument("--disable-h1-adx-filter", action="store_true")
    parser.add_argument("--adx-period", type=int, default=14)
    parser.add_argument("--h1-adx-min", type=float, default=18.0)

    parser.add_argument("--spread-max-points", type=float, default=30.0)
    parser.add_argument("--session-start-hour-utc", type=int, default=0)
    parser.add_argument("--session-end-hour-utc", type=int, default=24)

    parser.add_argument("--sl-atr-mult", type=float, default=2.2)
    parser.add_argument(
        "--trail-mode",
        choices=["chandelier", "donchian"],
        default="chandelier",
    )
    parser.add_argument("--trail-atr-mult", type=float, default=3.2)

    parser.add_argument("--point-value", type=float, default=0.01)
    parser.add_argument("--pip-value", type=float, default=0.01)
    parser.add_argument("--slippage-ticks", type=float, default=1.0)
    parser.add_argument("--commission-per-trade", type=float, default=0.05)
    parser.add_argument("--swap-long-per-lot-per-night", type=float, default=0.0)
    parser.add_argument("--swap-short-per-lot-per-night", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    timeframes = parse_timeframes(args.timeframes)
    input_files = resolve_input_files(args.input, timeframes=timeframes)

    enable_h1_adx_filter = True
    if args.enable_h1_adx_filter:
        enable_h1_adx_filter = True
    if args.disable_h1_adx_filter:
        enable_h1_adx_filter = False

    explicit_output = None
    if args.output:
        explicit_output = Path(args.output).expanduser()
        if not explicit_output.is_absolute():
            explicit_output = (Path.cwd() / explicit_output).resolve()
        if len(input_files) > 1:
            raise ValueError("--output is only allowed when using a single input file.")

    report_paths: list[Path] = []
    reports: list[dict[str, Any]] = []
    for idx, input_file in enumerate(input_files, start=1):
        config = EngineConfig(
            input_file=input_file,
            initial_balance=args.initial_balance,
            lot_size=args.lot_size,
            contract_size=args.contract_size,
            leverage=args.leverage,
            donchian_breakout_period=args.donchian_breakout_period,
            donchian_exit_period=args.donchian_exit_period,
            atr_period=args.atr_period,
            atr_ratio_lookback=args.atr_ratio_lookback,
            atr_ratio_min=args.atr_ratio_min,
            enable_h1_adx_filter=enable_h1_adx_filter,
            adx_period=args.adx_period,
            h1_adx_min=args.h1_adx_min,
            spread_max_points=args.spread_max_points,
            session_start_hour_utc=args.session_start_hour_utc,
            session_end_hour_utc=args.session_end_hour_utc,
            sl_atr_mult=args.sl_atr_mult,
            trail_mode=args.trail_mode,
            trail_atr_mult=args.trail_atr_mult,
            point_value=args.point_value,
            pip_value=args.pip_value,
            slippage_ticks=args.slippage_ticks,
            commission_per_trade=args.commission_per_trade,
            swap_long_per_lot_per_night=args.swap_long_per_lot_per_night,
            swap_short_per_lot_per_night=args.swap_short_per_lot_per_night,
        )

        engine = VolatilityBreakoutV1Engine(config)
        engine.load_data()
        report = engine.run()
        report_path = engine.save_report(report, output_path=explicit_output)
        report_paths.append(report_path)
        reports.append(report)
        print(f"[{idx}/{len(input_files)}] finished {input_file.name} -> {report_path}")

    print("Volatility Breakout V1 backtest finished.")
    if len(reports) == 1:
        print(json.dumps(reports[0], indent=2))
    print("Saved reports:")
    for path in report_paths:
        print(path)


if __name__ == "__main__":
    main()
