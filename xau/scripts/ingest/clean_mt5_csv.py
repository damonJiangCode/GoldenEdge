from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "historical" / "M1"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "historical" / "M1_clean"

REQUIRED_OUTPUT_COLUMNS = [
    "time",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "spread",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Clean MT5 CSV exports into engine-ready format: "
            "time,open,high,low,close,tick_volume,spread."
        )
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help="Directory containing source CSV files.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory to write cleaned CSV files.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Write cleaned files back into --input-dir.",
    )
    return parser.parse_args()


def read_mt5_csv(path: Path) -> pd.DataFrame:
    # MT5 exports are usually tab-delimited; fallback to comma.
    try:
        df = pd.read_csv(path, sep="\t", engine="python")
        if df.shape[1] == 1:
            df = pd.read_csv(path)
    except Exception:
        df = pd.read_csv(path)
    return df


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = {str(c).strip(): c for c in df.columns}
    mt5_date = cols.get("<DATE>")
    mt5_time = cols.get("<TIME>")
    mt5_open = cols.get("<OPEN>")
    mt5_high = cols.get("<HIGH>")
    mt5_low = cols.get("<LOW>")
    mt5_close = cols.get("<CLOSE>")
    mt5_tick_volume = cols.get("<TICKVOL>")
    mt5_spread = cols.get("<SPREAD>")

    if all(
        x is not None
        for x in (
            mt5_date,
            mt5_time,
            mt5_open,
            mt5_high,
            mt5_low,
            mt5_close,
            mt5_tick_volume,
            mt5_spread,
        )
    ):
        out = pd.DataFrame(
            {
                "time": (
                    df[mt5_date].astype(str).str.strip()
                    + " "
                    + df[mt5_time].astype(str).str.strip()
                ),
                "open": df[mt5_open],
                "high": df[mt5_high],
                "low": df[mt5_low],
                "close": df[mt5_close],
                "tick_volume": df[mt5_tick_volume],
                "spread": df[mt5_spread],
            }
        )
    else:
        lowered = {str(c).strip().lower(): c for c in df.columns}
        required = ["time", "open", "high", "low", "close", "tick_volume", "spread"]
        missing = [c for c in required if c not in lowered]
        if missing:
            raise ValueError(f"Missing expected columns: {missing}")
        out = pd.DataFrame({c: df[lowered[c]] for c in required})

    out["time"] = (
        out["time"]
        .astype(str)
        .str.replace(".", "-", regex=False)
        .str.replace("/", "-", regex=False)
        .str.strip()
    )
    dt = pd.to_datetime(out["time"], errors="coerce")
    out = out.loc[dt.notna()].copy()
    out["time"] = dt.loc[dt.notna()].dt.strftime("%Y-%m-%d %H:%M:%S")

    for col in ["open", "high", "low", "close", "tick_volume", "spread"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out.dropna(subset=["time", "open", "high", "low", "close", "spread"], inplace=True)
    out["tick_volume"] = out["tick_volume"].fillna(0).astype(int)
    out["spread"] = out["spread"].round().astype(int)

    out.sort_values("time", inplace=True)
    out.drop_duplicates(subset=["time"], inplace=True)
    out.reset_index(drop=True, inplace=True)
    return out[REQUIRED_OUTPUT_COLUMNS]


def clean_file(src: Path, dst: Path) -> tuple[int, str, str]:
    raw_df = read_mt5_csv(src)
    clean_df = normalize_columns(raw_df)
    dst.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(dst, index=False)
    return len(clean_df), clean_df.iloc[0]["time"], clean_df.iloc[-1]["time"]


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = input_dir if args.in_place else Path(args.output_dir).expanduser().resolve()

    files = sorted(input_dir.glob("*.csv"))
    if not files:
        raise SystemExit(f"No CSV files found under: {input_dir}")

    print(f"[INFO] Input:  {input_dir}")
    print(f"[INFO] Output: {output_dir}")
    print(f"[INFO] Files:  {len(files)}")

    ok_count = 0
    for src in files:
        dst = output_dir / src.name
        try:
            rows, t0, t1 = clean_file(src, dst)
            ok_count += 1
            print(f"[OK] {src.name}: rows={rows}, range={t0} -> {t1}")
        except Exception as exc:
            print(f"[ERR] {src.name}: {exc}")

    print(f"[DONE] cleaned {ok_count}/{len(files)} files.")


if __name__ == "__main__":
    main()
