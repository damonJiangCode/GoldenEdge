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


class CandleQualityAdx20RisingEngine(VBExperimentEngine):
    experiment_name = "07_candle_quality_adx20_rising"
    experiment_description = (
        "Require breakout candle close quality, H1 ADX >= 20, and H1 ADX rising."
    )

    def load_data(self):
        out = super().load_data()
        out["h1_adx_mean_3"] = out["h1_adx"].rolling(window=3, min_periods=3).mean().shift(1)
        out.dropna(subset=["h1_adx_mean_3"], inplace=True)
        out.reset_index(drop=True, inplace=True)
        self.df = out
        return out

    def signal_extra_filter(self, row, signal):
        bar_range = float(row["high"]) - float(row["low"])
        if bar_range <= 0.0:
            return False, "candle_quality_zero_range"

        close_position = (float(row["close"]) - float(row["low"])) / bar_range
        if signal == "long" and close_position < 0.65:
            return False, "candle_quality_close_not_high_enough"
        if signal == "short" and close_position > 0.35:
            return False, "candle_quality_close_not_low_enough"

        if float(row["h1_adx"]) <= float(row["h1_adx_mean_3"]):
            return False, "adx_not_rising"

        return True, None


if __name__ == "__main__":
    output_dir = DATA_ROOT / "07_candle_quality_adx20_rising"
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    reports = []

    for input_file in resolve_input_files(None, ["H4"]):
        cfg = default_config(input_file)
        cfg.h1_adx_min = 20.0
        engine = CandleQualityAdx20RisingEngine(cfg)
        engine.load_data()
        report = engine.run()
        year = Path(str(report["input_file"])).stem.split("_")[-1]
        report_path = reports_dir / f"report_{year}.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        reports.append(report)
        print(f"{CandleQualityAdx20RisingEngine.experiment_name}: {year} -> {report_path}")

    summary = summarize_reports(reports)
    summary["experiment"] = {
        "name": CandleQualityAdx20RisingEngine.experiment_name,
        "description": CandleQualityAdx20RisingEngine.experiment_description,
        "output_dir": str(output_dir),
    }
    write_summary(output_dir, summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
