from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).with_name("mt5_m1_ingest.py")
SPEC = importlib.util.spec_from_file_location("mt5_m1_ingest", MODULE_PATH)
assert SPEC and SPEC.loader
INGEST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INGEST)


class ResampleM1Test(unittest.TestCase):
    def test_resample_uses_ohlc_sum_volume_and_rounded_mean_spread(self) -> None:
        m1 = pd.DataFrame(
            {
                "time": pd.date_range("2026-01-02 00:00", periods=16, freq="min"),
                "open": range(100, 116),
                "high": range(101, 117),
                "low": range(99, 115),
                "close": range(100, 116),
                "tick_volume": [10] * 16,
                "spread": [10] * 14 + [20, 30],
            }
        )

        result = INGEST.resample_m1(m1, "M15")

        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]["open"], 100)
        self.assertEqual(result.iloc[0]["high"], 115)
        self.assertEqual(result.iloc[0]["low"], 99)
        self.assertEqual(result.iloc[0]["close"], 114)
        self.assertEqual(result.iloc[0]["tick_volume"], 150)
        self.assertEqual(result.iloc[0]["spread"], 11)

    def test_normalize_sorts_and_deduplicates_time(self) -> None:
        rows = pd.DataFrame(
            {
                "time": ["2026-01-01 00:01", "2026-01-01 00:00", "2026-01-01 00:01"],
                "open": [2, 1, 3],
                "high": [2, 1, 3],
                "low": [2, 1, 3],
                "close": [2, 1, 3],
                "tick_volume": [2, 1, 3],
                "spread": [2, 1, 3],
            }
        )

        result = INGEST.normalize_bars(rows)

        self.assertEqual(result["open"].tolist(), [1, 3])

    def test_normalize_reads_mt5_epoch_seconds(self) -> None:
        rows = pd.DataFrame(
            {
                "time": [1767225600],
                "open": [1],
                "high": [1],
                "low": [1],
                "close": [1],
                "tick_volume": [1],
                "spread": [1],
            }
        )

        result = INGEST.normalize_bars(rows)

        self.assertEqual(str(result.iloc[0]["time"]), "2026-01-01 00:00:00+00:00")

    def test_filter_range_excludes_end_timestamp(self) -> None:
        rows = pd.DataFrame(
            {
                "time": pd.date_range("2026-05-31 23:59", periods=2, freq="min"),
                "open": [1, 2],
                "high": [1, 2],
                "low": [1, 2],
                "close": [1, 2],
                "tick_volume": [1, 2],
                "spread": [1, 2],
            }
        )

        result = INGEST.filter_range(
            rows,
            INGEST.parse_utc("2026-01-01"),
            INGEST.parse_utc("2026-06-01"),
        )

        self.assertEqual(result["open"].tolist(), [1])


if __name__ == "__main__":
    unittest.main()
