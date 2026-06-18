from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf


ALPHA_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = ALPHA_ROOT / "data"
METADATA_PATH = DATA_ROOT / "symbols_metadata.csv"

REQUESTED_START = "2000-01-01"
REQUESTED_END_INCLUSIVE = "2025-12-31"
YFINANCE_END_EXCLUSIVE = "2026-01-01"
DOWNLOAD_ATTEMPTS = 3

UNIVERSE = {
    "equity": {
        "Core": ["SPY", "QQQ", "IWM", "EFA", "EEM", "VTI", "DIA"],
        "Sector": ["XLK", "XLF", "XLV", "XLY", "XLP", "XLE", "XLI", "XLU", "XLB", "XLRE"],
        "StyleFactor": ["IWF", "IWD", "MTUM", "QUAL", "USMV", "VLUE"],
        "RealEstate": ["VNQ"],
    },
    "commodity": {
        "Commodity": ["GLD", "SLV", "USO", "DBA"],
    },
    "bond": {
        "Bond": ["TLT", "IEF", "SHY", "LQD"],
    },
}

REQUIRED_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
PRICE_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
METADATA_COLUMNS = ["symbol", "asset_class", "category", "actual_start", "actual_end", "rows", "status"]


def iter_universe():
    for asset_class, categories in UNIVERSE.items():
        for category, symbols in categories.items():
            for symbol in symbols:
                yield symbol, asset_class, category


def ensure_directories() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    for asset_class in UNIVERSE:
        (DATA_ROOT / asset_class).mkdir(parents=True, exist_ok=True)


def normalize_download(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    if "Datetime" in df.columns and "Date" not in df.columns:
        df = df.rename(columns={"Datetime": "Date"})
    return df


def validate_frame(df: pd.DataFrame, require_complete_end: bool) -> tuple[Optional[pd.DataFrame], str]:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        return None, f"missing columns: {missing}"

    clean = df[REQUIRED_COLUMNS].copy()
    clean["Date"] = pd.to_datetime(clean["Date"], errors="coerce", utc=True).dt.tz_localize(None)
    for column in PRICE_COLUMNS:
        clean[column] = pd.to_numeric(clean[column], errors="coerce")

    if clean.empty:
        return None, "empty data"
    if clean["Date"].isna().any():
        return None, "invalid Date values"
    if clean[PRICE_COLUMNS].isna().any().any():
        bad_columns = clean[PRICE_COLUMNS].columns[clean[PRICE_COLUMNS].isna().any()].tolist()
        return None, f"null numeric values in: {bad_columns}"
    if clean["Date"].duplicated().any():
        return None, "duplicate dates"
    if not clean["Date"].is_monotonic_increasing:
        return None, "dates are not sorted ascending"

    requested_start = pd.Timestamp(REQUESTED_START)
    requested_end = pd.Timestamp(REQUESTED_END_INCLUSIVE)
    if clean["Date"].min() < requested_start:
        clean = clean.loc[clean["Date"] >= requested_start].copy()
    if clean["Date"].max() > requested_end:
        clean = clean.loc[clean["Date"] <= requested_end].copy()
    if clean.empty:
        return None, "no rows inside requested date range"
    if require_complete_end and clean["Date"].max() < requested_end:
        return None, f"data ends at {clean['Date'].max().date()}, expected {REQUESTED_END_INCLUSIVE}"

    clean["Date"] = clean["Date"].dt.strftime("%Y-%m-%d")
    return clean.reset_index(drop=True), ""


def read_complete_existing(file_path: Path) -> tuple[Optional[pd.DataFrame], str]:
    if not file_path.exists():
        return None, "file missing"
    try:
        existing = pd.read_csv(file_path)
    except Exception as exc:
        return None, f"cannot read existing file: {exc}"
    return validate_frame(existing, require_complete_end=True)


def fetch_symbol(symbol: str) -> tuple[Optional[pd.DataFrame], str]:
    last_error = "download failed"
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            raw = yf.download(
                symbol,
                start=REQUESTED_START,
                end=YFINANCE_END_EXCLUSIVE,
                interval="1d",
                auto_adjust=False,
                actions=False,
                progress=False,
                threads=False,
                timeout=30,
            )
            clean, error = validate_frame(normalize_download(raw), require_complete_end=True)
            if clean is not None:
                return clean, ""
            last_error = error
        except Exception as exc:
            last_error = str(exc)

        if attempt < DOWNLOAD_ATTEMPTS:
            time.sleep(attempt * 2)
    return None, last_error


def metadata_row(
    symbol: str,
    asset_class: str,
    category: str,
    df: Optional[pd.DataFrame],
    status: str,
) -> dict:
    if df is None or df.empty:
        actual_start = ""
        actual_end = ""
        rows = 0
    else:
        actual_start = str(df["Date"].iloc[0])
        actual_end = str(df["Date"].iloc[-1])
        rows = len(df)
    return {
        "symbol": symbol,
        "asset_class": asset_class,
        "category": category,
        "actual_start": actual_start,
        "actual_end": actual_end,
        "rows": rows,
        "status": status,
    }


def process_symbol(symbol: str, asset_class: str, category: str) -> tuple[dict, str]:
    file_path = DATA_ROOT / asset_class / f"{symbol}.csv"
    existing, existing_error = read_complete_existing(file_path)
    if existing is not None:
        print(f"[SKIP]     {symbol:<5} complete local data: {existing['Date'].iloc[0]} to {existing['Date'].iloc[-1]}")
        return metadata_row(symbol, asset_class, category, existing, "OK"), "skipped"

    reason = existing_error if file_path.exists() else "file missing"
    print(f"[DOWNLOAD] {symbol:<5} {reason}")
    downloaded, download_error = fetch_symbol(symbol)
    if downloaded is None:
        print(f"[FAILED]   {symbol:<5} {download_error}")
        return metadata_row(symbol, asset_class, category, None, f"FAILED: {download_error}"), "failed"

    temporary_path = file_path.with_suffix(".csv.tmp")
    downloaded.to_csv(temporary_path, index=False)
    temporary_path.replace(file_path)
    print(
        f"[SAVED]    {symbol:<5} {downloaded['Date'].iloc[0]} to "
        f"{downloaded['Date'].iloc[-1]} ({len(downloaded)} rows)"
    )
    return metadata_row(symbol, asset_class, category, downloaded, "OK"), "downloaded"


def main() -> None:
    ensure_directories()
    metadata_rows = []
    action_counts = {"skipped": 0, "downloaded": 0, "failed": 0}

    for symbol, asset_class, category in iter_universe():
        try:
            row, action = process_symbol(symbol, asset_class, category)
        except Exception as exc:
            row = metadata_row(symbol, asset_class, category, None, f"FAILED: {exc}")
            action = "failed"
            print(f"[FAILED]   {symbol:<5} unexpected error: {exc}")
        metadata_rows.append(row)
        action_counts[action] += 1

    metadata = pd.DataFrame(metadata_rows, columns=METADATA_COLUMNS)
    metadata.to_csv(METADATA_PATH, index=False)

    print("\nDownload summary")
    print("=" * 72)
    print(f"Requested range : {REQUESTED_START} to {REQUESTED_END_INCLUSIVE}")
    print(f"Universe size   : {len(metadata)}")
    print(f"Existing skipped: {action_counts['skipped']}")
    print(f"Downloaded      : {action_counts['downloaded']}")
    print(f"Failed          : {action_counts['failed']}")
    print("\nBy asset class and status:")
    print(metadata.groupby(["asset_class", "status"]).size().rename("symbols").to_string())
    print(f"\nMetadata saved to: {METADATA_PATH}")

    failures = metadata.loc[metadata["status"].str.startswith("FAILED"), ["symbol", "status"]]
    if not failures.empty:
        print("\nFailures:")
        print(failures.to_string(index=False))


if __name__ == "__main__":
    main()
