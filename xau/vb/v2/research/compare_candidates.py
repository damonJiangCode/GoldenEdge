from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


V2_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = V2_ROOT.parents[2]
sys.path.insert(0, str(V2_ROOT))

from engine import EngineConfig, TRAIN_YEARS, VolatilityBreakoutV2Engine  # noqa: E402


OUTPUT = Path(__file__).resolve().parent / "results"
CANDIDATES = {
    "00_corrected_intrabar": {"close_quality_min": 0.0, "atr_ratio_min": 1.0},
    "01_close_confirmation": {
        "signal_mode": "close",
        "close_quality_min": 0.0,
        "atr_ratio_min": 1.0,
    },
    "02_close_quality_65": {"close_quality_min": 0.65, "atr_ratio_min": 1.0},
    "03_atr_ratio_1_1": {"close_quality_min": 0.0, "atr_ratio_min": 1.1},
    "04_close_confirm_atr_1_1": {
        "signal_mode": "close",
        "close_quality_min": 0.0,
        "atr_ratio_min": 1.1,
    },
    "05_close_quality_atr_1_1": {"close_quality_min": 0.65, "atr_ratio_min": 1.1},
}
STRESS_SCENARIOS = {
    "base": {"slippage_ticks": 1.0, "commission_per_lot_round_turn": 5.0},
    "stress": {"slippage_ticks": 10.0, "commission_per_lot_round_turn": 10.0},
    "severe": {"slippage_ticks": 20.0, "commission_per_lot_round_turn": 20.0},
}


def stress_overview(trades: pd.DataFrame) -> dict:
    result = {}
    for name, settings in STRESS_SCENARIOS.items():
        extra_slippage = (
            2.0
            * (settings["slippage_ticks"] - 1.0)
            * 0.01
            * trades["lot_size"]
            * 100.0
        )
        extra_commission = (
            settings["commission_per_lot_round_turn"] - 5.0
        ) * trades["lot_size"]
        scenario_pnl = trades["net_pnl"] - extra_slippage - extra_commission
        annual = scenario_pnl.groupby(trades["year"]).sum() / 10_000.0 * 100.0
        result[name] = {
            "positive_years": int((annual > 0.0).sum()),
            "median_return_pct": float(annual.median()),
            "worst_return_pct": float(annual.min()),
            "simple_sum_return_pct": float(annual.sum()),
        }
    return result


def run_candidate(name: str, overrides: dict) -> dict:
    annual = []
    all_trades = []
    for year in TRAIN_YEARS:
        config = EngineConfig(
            h4_file=REPO_ROOT / "xau" / "marketdata" / "H4" / f"H4_{year}.csv",
            h1_file=REPO_ROOT / "xau" / "marketdata" / "H1" / f"H1_{year}.csv",
            **overrides,
        )
        engine = VolatilityBreakoutV2Engine(config)
        engine.load_data()
        report = engine.run()
        annual.append({"year": year, "trades": report["trades"], **report["performance"]})
        all_trades.extend(report["trade_details"])

    rows = pd.DataFrame(annual)
    trades = pd.DataFrame(all_trades)
    result = {
        "candidate": name,
        "overrides": overrides,
        "years": list(TRAIN_YEARS),
        "positive_years": int((rows["return_pct"] > 0.0).sum()),
        "average_return_pct": float(rows["return_pct"].mean()),
        "median_return_pct": float(rows["return_pct"].median()),
        "worst_return_pct": float(rows["return_pct"].min()),
        "average_max_drawdown_pct": float(rows["max_drawdown_pct"].mean()),
        "worst_max_drawdown_pct": float(rows["max_drawdown_pct"].max()),
        "average_profit_factor": float(rows["profit_factor"].mean()),
        "total_trades": int(rows["trades"].sum()),
        "pooled_average_r": float(trades["r_multiple"].mean()),
        "pooled_sum_r": float(trades["r_multiple"].sum()),
        "stress": stress_overview(trades),
        "annual": annual,
    }
    return result


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results = [run_candidate(name, overrides) for name, overrides in CANDIDATES.items()]
    (OUTPUT / "comparison.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    flat_rows = []
    for item in results:
        row = {
            key: value
            for key, value in item.items()
            if key not in ("annual", "stress", "overrides", "years")
        }
        for scenario, metrics in item["stress"].items():
            for key, value in metrics.items():
                row[f"{scenario}_{key}"] = value
        flat_rows.append(row)
    flat = pd.DataFrame(flat_rows)
    flat.to_csv(OUTPUT / "comparison.csv", index=False)
    print(
        flat[
            [
                "candidate",
                "positive_years",
                "median_return_pct",
                "worst_return_pct",
                "worst_max_drawdown_pct",
                "total_trades",
                "pooled_average_r",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
