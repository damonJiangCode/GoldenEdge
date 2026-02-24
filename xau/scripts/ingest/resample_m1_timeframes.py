from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "historical" / "M1"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "data" / "historical"

SUPPORTED_TIMEFRAMES = {
    "M15": "15min",
    "M30": "30min",
    "H1": "1h",
    "H4": "4h",
}

REQUIRED_COLUMNS = [
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
            "Build higher-timeframe bars from M1 CSV files. "
            "Output schema: time,open,high,low,close,tick_volume,spread."
        )
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help="Input directory containing M1_YYYY.csv files.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Output root directory (writes into M15/M30/H1/H4 subfolders).",
    )
    parser.add_argument(
        "--timeframes",
        nargs="+",
        default=["M15", "M30", "H1", "H4"],
        choices=sorted(SUPPORTED_TIMEFRAMES.keys()),
        help="Target timeframes to generate.",
    )
    parser.add_argument(
        "--years",
        nargs="*",
        type=int,
        default=None,
        help="Optional year list, e.g. --years 2019 2020 2021. Default: all files in input-dir.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files.",
    )
    return parser.parse_args()


def load_m1_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name} missing columns: {missing}")

    out = df[REQUIRED_COLUMNS].copy()
    out["time"] = pd.to_datetime(out["time"], errors="coerce")
    out.dropna(subset=["time"], inplace=True)

    numeric_cols = ["open", "high", "low", "close", "tick_volume", "spread"]
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out.dropna(subset=["open", "high", "low", "close", "spread"], inplace=True)

    out.sort_values("time", inplace=True)
    out.drop_duplicates(subset=["time"], inplace=True)
    out.reset_index(drop=True, inplace=True)
    return out


def resample_from_m1(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    base = df.set_index("time")
    ohlcv = base.resample(rule, label="left", closed="left").agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "tick_volume": "sum",
            "spread": "mean",
        }
    )
    ohlcv.dropna(subset=["open", "high", "low", "close"], inplace=True)
    ohlcv["tick_volume"] = ohlcv["tick_volume"].fillna(0).astype(int)
    ohlcv["spread"] = ohlcv["spread"].round().astype(int)
    ohlcv.reset_index(inplace=True)
    ohlcv["time"] = ohlcv["time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return ohlcv[REQUIRED_COLUMNS]


def extract_year(path: Path) -> int:
    stem = path.stem  # M1_2015
    try:
        return int(stem.split("_")[-1])
    except Exception as exc:
        raise ValueError(f"Unexpected filename format: {path.name}") from exc


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve()

    files = sorted(input_dir.glob("M1_*.csv"))
    if args.years:
        year_set = set(args.years)
        files = [f for f in files if extract_year(f) in year_set]

    if not files:
        raise SystemExit(f"No matching M1 files found in {input_dir}")

    print(f"[INFO] Input dir: {input_dir}")
    print(f"[INFO] Output root: {output_root}")
    print(f"[INFO] M1 files: {len(files)}")
    print(f"[INFO] Target TFs: {args.timeframes}")

    ok = 0
    for src in files:
        year = extract_year(src)
        m1_df = load_m1_csv(src)
        if m1_df.empty:
            print(f"[WARN] Skip empty source: {src.name}")
            continue

        for tf in args.timeframes:
            out_dir = output_root / tf
            out_dir.mkdir(parents=True, exist_ok=True)
            dst = out_dir / f"{tf}_{year}.csv"

            if dst.exists() and not args.overwrite:
                print(f"[SKIP] Exists: {dst}")
                continue

            out_df = resample_from_m1(m1_df, SUPPORTED_TIMEFRAMES[tf])
            out_df.to_csv(dst, index=False)
            print(
                f"[OK] {src.name} -> {dst.name} rows={len(out_df)} "
                f"range={out_df.iloc[0]['time']} -> {out_df.iloc[-1]['time']}"
            )
            ok += 1

    print(f"[DONE] Generated {ok} file(s).")


if __name__ == "__main__":
    main()
