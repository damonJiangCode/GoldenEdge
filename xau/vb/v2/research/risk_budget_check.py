from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


V2_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = V2_ROOT.parents[2]
sys.path.insert(0, str(V2_ROOT))

from engine import EngineConfig, TRAIN_YEARS, VolatilityBreakoutV2Engine  # noqa: E402


OUTPUT = Path(__file__).resolve().parent / "results" / "risk_budget_check.csv"
RISK_BUDGETS = (0.5, 1.0, 1.5)


def main() -> None:
    rows = []
    for risk_pct in RISK_BUDGETS:
        annual = []
        total_trades = 0
        skipped = 0
        for year in TRAIN_YEARS:
            engine = VolatilityBreakoutV2Engine(
                EngineConfig(
                    h4_file=REPO_ROOT / "xau" / "marketdata" / "H4" / f"H4_{year}.csv",
                    h1_file=REPO_ROOT / "xau" / "marketdata" / "H1" / f"H1_{year}.csv",
                    risk_per_trade_pct=risk_pct,
                )
            )
            engine.load_data()
            report = engine.run()
            annual.append(report["performance"])
            total_trades += report["trades"]
            skipped += report["reject_counts"].get("below_min_lot", 0)
        frame = pd.DataFrame(annual)
        rows.append(
            {
                "risk_per_trade_pct": risk_pct,
                "positive_years": int((frame["return_pct"] > 0.0).sum()),
                "median_return_pct": float(frame["return_pct"].median()),
                "worst_return_pct": float(frame["return_pct"].min()),
                "worst_max_drawdown_pct": float(frame["max_drawdown_pct"].max()),
                "total_trades": total_trades,
                "below_min_lot_rejects": skipped,
            }
        )
    result = pd.DataFrame(rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
