from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import VBExperimentEngine, run_experiment  # noqa: E402


class EarlyFailureExitEngine(VBExperimentEngine):
    experiment_name = "06_early_failure_exit"
    experiment_description = "Exit after 8 H4 bars if trade has not reached +0.5R."

    max_wait_bars = 8
    min_favorable_r = 0.5

    def early_exit_raw_price(self, position, row, idx):
        holding_bars = idx - int(position["entry_idx"]) + 1
        if holding_bars < self.max_wait_bars:
            return None

        entry_price = float(position["entry_price"])
        entry_atr = float(position["entry_atr"])
        initial_risk = self.config.sl_atr_mult * entry_atr
        if initial_risk <= 0.0:
            return None

        side = str(position["side"])
        if side == "long":
            best_price = float(position["highest_since_entry"])
            favorable_r = (best_price - entry_price) / initial_risk
            raw_exit = float(row["close"])
        else:
            best_price = float(position["lowest_since_entry"])
            favorable_r = (entry_price - best_price) / initial_risk
            raw_exit = float(row["close"]) + self.points_to_price(float(row["spread"]))

        if favorable_r < self.min_favorable_r:
            return "EARLY_FAILURE_EXIT", raw_exit
        return None


if __name__ == "__main__":
    run_experiment(EarlyFailureExitEngine, "06_early_failure_exit")
