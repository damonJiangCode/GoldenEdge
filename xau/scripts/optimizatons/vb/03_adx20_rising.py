from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import VBExperimentEngine, default_config, run_experiment  # noqa: E402


class Adx20RisingEngine(VBExperimentEngine):
    experiment_name = "03_adx20_rising"
    experiment_description = "Raise H1 ADX minimum to 20 and require ADX to be rising."

    def load_data(self):
        out = super().load_data()
        out["h1_adx_mean_3"] = out["h1_adx"].rolling(window=3, min_periods=3).mean().shift(1)
        out.dropna(subset=["h1_adx_mean_3"], inplace=True)
        out.reset_index(drop=True, inplace=True)
        self.df = out
        return out

    def signal_extra_filter(self, row, signal):
        if float(row["h1_adx"]) <= float(row["h1_adx_mean_3"]):
            return False, "adx_not_rising"
        return True, None


def config(input_file):
    cfg = default_config(input_file)
    cfg.h1_adx_min = 20.0
    return cfg


if __name__ == "__main__":
    from common import resolve_input_files, DATA_ROOT, summarize_reports, write_summary
    import json

    output_dir = DATA_ROOT / "03_adx20_rising"
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    reports = []
    for input_file in resolve_input_files(None, ["H4"]):
        engine = Adx20RisingEngine(config(input_file))
        engine.load_data()
        report = engine.run()
        year = Path(str(report["input_file"])).stem.split("_")[-1]
        report_path = reports_dir / f"report_{year}.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        reports.append(report)
        print(f"{Adx20RisingEngine.experiment_name}: {year} -> {report_path}")
    summary = summarize_reports(reports)
    summary["experiment"] = {
        "name": Adx20RisingEngine.experiment_name,
        "description": Adx20RisingEngine.experiment_description,
        "output_dir": str(output_dir),
    }
    write_summary(output_dir, summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
