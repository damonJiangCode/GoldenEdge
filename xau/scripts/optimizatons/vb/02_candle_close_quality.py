from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import VBExperimentEngine, run_experiment  # noqa: E402


class CandleCloseQualityEngine(VBExperimentEngine):
    experiment_name = "02_candle_close_quality"
    experiment_description = "Require breakout candle to close near the breakout side."

    def signal_extra_filter(self, row, signal):
        bar_range = float(row["high"]) - float(row["low"])
        if bar_range <= 0.0:
            return False, "candle_quality_zero_range"
        close_position = (float(row["close"]) - float(row["low"])) / bar_range
        if signal == "long" and close_position < 0.65:
            return False, "candle_quality_close_not_high_enough"
        if signal == "short" and close_position > 0.35:
            return False, "candle_quality_close_not_low_enough"
        return True, None


if __name__ == "__main__":
    run_experiment(CandleCloseQualityEngine, "02_candle_close_quality")
