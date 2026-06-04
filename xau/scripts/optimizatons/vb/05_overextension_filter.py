from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import VBExperimentEngine, run_experiment  # noqa: E402


class OverextensionFilterEngine(VBExperimentEngine):
    experiment_name = "05_overextension_filter"
    experiment_description = "Reject breakout bars with range greater than 1.8 ATR."

    def signal_extra_filter(self, row, signal):
        bar_range = float(row["high"]) - float(row["low"])
        if bar_range > 1.8 * float(row["atr"]):
            return False, "overextended_breakout_bar"
        return True, None


if __name__ == "__main__":
    run_experiment(OverextensionFilterEngine, "05_overextension_filter")
