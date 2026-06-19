from __future__ import annotations

import warnings
from pathlib import Path
from typing import Optional

import pandas as pd


REQUIRED_PRICE_COLUMNS = ["Date", "Adj Close"]


def load_symbol(path: Path) -> Optional[pd.DataFrame]:
    symbol = path.stem
    try:
        raw = pd.read_csv(path)
    except Exception as exc:
        warnings.warn(f"{symbol}: failed to read {path}: {exc}")
        return None

    missing = [column for column in REQUIRED_PRICE_COLUMNS if column not in raw.columns]
    if missing:
        warnings.warn(f"{symbol}: missing columns {missing}, skipped")
        return None

    frame = raw[REQUIRED_PRICE_COLUMNS].copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame[symbol] = pd.to_numeric(frame["Adj Close"], errors="coerce")
    frame = frame.dropna(subset=["Date", symbol]).sort_values("Date")
    frame = frame.drop_duplicates(subset=["Date"], keep="last").set_index("Date")
    if frame.empty:
        warnings.warn(f"{symbol}: no valid rows, skipped")
        return None
    return frame[[symbol]]


def load_directory(directory: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    paths = sorted(directory.glob("*.csv"))
    if not paths:
        raise RuntimeError(f"No CSV files found in {directory}")

    frames = []
    coverage_rows = []
    for path in paths:
        frame = load_symbol(path)
        if frame is None:
            continue
        frames.append(frame)
        coverage_rows.append(
            {
                "symbol": path.stem,
                "actual_start": frame.index.min(),
                "actual_end": frame.index.max(),
                "rows": len(frame),
            }
        )
    if len(frames) != len(paths):
        raise RuntimeError(f"Expected {len(paths)} valid files in {directory}, loaded {len(frames)}.")

    prices = pd.concat(frames, axis=1).sort_index().dropna(how="any")
    coverage = pd.DataFrame(coverage_rows).sort_values("symbol").reset_index(drop=True)
    return prices, coverage


def load_mixed_asset_prices(
    data_root: Path,
    symbols: list[str],
    asset_classes: list[str],
) -> pd.DataFrame:
    files_by_symbol = {}
    for asset_class in asset_classes:
        directory = data_root / asset_class
        if not directory.exists():
            warnings.warn(f"Missing asset class directory: {directory}")
            continue
        for path in directory.glob("*.csv"):
            if path.stem in symbols:
                files_by_symbol[path.stem] = path

    missing = [symbol for symbol in symbols if symbol not in files_by_symbol]
    if missing:
        raise RuntimeError(f"Missing mixed-asset symbols: {missing}")

    frames = []
    for symbol in symbols:
        frame = load_symbol(files_by_symbol[symbol])
        if frame is None:
            raise RuntimeError(f"Failed to load required symbol: {symbol}")
        frames.append(frame)
    return pd.concat(frames, axis=1).sort_index().dropna(how="any")[symbols]
