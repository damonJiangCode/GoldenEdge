from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EUR_DATA_DIR = PROJECT_ROOT / "data" / "historical" / "eur"
RESULT_DIR = PROJECT_ROOT / "data" / "backtest_results" / "eur"

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


class BareBacktestEngine:
    """Minimal backtest runtime without any strategy logic."""

    def __init__(self, config: EngineConfig) -> None:
        self.config = config
        self.df: pd.DataFrame | None = None

    def load_data(self) -> pd.DataFrame:
        df = pd.read_csv(self.config.input_file)

        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(
                f"Input CSV missing columns: {missing}. Required: {REQUIRED_COLUMNS}"
            )

        df["time"] = pd.to_datetime(df["time"], utc=True)
        df.sort_values("time", inplace=True)
        df.drop_duplicates(subset=["time"], inplace=True)
        df.reset_index(drop=True, inplace=True)

        if df.empty:
            raise ValueError("Input CSV has no rows after cleaning.")

        self.df = df
        return df

    def run(self) -> dict[str, Any]:
        if self.df is None:
            raise RuntimeError("Data not loaded. Call load_data() first.")

        # Base engine loop: iterate bars but intentionally do not trade.
        equity = self.config.initial_balance
        last_close = float(self.df.iloc[0]["close"])
        for _, bar in self.df.iterrows():
            last_close = float(bar["close"])

        report = {
            "engine": "bare_backtest_runtime",
            "input_file": str(self.config.input_file),
            "bars": int(len(self.df)),
            "time_start_utc": self.df.iloc[0]["time"].isoformat(),
            "time_end_utc": self.df.iloc[-1]["time"].isoformat(),
            "initial_balance": float(self.config.initial_balance),
            "final_balance": float(equity),
            "trades": 0,
            "last_close": last_close,
            "spread_mean": float(self.df["spread"].mean()),
            "spread_min": float(self.df["spread"].min()),
            "spread_max": float(self.df["spread"].max()),
        }
        return report

    def save_report(self, report: dict[str, Any]) -> Path:
        RESULT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = RESULT_DIR / "EUR_bare_engine_report.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return output_path


def resolve_input_file(cli_input: str | None) -> Path:
    if cli_input:
        path = Path(cli_input).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        return path

    candidates = sorted(EUR_DATA_DIR.glob("*.csv"))
    if not candidates:
        raise FileNotFoundError(
            f"No EUR CSV found in {EUR_DATA_DIR}. "
            "Please place your EURUSD M15 CSV there first."
        )
    return candidates[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run bare backtesting runtime for EURUSD M15 (no strategy, no trades)."
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Path to EURUSD M15 CSV. Defaults to first CSV in ai/data/historical/eur.",
    )
    parser.add_argument("--initial-balance", type=float, default=1000.0)
    parser.add_argument("--lot-size", type=float, default=0.01)
    parser.add_argument("--contract-size", type=int, default=100000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_file = resolve_input_file(args.input)

    config = EngineConfig(
        input_file=input_file,
        initial_balance=args.initial_balance,
        lot_size=args.lot_size,
        contract_size=args.contract_size,
    )

    engine = BareBacktestEngine(config)
    engine.load_data()
    report = engine.run()
    report_path = engine.save_report(report)

    print("Bare backtest runtime finished.")
    print(json.dumps(report, indent=2))
    print(f"Saved report: {report_path}")


if __name__ == "__main__":
    main()
