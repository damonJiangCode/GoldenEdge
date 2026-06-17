from pathlib import Path

import pandas as pd
import yfinance as yf


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_ROOT = PROJECT_ROOT / "data"
METADATA_PATH = DATA_ROOT / "symbols_metadata.csv"

REQUESTED_START = "2000-01-01"
REQUESTED_END = "2026-01-01"

SYMBOLS = {
    "equity": ["SPY", "QQQ", "IWM", "EFA"],
    "commodity": ["GLD", "SLV", "USO", "DBA"],
    "bond": ["TLT", "IEF", "SHY", "LQD"],
}

REQUIRED_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]


def ensure_directories() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    for asset_class in SYMBOLS:
        (DATA_ROOT / asset_class).mkdir(parents=True, exist_ok=True)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.reset_index()


def download_symbol(symbol: str, asset_class: str) -> dict:
    file_path = DATA_ROOT / asset_class / f"{symbol}.csv"
    metadata = {
        "symbol": symbol,
        "asset_class": asset_class,
        "requested_start": REQUESTED_START,
        "actual_start": "",
        "actual_end": "",
        "rows": 0,
        "status": "FAILED",
        "file_path": str(file_path),
    }

    print(f"Symbol: {symbol}")
    print(f"Requested start: {REQUESTED_START}")

    try:
        df = yf.download(
            symbol,
            start=REQUESTED_START,
            end=REQUESTED_END,
            auto_adjust=False,
            progress=False,
        )
        df = normalize_columns(df)

        if df.empty:
            metadata["status"] = "FAILED"
            print("Status: FAILED")
            print("Reason: empty data\n")
            return metadata

        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            metadata["status"] = "FAILED"
            print("Status: FAILED")
            print(f"Reason: missing columns {missing}\n")
            return metadata

        df = df[REQUIRED_COLUMNS].copy()
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").dropna(subset=["Date"]).reset_index(drop=True)

        if df.empty:
            metadata["status"] = "FAILED"
            print("Status: FAILED")
            print("Reason: empty data after cleanup\n")
            return metadata

        df.to_csv(file_path, index=False)

        actual_start = df["Date"].iloc[0].date().isoformat()
        actual_end = df["Date"].iloc[-1].date().isoformat()
        status = "OK" if actual_start <= REQUESTED_START else "OK, limited history"

        metadata.update(
            {
                "actual_start": actual_start,
                "actual_end": actual_end,
                "rows": len(df),
                "status": status,
            }
        )

        print(f"Actual start: {actual_start}")
        print(f"Actual end: {actual_end}")
        print(f"Rows: {len(df)}")
        print(f"Status: {status}\n")
        return metadata

    except Exception as exc:
        metadata["status"] = "FAILED"
        print("Status: FAILED")
        print(f"Reason: {exc}\n")
        return metadata


def main() -> None:
    ensure_directories()

    metadata_rows = []
    for asset_class, symbols in SYMBOLS.items():
        for symbol in symbols:
            metadata_rows.append(download_symbol(symbol, asset_class))

    metadata = pd.DataFrame(metadata_rows)
    metadata.to_csv(METADATA_PATH, index=False)

    print("Download summary:")
    print(metadata.to_string(index=False))
    print(f"\nMetadata saved to: {METADATA_PATH}")


if __name__ == "__main__":
    main()
