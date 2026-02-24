from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

try:
    import MetaTrader5 as mt5
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "MetaTrader5 package is not installed. Install with: pip install MetaTrader5"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "data" / "historiccal"
DEFAULT_SYMBOL = "XAUUSD"

TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download one year of MT5 historical data and save to "
            "data/historiccal/<TIMEFRAME>/<TIMEFRAME>_<YEAR>.csv."
        )
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Year to download, e.g. 2024.",
    )
    parser.add_argument(
        "--timeframe",
        default="M1",
        choices=sorted(TIMEFRAME_MAP.keys()),
        help="MT5 timeframe (default: M1).",
    )
    parser.add_argument(
        "--symbol",
        default=DEFAULT_SYMBOL,
        help=f"Trading symbol (default: {DEFAULT_SYMBOL}).",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Output root directory (default: xau/data/historiccal).",
    )
    parser.add_argument(
        "--terminal-path",
        default=os.getenv("MT5_TERMINAL_PATH"),
        help="MT5 terminal executable path. Optional.",
    )
    parser.add_argument("--login", type=int, default=None, help="MT5 account login.")
    parser.add_argument("--password", default=None, help="MT5 account password.")
    parser.add_argument("--server", default=None, help="MT5 server name.")
    return parser.parse_args()


def initialize_mt5(args: argparse.Namespace) -> None:
    ok = mt5.initialize(path=args.terminal_path) if args.terminal_path else mt5.initialize()
    if not ok:
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    if args.login is not None:
        if not args.password or not args.server:
            raise ValueError(
                "When --login is provided, --password and --server are required."
            )
        if not mt5.login(args.login, password=args.password, server=args.server):
            raise RuntimeError(f"MT5 login failed: {mt5.last_error()}")


def get_year_bars(symbol: str, timeframe: str, year: int) -> pd.DataFrame:
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    rates = mt5.copy_rates_range(symbol, TIMEFRAME_MAP[timeframe], start, end)

    if rates is None:
        raise RuntimeError(
            f"copy_rates_range returned None for {symbol} {timeframe} {year}: {mt5.last_error()}"
        )
    if len(rates) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True).dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    keep_cols = ["time", "open", "high", "low", "close", "tick_volume", "spread"]
    return df[keep_cols]


def save_csv(df: pd.DataFrame, timeframe: str, year: int, output_root: Path) -> Path:
    tf_dir = output_root / timeframe
    tf_dir.mkdir(parents=True, exist_ok=True)
    out_path = tf_dir / f"{timeframe}_{year}.csv"
    df.to_csv(out_path, index=False)
    return out_path


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root).expanduser().resolve()

    print(f"Connecting MT5 for {args.symbol} {args.timeframe} ...")
    initialize_mt5(args)
    try:
        print(f"Downloading {args.symbol} {args.timeframe} {args.year} ...")
        df = get_year_bars(args.symbol, args.timeframe, args.year)
        if df.empty:
            print(f"[WARN] No data for {args.symbol} {args.timeframe} {args.year}")
            return
        out_path = save_csv(df, args.timeframe, args.year, output_root)
        print(f"[OK] Saved: {out_path}")
    finally:
        mt5.shutdown()
        print("MT5 connection closed.")


if __name__ == "__main__":
    main()
