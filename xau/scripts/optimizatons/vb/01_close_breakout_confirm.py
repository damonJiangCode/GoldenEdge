from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import VBExperimentEngine, run_experiment  # noqa: E402


class CloseBreakoutConfirmEngine(VBExperimentEngine):
    experiment_name = "01_close_breakout_confirm"
    experiment_description = "Require H4 close beyond Donchian breakout level."

    def calc_signal(self, row):
        ok, reason = self._filter_ok(row)
        if not ok:
            return None, reason
        close = float(row["close"])
        hit_up = close > float(row["donchian_high_n"])
        hit_dn = close < float(row["donchian_low_n"])
        if hit_up and hit_dn:
            return None, "both_breakout_same_bar"
        if hit_up:
            return "long", None
        if hit_dn:
            return "short", None
        return None, None


if __name__ == "__main__":
    run_experiment(CloseBreakoutConfirmEngine, "01_close_breakout_confirm")
