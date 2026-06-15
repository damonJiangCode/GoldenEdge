from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


V2_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = V2_ROOT.parents[2]
sys.path.insert(0, str(V2_ROOT))

from engine import EngineConfig, TRAIN_YEARS, VolatilityBreakoutV2Engine  # noqa: E402


OUTPUT = Path(__file__).resolve().parent / "results" / "parameter_neighborhood.csv"
CLOSE_QUALITY_VALUES = (0.60, 0.65, 0.70)
ATR_RATIO_VALUES = (1.05, 1.10, 1.15)


def main() -> None:
    rows = []
    for close_quality in CLOSE_QUALITY_VALUES:
        for atr_ratio in ATR_RATIO_VALUES:
            annual = []
            for year in TRAIN_YEARS:
                engine = VolatilityBreakoutV2Engine(
                    EngineConfig(
                        h4_file=REPO_ROOT / "xau" / "marketdata" / "H4" / f"H4_{year}.csv",
                        h1_file=REPO_ROOT / "xau" / "marketdata" / "H1" / f"H1_{year}.csv",
                        close_quality_min=close_quality,
                        atr_ratio_min=atr_ratio,
                    )
                )
                engine.load_data()
                report = engine.run()
                annual.append(report["performance"]["return_pct"])
            rows.append(
                {
                    "close_quality_min": close_quality,
                    "atr_ratio_min": atr_ratio,
                    "positive_years": sum(value > 0.0 for value in annual),
                    "average_return_pct": sum(annual) / len(annual),
                    "median_return_pct": float(pd.Series(annual).median()),
                    "worst_return_pct": min(annual),
                    "best_return_pct": max(annual),
                }
            )
    result = pd.DataFrame(rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
