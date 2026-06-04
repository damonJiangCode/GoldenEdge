from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    DATA_ROOT,
    VBExperimentEngine,
    default_config,
    resolve_input_files,
    summarize_reports,
    write_summary,
)


class AtrRatio11Engine(VBExperimentEngine):
    experiment_name = "04_atr_ratio_1_1"
    experiment_description = "Raise ATR ratio minimum from 1.0 to 1.1."


if __name__ == "__main__":
    output_dir = DATA_ROOT / "04_atr_ratio_1_1"
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    reports = []
    for input_file in resolve_input_files(None, ["H4"]):
        cfg = default_config(input_file)
        cfg.atr_ratio_min = 1.1
        engine = AtrRatio11Engine(cfg)
        engine.load_data()
        report = engine.run()
        year = Path(str(report["input_file"])).stem.split("_")[-1]
        report_path = reports_dir / f"report_{year}.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        reports.append(report)
        print(f"{AtrRatio11Engine.experiment_name}: {year} -> {report_path}")
    summary = summarize_reports(reports)
    summary["experiment"] = {
        "name": AtrRatio11Engine.experiment_name,
        "description": AtrRatio11Engine.experiment_description,
        "output_dir": str(output_dir),
    }
    write_summary(output_dir, summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
