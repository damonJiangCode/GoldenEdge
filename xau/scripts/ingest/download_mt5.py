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
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "data" / "historical"

TIMEFRAME_MAP = {
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download one year of XAUUSD historical data from MT5, and refresh "
            "one merged summary CSV per timeframe."
        )
    )
    parser.add_argument(
        "--timeframe", required=True, choices=sorted(TIMEFRAME_MAP.keys())
    )
    parser.add_argument("--year", type=int, required=True, help="Single year, e.g. 2017.")
    parser.add_argument(
        "--aggregate-from-year",
        type=int,
        default=2017,
        help="Summary CSV start year (default: 2017).",
    )
    parser.add_argument(
        "--aggregate-to-year",
        type=int,
        default=2025,
        help="Summary CSV end year (default: 2025).",
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Output root directory (default: xau/data/historical).",
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
    if args.terminal_path:
        ok = mt5.initialize(path=args.terminal_path)
    else:
        ok = mt5.initialize()
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

    # Keep compatibility with the existing engine CSV schema.
    keep_cols = ["time", "open", "high", "low", "close", "tick_volume", "spread"]
    return df[keep_cols]


def save_year_file(
    df: pd.DataFrame, timeframe: str, year: int, output_root: Path
) -> Path:
    tf_dir = output_root / timeframe
    tf_dir.mkdir(parents=True, exist_ok=True)
    out_path = tf_dir / f"{timeframe}_{year}.csv"
    df.to_csv(out_path, index=False)
    return out_path


def build_aggregate_file(
    timeframe: str, aggregate_from_year: int, aggregate_to_year: int, output_root: Path
) -> Path | None:
    tf_dir = output_root / timeframe
    frames: list[pd.DataFrame] = []

    for year in range(aggregate_from_year, aggregate_to_year + 1):
        year_path = tf_dir / f"{timeframe}_{year}.csv"
        if not year_path.exists():
            continue
        frames.append(pd.read_csv(year_path))

    if not frames:
        return None

    merged = pd.concat(frames, ignore_index=True)
    merged["time"] = pd.to_datetime(merged["time"], utc=True, errors="coerce")
    merged.dropna(subset=["time"], inplace=True)
    merged.sort_values("time", inplace=True)
    merged.drop_duplicates(subset=["time"], inplace=True)
    merged["time"] = merged["time"].dt.strftime("%Y-%m-%d %H:%M:%S")

    out_path = tf_dir / f"{timeframe}_{aggregate_from_year}_{aggregate_to_year}.csv"
    merged.to_csv(out_path, index=False)
    return out_path


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root).expanduser().resolve()
    year = args.year

    print(f"Connecting MT5 for {args.symbol} {args.timeframe} ...")
    initialize_mt5(args)
    try:
        print(f"Downloading {args.symbol} {args.timeframe} {year} ...")
        year_df = get_year_bars(args.symbol, args.timeframe, year)
        if year_df.empty:
            print(f"[WARN] No data for {args.symbol} {args.timeframe} {year}")
            return
        out_path = save_year_file(year_df, args.timeframe, year, output_root)
        print(f"[OK] Saved: {out_path}")

        agg_path = build_aggregate_file(
            timeframe=args.timeframe,
            aggregate_from_year=args.aggregate_from_year,
            aggregate_to_year=args.aggregate_to_year,
            output_root=output_root,
        )
        if agg_path:
            print(f"[OK] Saved summary: {agg_path}")
        else:
            print(
                "[WARN] Summary not created (no yearly files found in summary range)."
            )
    finally:
        mt5.shutdown()
        print("MT5 connection closed.")


if __name__ == "__main__":
    main()
