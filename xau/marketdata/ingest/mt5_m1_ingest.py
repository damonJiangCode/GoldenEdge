from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "xau" / "marketdata"
DEFAULT_START = "2026-01-01"
DEFAULT_END = "2026-06-01"
DEFAULT_TARGETS = ("M15", "M30", "H1", "H4")
REQUIRED_COLUMNS = (
    "time",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "spread",
)
RESAMPLE_RULES = {
    "M15": "15min",
    "M30": "30min",
    "H1": "1h",
    "H4": "4h",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download MT5 XAUUSD M1 bars and build higher timeframes."
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("run", "download", "resample"),
        default="run",
        help="run downloads M1 then resamples it (default: run).",
    )
    parser.add_argument("--symbol", default="XAUUSD", help="MT5 symbol name.")
    parser.add_argument(
        "--start",
        default=DEFAULT_START,
        help="Inclusive UTC start date/time (default: 2026-01-01).",
    )
    parser.add_argument(
        "--end",
        default=DEFAULT_END,
        help="Exclusive UTC end date/time (default: 2026-06-01).",
    )
    parser.add_argument(
        "--targets",
        nargs="+",
        choices=tuple(RESAMPLE_RULES),
        default=list(DEFAULT_TARGETS),
        help="Higher timeframes to build from M1.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Output root (default: xau/marketdata).",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="M1 CSV used by the resample command. Defaults to M1/M1_<year>.csv.",
    )
    parser.add_argument(
        "--terminal-path",
        default=os.getenv("MT5_TERMINAL_PATH"),
        help="Optional MT5 terminal executable path.",
    )
    parser.add_argument(
        "--login",
        type=int,
        default=int(os.environ["MT5_LOGIN"]) if os.getenv("MT5_LOGIN") else None,
        help="MT5 account login. Can also use MT5_LOGIN.",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("MT5_PASSWORD"),
        help="MT5 account password. Prefer MT5_PASSWORD.",
    )
    parser.add_argument(
        "--server",
        default=os.getenv("MT5_SERVER"),
        help="MT5 server name. Can also use MT5_SERVER.",
    )
    parser.add_argument(
        "--merge-existing",
        action="store_true",
        help="Merge downloaded M1 bars into an existing annual M1 CSV.",
    )
    return parser.parse_args()


def parse_utc(value: str) -> datetime:
    parsed = pd.Timestamp(value)
    if parsed.tzinfo is None:
        parsed = parsed.tz_localize("UTC")
    else:
        parsed = parsed.tz_convert("UTC")
    return parsed.to_pydatetime()


def validate_range(start: datetime, end: datetime) -> None:
    if start >= end:
        raise ValueError(f"--start must be earlier than --end: {start} >= {end}")
    if start.year != (end - pd.Timedelta(seconds=1)).year:
        raise ValueError(
            "One run must stay within one calendar year so annual filenames remain clear."
        )


def import_mt5() -> Any:
    try:
        import MetaTrader5 as mt5  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "MetaTrader5 is not installed. Run the download command on a Windows "
            "machine with an MT5 terminal and install: pip install MetaTrader5 pandas"
        ) from exc
    return mt5


def initialize_mt5(mt5: Any, args: argparse.Namespace) -> None:
    initialized = (
        mt5.initialize(path=args.terminal_path)
        if args.terminal_path
        else mt5.initialize()
    )
    if not initialized:
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    supplied = (args.login is not None, bool(args.password), bool(args.server))
    if any(supplied) and not all(supplied):
        raise ValueError(
            "MT5 login requires --login, --password, and --server together."
        )
    if all(supplied) and not mt5.login(
        args.login, password=args.password, server=args.server
    ):
        raise RuntimeError(f"MT5 login failed: {mt5.last_error()}")


def resolve_symbol(mt5: Any, requested: str) -> str:
    if mt5.symbol_info(requested) is not None:
        resolved = requested
    else:
        matches = mt5.symbols_get(f"*{requested}*") or []
        exactish = [item.name for item in matches if requested in item.name]
        if len(exactish) != 1:
            raise RuntimeError(
                f"Cannot resolve symbol {requested!r}. Matching symbols: {exactish[:20]}"
            )
        resolved = exactish[0]

    if not mt5.symbol_select(resolved, True):
        raise RuntimeError(f"Cannot select MT5 symbol {resolved}: {mt5.last_error()}")
    return resolved


def month_boundaries(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    boundaries = list(pd.date_range(start=start, end=end, freq="MS", inclusive="left"))
    points = [pd.Timestamp(start), *boundaries, pd.Timestamp(end)]
    points = sorted(set(points))
    return [
        (points[index].to_pydatetime(), points[index + 1].to_pydatetime())
        for index in range(len(points) - 1)
    ]


def normalize_bars(df: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Market data is missing columns: {missing}")

    clean = df.loc[:, REQUIRED_COLUMNS].copy()
    if pd.api.types.is_numeric_dtype(clean["time"]):
        # MT5 copy_rates_* returns Unix timestamps in seconds. Without unit="s",
        # pandas interprets integers as nanoseconds and turns 2026 into 1970.
        clean["time"] = pd.to_datetime(
            clean["time"], unit="s", utc=True, errors="coerce"
        )
    else:
        clean["time"] = pd.to_datetime(clean["time"], utc=True, errors="coerce")
    for column in REQUIRED_COLUMNS[1:]:
        clean[column] = pd.to_numeric(clean[column], errors="coerce")
    clean.dropna(subset=["time", "open", "high", "low", "close"], inplace=True)
    clean.sort_values("time", inplace=True)
    clean.drop_duplicates(subset=["time"], keep="last", inplace=True)
    clean.reset_index(drop=True, inplace=True)
    return clean


def download_m1(mt5: Any, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for chunk_start, chunk_end in month_boundaries(start, end):
        print(f"Downloading M1: {chunk_start:%Y-%m-%d} -> {chunk_end:%Y-%m-%d}")
        rates = mt5.copy_rates_range(
            symbol, mt5.TIMEFRAME_M1, chunk_start, chunk_end
        )
        if rates is None:
            raise RuntimeError(
                f"copy_rates_range failed for {chunk_start} -> {chunk_end}: "
                f"{mt5.last_error()}"
            )
        if len(rates):
            frames.append(pd.DataFrame(rates))

    if not frames:
        raise RuntimeError(f"MT5 returned no M1 bars for {symbol} in the requested range.")
    downloaded = normalize_bars(pd.concat(frames, ignore_index=True))
    filtered = filter_range(downloaded, start, end)
    if filtered.empty:
        raise RuntimeError(
            "MT5 returned bars, but none were inside the requested UTC range. "
            f"Requested: {start.isoformat()} -> {end.isoformat()}; "
            f"returned: {downloaded['time'].iloc[0].isoformat()} -> "
            f"{downloaded['time'].iloc[-1].isoformat()}."
        )
    return filtered


def load_m1(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"M1 input does not exist: {path}")
    return normalize_bars(pd.read_csv(path))


def merge_bars(existing: pd.DataFrame, incoming: pd.DataFrame) -> pd.DataFrame:
    return normalize_bars(pd.concat([existing, incoming], ignore_index=True))


def filter_range(df: pd.DataFrame, start: datetime, end: datetime) -> pd.DataFrame:
    clean = normalize_bars(df)
    return clean.loc[(clean["time"] >= start) & (clean["time"] < end)].reset_index(
        drop=True
    )


def resample_m1(m1: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    if timeframe not in RESAMPLE_RULES:
        raise ValueError(f"Unsupported target timeframe: {timeframe}")

    indexed = normalize_bars(m1).set_index("time")
    result = (
        indexed.resample(RESAMPLE_RULES[timeframe])
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
        .reset_index()
    )
    result["tick_volume"] = result["tick_volume"].round().astype("int64")
    result["spread"] = result["spread"].round().astype("int64")
    return result.loc[:, REQUIRED_COLUMNS]


def annual_path(output_root: Path, timeframe: str, year: int) -> Path:
    return output_root / timeframe / f"{timeframe}_{year}.csv"


def save_bars(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    output = normalize_bars(df)
    if output.empty:
        raise ValueError(f"Refusing to save an empty market data file: {path}")
    output["time"] = output["time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    output.to_csv(path, index=False)
    print(
        f"Saved {len(output):,} bars: {path} "
        f"({output['time'].iloc[0]} -> {output['time'].iloc[-1]})"
    )


def main() -> None:
    args = parse_args()
    start = parse_utc(args.start)
    end = parse_utc(args.end)
    validate_range(start, end)
    output_root = args.output_root.expanduser().resolve()
    year = start.year
    m1_path = (
        args.input.expanduser().resolve()
        if args.input
        else annual_path(output_root, "M1", year)
    )

    m1: pd.DataFrame
    if args.command in ("run", "download"):
        mt5 = import_mt5()
        initialize_mt5(mt5, args)
        try:
            symbol = resolve_symbol(mt5, args.symbol)
            print(f"Connected to MT5; using symbol {symbol}.")
            m1 = download_m1(mt5, symbol, start, end)
        finally:
            mt5.shutdown()

        if args.merge_existing and m1_path.exists():
            m1 = merge_bars(load_m1(m1_path), m1)
        save_bars(m1, m1_path)
    else:
        m1 = filter_range(load_m1(m1_path), start, end)

    if args.command in ("run", "resample"):
        for timeframe in args.targets:
            save_bars(
                resample_m1(m1, timeframe),
                annual_path(output_root, timeframe, year),
            )


if __name__ == "__main__":
    main()
