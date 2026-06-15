from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MARKET_DATA_ROOT = PROJECT_ROOT / "xau" / "marketdata"
REPORT_ROOT = Path(__file__).resolve().parent / "reports"
TRAIN_YEARS = tuple(range(2015, 2024))
OOS_START_YEAR = 2024
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
    h4_file: Path
    h1_file: Path
    initial_balance: float = 10_000.0
    risk_per_trade_pct: float = 1.0
    min_lot: float = 0.01
    lot_step: float = 0.01
    max_lot: float = 100.0
    contract_size: int = 100
    leverage: float = 100.0

    donchian_breakout_period: int = 18
    atr_period: int = 14
    atr_ratio_lookback: int = 100
    atr_ratio_min: float = 1.1
    h1_adx_period: int = 14
    h1_adx_min: float = 18.0

    signal_mode: str = "intrabar"  # intrabar | close
    close_quality_min: float = 0.65
    spread_max_points: float = 30.0
    sl_atr_mult: float = 2.2
    trail_atr_mult: float = 3.2

    point_value: float = 0.01
    slippage_ticks: float = 1.0
    commission_per_lot_round_turn: float = 5.0


def year_from_path(path: Path) -> int:
    match = re.search(r"(19|20)\d{2}", path.stem)
    if not match:
        raise ValueError(f"Cannot determine year from market-data filename: {path}")
    return int(match.group(0))


def enforce_training_year(path: Path) -> int:
    year = year_from_path(path)
    if year >= OOS_START_YEAR:
        raise ValueError(
            f"VB V2 research refuses frozen OOS year {year}. "
            "Only 2015-2023 are allowed."
        )
    if year not in TRAIN_YEARS:
        raise ValueError(f"VB V2 training year must be 2015-2023, got {year}.")
    return year


def load_market_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    for column in REQUIRED_COLUMNS[1:]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    df.dropna(subset=["time", "open", "high", "low", "close", "spread"], inplace=True)
    df.sort_values("time", inplace=True)
    df.drop_duplicates(subset=["time"], keep="last", inplace=True)
    df.reset_index(drop=True, inplace=True)
    if df.empty:
        raise ValueError(f"No usable market data in {path}")
    return df


def calc_adx(df: pd.DataFrame, period: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    tr = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0.0), up_move, 0.0),
        index=df.index,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0.0), down_move, 0.0),
        index=df.index,
    )
    tr_smoothed = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_smoothed = plus_dm.ewm(alpha=1 / period, adjust=False).mean()
    minus_smoothed = minus_dm.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100.0 * plus_smoothed / tr_smoothed.replace(0.0, np.nan)
    minus_di = 100.0 * minus_smoothed / tr_smoothed.replace(0.0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(
        0.0, np.nan
    )
    return dx.ewm(alpha=1 / period, adjust=False).mean()


def max_drawdown(equity: list[float]) -> tuple[float, float]:
    peak = equity[0]
    max_abs = 0.0
    max_pct = 0.0
    for value in equity:
        peak = max(peak, value)
        drawdown = peak - value
        max_abs = max(max_abs, drawdown)
        if peak > 0.0:
            max_pct = max(max_pct, drawdown / peak * 100.0)
    return max_abs, max_pct


class VolatilityBreakoutV2Engine:
    def __init__(self, config: EngineConfig) -> None:
        self.config = config
        self.year = enforce_training_year(config.h4_file)
        if enforce_training_year(config.h1_file) != self.year:
            raise ValueError("H4 and H1 files must belong to the same training year.")
        self.df: pd.DataFrame | None = None

    def load_data(self) -> pd.DataFrame:
        h4 = load_market_data(self.config.h4_file)
        h1 = load_market_data(self.config.h1_file)

        tr = pd.concat(
            [
                h4["high"] - h4["low"],
                (h4["high"] - h4["close"].shift(1)).abs(),
                (h4["low"] - h4["close"].shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)
        h4["atr"] = tr.ewm(alpha=1 / self.config.atr_period, adjust=False).mean()
        slow_atr = h4["atr"].rolling(
            self.config.atr_ratio_lookback,
            min_periods=self.config.atr_ratio_lookback,
        ).mean()
        h4["atr_ratio"] = h4["atr"] / slow_atr.replace(0.0, np.nan)
        n = self.config.donchian_breakout_period
        h4["donchian_high"] = h4["high"].rolling(n, min_periods=n).max().shift(1)
        h4["donchian_low"] = h4["low"].rolling(n, min_periods=n).min().shift(1)

        h1["h1_adx"] = calc_adx(h1, self.config.h1_adx_period)
        h1_adx = h1.set_index("time")["h1_adx"].sort_index()
        # An H4 bar timestamp marks its open. At its close, the H1 bars opened
        # at H4+0h through H4+3h are complete, so H4+3h is the latest usable H1.
        latest_completed_h1_open = h4["time"] + pd.Timedelta(hours=3)
        h4["h1_adx"] = h1_adx.reindex(
            pd.DatetimeIndex(latest_completed_h1_open), method="ffill"
        ).to_numpy()

        h4.dropna(
            subset=["atr", "atr_ratio", "donchian_high", "donchian_low", "h1_adx"],
            inplace=True,
        )
        h4.reset_index(drop=True, inplace=True)
        self.df = h4
        return h4

    def signal(self, row: pd.Series) -> tuple[str | None, str | None]:
        if float(row["atr_ratio"]) < self.config.atr_ratio_min:
            return None, "atr_ratio"
        if float(row["h1_adx"]) < self.config.h1_adx_min:
            return None, "h1_adx"
        if float(row["spread"]) > self.config.spread_max_points:
            return None, "spread"

        if self.config.signal_mode == "close":
            up = float(row["close"]) > float(row["donchian_high"])
            down = float(row["close"]) < float(row["donchian_low"])
        else:
            up = float(row["high"]) >= float(row["donchian_high"])
            down = float(row["low"]) <= float(row["donchian_low"])
        if up and down:
            return None, "both_sides"
        side = "long" if up else "short" if down else None
        if side is None:
            return None, None

        if self.config.close_quality_min > 0.0:
            bar_range = float(row["high"] - row["low"])
            if bar_range <= 0.0:
                return None, "close_quality"
            close_position = float(row["close"] - row["low"]) / bar_range
            if side == "long" and close_position < self.config.close_quality_min:
                return None, "close_quality"
            if side == "short" and close_position > 1.0 - self.config.close_quality_min:
                return None, "close_quality"
        return side, None

    def lot_size(self, equity: float, stop_distance: float) -> float:
        risk_budget = equity * self.config.risk_per_trade_pct / 100.0
        raw_lot = risk_budget / (stop_distance * self.config.contract_size)
        stepped = math.floor(raw_lot / self.config.lot_step + 1e-12) * self.config.lot_step
        return min(stepped, self.config.max_lot) if stepped >= self.config.min_lot else 0.0

    def commission_side(self, lot: float) -> float:
        return lot * self.config.commission_per_lot_round_turn / 2.0

    def required_margin(self, price: float, lot: float) -> float:
        return price * lot * self.config.contract_size / self.config.leverage

    def pnl(self, entry: float, exit_price: float, side: str, lot: float) -> float:
        units = lot * self.config.contract_size
        return (
            (exit_price - entry) * units
            if side == "long"
            else (entry - exit_price) * units
        )

    def run(self) -> dict[str, Any]:
        if self.df is None:
            raise RuntimeError("Call load_data() before run().")
        df = self.df
        balance = self.config.initial_balance
        position: dict[str, Any] | None = None
        trades: list[dict[str, Any]] = []
        equity_curve: list[float] = [balance]
        reject_counts: dict[str, int] = {}

        for index, row in df.iterrows():
            if position is not None and index >= position["entry_idx"]:
                side = position["side"]
                spread_px = float(row["spread"]) * self.config.point_value
                stop = float(position["sl"])
                if side == "long":
                    hit_stop = float(row["low"]) <= stop
                    open_exit = float(row["open"])
                    raw_exit = min(stop, open_exit) if hit_stop else None
                else:
                    open_ask = float(row["open"]) + spread_px
                    high_ask = float(row["high"]) + spread_px
                    hit_stop = high_ask >= stop
                    raw_exit = max(stop, open_ask) if hit_stop else None

                if raw_exit is not None:
                    slip = self.config.slippage_ticks * self.config.point_value
                    exit_price = raw_exit - slip if side == "long" else raw_exit + slip
                    gross = self.pnl(
                        position["entry_price"], exit_price, side, position["lot"]
                    )
                    exit_commission = self.commission_side(position["lot"])
                    balance += gross - exit_commission
                    net = gross - position["entry_commission"] - exit_commission
                    trades.append(
                        {
                            "year": self.year,
                            "side": side,
                            "signal_time": position["signal_time"].isoformat(),
                            "entry_time": position["entry_time"].isoformat(),
                            "exit_time": row["time"].isoformat(),
                            "entry_price": position["entry_price"],
                            "exit_price": exit_price,
                            "initial_sl": position["initial_sl"],
                            "final_sl": stop,
                            "lot_size": position["lot"],
                            "initial_equity": position["initial_equity"],
                            "initial_risk_money": position["initial_risk_money"],
                            "initial_risk_pct": position["initial_risk_pct"],
                            "entry_atr": position["entry_atr"],
                            "entry_atr_ratio": position["entry_atr_ratio"],
                            "entry_h1_adx": position["entry_h1_adx"],
                            "gross_pnl": gross,
                            "commission": position["entry_commission"] + exit_commission,
                            "net_pnl": net,
                            "r_multiple": net / position["initial_risk_money"],
                            "holding_bars": index - position["entry_idx"] + 1,
                            "sl_update_count": position["sl_update_count"],
                            "exit_reason": "SL",
                        }
                    )
                    position = None
                else:
                    if side == "long":
                        position["extreme"] = max(position["extreme"], float(row["high"]))
                        new_sl = position["extreme"] - self.config.trail_atr_mult * float(
                            row["atr"]
                        )
                        updated = max(stop, new_sl)
                    else:
                        position["extreme"] = min(position["extreme"], float(row["low"]))
                        new_sl = position["extreme"] + self.config.trail_atr_mult * float(
                            row["atr"]
                        )
                        updated = min(stop, new_sl)
                    if updated != stop:
                        position["sl"] = updated
                        position["sl_update_count"] += 1

            if position is None and index + 1 < len(df):
                side, reason = self.signal(row)
                if side is None:
                    if reason:
                        reject_counts[reason] = reject_counts.get(reason, 0) + 1
                else:
                    entry_row = df.iloc[index + 1]
                    spread_px = float(entry_row["spread"]) * self.config.point_value
                    slip = self.config.slippage_ticks * self.config.point_value
                    entry_price = (
                        float(entry_row["open"]) + spread_px + slip
                        if side == "long"
                        else float(entry_row["open"]) - slip
                    )
                    # Only the completed signal bar is available at the next open.
                    entry_atr = float(row["atr"])
                    stop_distance = self.config.sl_atr_mult * entry_atr
                    lot = self.lot_size(balance, stop_distance)
                    if lot <= 0.0:
                        reject_counts["below_min_lot"] = (
                            reject_counts.get("below_min_lot", 0) + 1
                        )
                    else:
                        initial_sl = (
                            entry_price - stop_distance
                            if side == "long"
                            else entry_price + stop_distance
                        )
                        risk_money = stop_distance * lot * self.config.contract_size
                        entry_commission = self.commission_side(lot)
                        initial_equity = balance
                        required_margin = self.required_margin(entry_price, lot)
                        if balance - entry_commission < required_margin:
                            reject_counts["insufficient_margin"] = (
                                reject_counts.get("insufficient_margin", 0) + 1
                            )
                        else:
                            balance -= entry_commission
                            position = {
                                "side": side,
                                "signal_time": row["time"],
                                "entry_time": entry_row["time"],
                                "entry_idx": index + 1,
                                "entry_price": entry_price,
                                "initial_sl": initial_sl,
                                "sl": initial_sl,
                                "lot": lot,
                                "initial_equity": initial_equity,
                                "initial_risk_money": risk_money,
                                "initial_risk_pct": risk_money / initial_equity * 100.0,
                                "required_margin": required_margin,
                                "entry_atr": entry_atr,
                                "entry_atr_ratio": float(row["atr_ratio"]),
                                "entry_h1_adx": float(row["h1_adx"]),
                                "entry_commission": entry_commission,
                                "extreme": (
                                    float(entry_row["high"])
                                    if side == "long"
                                    else float(entry_row["low"])
                                ),
                                "sl_update_count": 0,
                            }

            floating = 0.0
            if position is not None and index >= position["entry_idx"]:
                exit_mark = (
                    float(row["close"])
                    if position["side"] == "long"
                    else float(row["close"])
                    + float(row["spread"]) * self.config.point_value
                )
                floating = self.pnl(
                    position["entry_price"],
                    exit_mark,
                    position["side"],
                    position["lot"],
                )
            equity_curve.append(balance + floating)

        if position is not None:
            row = df.iloc[-1]
            side = position["side"]
            spread_px = float(row["spread"]) * self.config.point_value
            slip = self.config.slippage_ticks * self.config.point_value
            exit_price = (
                float(row["close"]) - slip
                if side == "long"
                else float(row["close"]) + spread_px + slip
            )
            gross = self.pnl(position["entry_price"], exit_price, side, position["lot"])
            exit_commission = self.commission_side(position["lot"])
            balance += gross - exit_commission
            net = gross - position["entry_commission"] - exit_commission
            trades.append(
                {
                    "year": self.year,
                    "side": side,
                    "signal_time": position["signal_time"].isoformat(),
                    "entry_time": position["entry_time"].isoformat(),
                    "exit_time": row["time"].isoformat(),
                    "entry_price": position["entry_price"],
                    "exit_price": exit_price,
                    "initial_sl": position["initial_sl"],
                    "final_sl": position["sl"],
                    "lot_size": position["lot"],
                    "initial_equity": position["initial_equity"],
                    "initial_risk_money": position["initial_risk_money"],
                    "initial_risk_pct": position["initial_risk_pct"],
                    "entry_atr": position["entry_atr"],
                    "entry_atr_ratio": position["entry_atr_ratio"],
                    "entry_h1_adx": position["entry_h1_adx"],
                    "gross_pnl": gross,
                    "commission": position["entry_commission"] + exit_commission,
                    "net_pnl": net,
                    "r_multiple": net / position["initial_risk_money"],
                    "holding_bars": len(df) - position["entry_idx"],
                    "sl_update_count": position["sl_update_count"],
                    "exit_reason": "END_OF_DATA",
                }
            )
            equity_curve[-1] = balance
            position = None

        final_equity = equity_curve[-1]
        pnls = pd.Series([trade["net_pnl"] for trade in trades], dtype=float)
        gross_profit = float(pnls[pnls > 0.0].sum())
        gross_loss = float(-pnls[pnls < 0.0].sum())
        dd_abs, dd_pct = max_drawdown(equity_curve)
        return {
            "engine": "volatility_breakout_v2",
            "research_boundary": "2015-2023 only; 2024-2026 frozen OOS",
            "year": self.year,
            "h4_file": str(self.config.h4_file),
            "h1_file": str(self.config.h1_file),
            "config": {
                key: str(value) if isinstance(value, Path) else value
                for key, value in asdict(self.config).items()
            },
            "bars": len(df),
            "trades": len(trades),
            "initial_balance": self.config.initial_balance,
            "final_balance": balance,
            "final_equity": final_equity,
            "performance": {
                "net_pnl": final_equity - self.config.initial_balance,
                "return_pct": (
                    (final_equity / self.config.initial_balance - 1.0) * 100.0
                ),
                "win_rate": float((pnls > 0.0).mean()) if len(pnls) else 0.0,
                "profit_factor": gross_profit / gross_loss if gross_loss else 0.0,
                "average_r": float(
                    np.mean([trade["r_multiple"] for trade in trades])
                )
                if trades
                else 0.0,
                "sum_r": float(sum(trade["r_multiple"] for trade in trades)),
                "max_drawdown_abs": dd_abs,
                "max_drawdown_pct": dd_pct,
            },
            "reject_counts": reject_counts,
            "open_position_at_end": (
                {
                    "side": position["side"],
                    "entry_time": position["entry_time"].isoformat(),
                    "entry_price": position["entry_price"],
                    "initial_sl": position["initial_sl"],
                    "final_sl": position["sl"],
                    "lot_size": position["lot"],
                    "initial_risk_money": position["initial_risk_money"],
                    "initial_risk_pct": position["initial_risk_pct"],
                    "required_margin": position["required_margin"],
                }
                if position is not None
                else None
            ),
            "trade_details": trades,
        }


def configs_for_years(args: argparse.Namespace) -> list[EngineConfig]:
    if args.input:
        h4_file = Path(args.input).expanduser().resolve()
        year = enforce_training_year(h4_file)
        h1_file = MARKET_DATA_ROOT / "H1" / f"H1_{year}.csv"
        return [config_from_args(args, h4_file, h1_file)]
    years = [int(value) for value in args.years.split(",")]
    invalid = [year for year in years if year not in TRAIN_YEARS]
    if invalid:
        raise ValueError(f"Only 2015-2023 are allowed; invalid years: {invalid}")
    return [
        config_from_args(
            args,
            MARKET_DATA_ROOT / "H4" / f"H4_{year}.csv",
            MARKET_DATA_ROOT / "H1" / f"H1_{year}.csv",
        )
        for year in years
    ]


def config_from_args(args: argparse.Namespace, h4_file: Path, h1_file: Path) -> EngineConfig:
    return EngineConfig(
        h4_file=h4_file,
        h1_file=h1_file,
        initial_balance=args.initial_balance,
        risk_per_trade_pct=args.risk_per_trade_pct,
        min_lot=args.min_lot,
        lot_step=args.lot_step,
        signal_mode=args.signal_mode,
        close_quality_min=args.close_quality_min,
        atr_ratio_min=args.atr_ratio_min,
        h1_adx_min=args.h1_adx_min,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="XAU VB V2 training-only research engine.")
    parser.add_argument("--input")
    parser.add_argument("--years", default="2015,2016,2017,2018,2019,2020,2021,2022,2023")
    parser.add_argument("--output-dir", type=Path, default=REPORT_ROOT)
    parser.add_argument("--initial-balance", type=float, default=10_000.0)
    parser.add_argument("--risk-per-trade-pct", type=float, default=1.0)
    parser.add_argument("--min-lot", type=float, default=0.01)
    parser.add_argument("--lot-step", type=float, default=0.01)
    parser.add_argument("--signal-mode", choices=("intrabar", "close"), default="intrabar")
    parser.add_argument("--close-quality-min", type=float, default=0.65)
    parser.add_argument("--atr-ratio-min", type=float, default=1.1)
    parser.add_argument("--h1-adx-min", type=float, default=18.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for config in configs_for_years(args):
        engine = VolatilityBreakoutV2Engine(config)
        engine.load_data()
        report = engine.run()
        path = output_dir / f"report_{engine.year}.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        summaries.append({"year": engine.year, **report["performance"], "trades": report["trades"]})
        print(
            f"{engine.year}: trades={report['trades']} "
            f"return={report['performance']['return_pct']:.2f}% "
            f"DD={report['performance']['max_drawdown_pct']:.2f}%"
        )
    pd.DataFrame(summaries).to_csv(output_dir / "summary.csv", index=False)


if __name__ == "__main__":
    main()
