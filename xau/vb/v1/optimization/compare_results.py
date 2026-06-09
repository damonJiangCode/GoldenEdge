from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

OUTPUT_ROOT = Path(__file__).resolve().parent / "results"

VARIANTS = [
    "00_baseline_current_v1_default",
    "01_close_breakout_confirm",
    "02_candle_close_quality",
    "03_adx20_rising",
    "04_atr_ratio_1_1",
    "05_overextension_filter",
    "06_early_failure_exit",
    "07_candle_quality_adx20_rising",
]


def summarize_ex_2025(summary: dict) -> dict:
    rows = [row for row in summary["rows"] if row["year"] != "2025"]

    def avg(key: str) -> float:
        return sum(float(row[key]) for row in rows) / len(rows)

    return {
        "years": len(rows),
        "avg_return_pct": avg("return_pct"),
        "avg_profit_factor": avg("profit_factor"),
        "avg_max_drawdown_pct": avg("max_drawdown_pct"),
        "positive_years": sum(1 for row in rows if row["return_pct"] > 0.0),
        "avg_trades": avg("trades"),
        "avg_win_rate": avg("win_rate"),
        "total_early_exits": sum(int(row.get("early_exit_count", 0)) for row in rows),
        "worst_year": min(rows, key=lambda row: row["return_pct"]),
        "best_year": max(rows, key=lambda row: row["return_pct"]),
        "experiment": {
            **summary["experiment"],
            "name": f"{summary['experiment']['name']}_ex_2025",
        },
    }


def flatten(item: dict) -> dict:
    return {
        "name": item["experiment"]["name"],
        "years": item["years"],
        "avg_return_pct": item["avg_return_pct"],
        "avg_profit_factor": item["avg_profit_factor"],
        "avg_max_drawdown_pct": item["avg_max_drawdown_pct"],
        "positive_years": item["positive_years"],
        "avg_trades": item["avg_trades"],
        "avg_win_rate": item["avg_win_rate"],
        "worst_year": f"{item['worst_year']['year']}:{item['worst_year']['return_pct']:.2f}",
        "best_year": f"{item['best_year']['year']}:{item['best_year']['return_pct']:.2f}",
    }


def main() -> None:
    summaries = []
    for variant in VARIANTS:
        summary_path = OUTPUT_ROOT / variant / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summaries.append({key: value for key, value in summary.items() if key != "rows"})
        summaries.append(summarize_ex_2025(summary))

    (OUTPUT_ROOT / "comparison_summary.json").write_text(
        json.dumps(summaries, indent=2),
        encoding="utf-8",
    )
    pd.DataFrame([flatten(item) for item in summaries]).to_csv(
        OUTPUT_ROOT / "comparison_summary.csv",
        index=False,
    )
    print(OUTPUT_ROOT / "comparison_summary.csv")


if __name__ == "__main__":
    main()
