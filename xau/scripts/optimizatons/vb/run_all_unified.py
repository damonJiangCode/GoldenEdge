from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from common import (
    DATA_ROOT,
    VBExperimentEngine,
    default_config,
    report_to_unified_rows,
    resolve_input_files,
    summarize_reports,
    write_summary,
    write_unified_trades,
)

SCRIPT_DIR = Path(__file__).resolve().parent


class BaselineCurrentV1Engine(VBExperimentEngine):
    experiment_name = "00_baseline_current_v1_default"
    experiment_description = "Current VB v1 default parameters without extra quality filters."


def load_class(script_name: str, class_name: str) -> type[VBExperimentEngine]:
    module_path = SCRIPT_DIR / script_name
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)


VARIANTS: list[dict] = [
    {
        "output_name": "00_baseline_current_v1_default",
        "engine_cls": BaselineCurrentV1Engine,
        "config_overrides": {},
    },
    {
        "output_name": "01_close_breakout_confirm",
        "engine_cls": load_class("01_close_breakout_confirm.py", "CloseBreakoutConfirmEngine"),
        "config_overrides": {},
    },
    {
        "output_name": "02_candle_close_quality",
        "engine_cls": load_class("02_candle_close_quality.py", "CandleCloseQualityEngine"),
        "config_overrides": {},
    },
    {
        "output_name": "03_adx20_rising",
        "engine_cls": load_class("03_adx20_rising.py", "Adx20RisingEngine"),
        "config_overrides": {"h1_adx_min": 20.0},
    },
    {
        "output_name": "04_atr_ratio_1_1",
        "engine_cls": load_class("04_atr_ratio_1_1.py", "AtrRatio11Engine"),
        "config_overrides": {"atr_ratio_min": 1.1},
    },
    {
        "output_name": "05_overextension_filter",
        "engine_cls": load_class("05_overextension_filter.py", "OverextensionFilterEngine"),
        "config_overrides": {},
    },
    {
        "output_name": "06_early_failure_exit",
        "engine_cls": load_class("06_early_failure_exit.py", "EarlyFailureExitEngine"),
        "config_overrides": {},
    },
    {
        "output_name": "07_candle_quality_adx20_rising",
        "engine_cls": load_class(
            "07_candle_quality_adx20_rising.py",
            "CandleQualityAdx20RisingEngine",
        ),
        "config_overrides": {"h1_adx_min": 20.0},
    },
]


def build_config(input_file: Path, overrides: dict) -> object:
    cfg = default_config(input_file)
    for key, value in overrides.items():
        setattr(cfg, key, value)
    return cfg


def run_variant(output_name: str, engine_cls: type[VBExperimentEngine], config_overrides: dict):
    output_dir = DATA_ROOT / output_name
    reports = []
    unified_rows = []

    for input_file in resolve_input_files(None, ["H4"]):
        engine = engine_cls(build_config(input_file, config_overrides))
        engine.load_data()
        report = engine.run()
        reports.append(report)
        unified_rows.extend(report_to_unified_rows(report, output_name=output_name))
        print(f"{output_name}: {Path(input_file).stem} done")

    summary = summarize_reports(reports)
    summary["experiment"] = {
        "name": output_name,
        "description": engine_cls.experiment_description,
        "output_dir": str(output_dir),
    }
    write_unified_trades(output_dir, unified_rows)
    write_summary(output_dir, summary)
    return summary


def main() -> None:
    all_summaries = []
    for item in VARIANTS:
        summary = run_variant(**item)
        all_summaries.append(summary)

    comparison_rows = []
    for summary in all_summaries:
        item = {key: value for key, value in summary.items() if key != "rows"}
        comparison_rows.append(item)

        rows_ex_2025 = [row for row in summary["rows"] if row["year"] != "2025"]
        if rows_ex_2025:
            ex_returns = [row["return_pct"] for row in rows_ex_2025]
            ex_pfs = [row["profit_factor"] for row in rows_ex_2025]
            ex_dds = [row["max_drawdown_pct"] for row in rows_ex_2025]
            ex_trades = [row["trades"] for row in rows_ex_2025]
            ex_win_rates = [row["win_rate"] for row in rows_ex_2025]
            comparison_rows.append(
                {
                    "years": len(rows_ex_2025),
                    "avg_return_pct": sum(ex_returns) / len(ex_returns),
                    "avg_profit_factor": sum(ex_pfs) / len(ex_pfs),
                    "avg_max_drawdown_pct": sum(ex_dds) / len(ex_dds),
                    "positive_years": sum(1 for row in rows_ex_2025 if row["return_pct"] > 0.0),
                    "avg_trades": sum(ex_trades) / len(ex_trades),
                    "avg_win_rate": sum(ex_win_rates) / len(ex_win_rates),
                    "total_early_exits": sum(row["early_exit_count"] for row in rows_ex_2025),
                    "worst_year": min(rows_ex_2025, key=lambda row: row["return_pct"]),
                    "best_year": max(rows_ex_2025, key=lambda row: row["return_pct"]),
                    "experiment": {
                        **summary["experiment"],
                        "name": f"{summary['experiment']['name']}_ex_2025",
                    },
                }
            )

    (DATA_ROOT / "comparison_summary.json").write_text(
        json.dumps(comparison_rows, indent=2),
        encoding="utf-8",
    )

    import pandas as pd

    flat_rows = []
    for item in comparison_rows:
        flat_rows.append(
            {
                "name": item["experiment"]["name"],
                "years": item["years"],
                "avg_return_pct": item["avg_return_pct"],
                "avg_profit_factor": item["avg_profit_factor"],
                "avg_max_drawdown_pct": item["avg_max_drawdown_pct"],
                "positive_years": item["positive_years"],
                "avg_trades": item["avg_trades"],
                "avg_win_rate": item["avg_win_rate"],
                "worst_year": (
                    f"{item['worst_year']['year']}:{item['worst_year']['return_pct']:.2f}"
                ),
                "best_year": (
                    f"{item['best_year']['year']}:{item['best_year']['return_pct']:.2f}"
                ),
            }
        )
    pd.DataFrame(flat_rows).to_csv(DATA_ROOT / "comparison_summary.csv", index=False)
    print(DATA_ROOT / "comparison_summary.csv")


if __name__ == "__main__":
    main()
