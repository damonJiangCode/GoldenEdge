from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import EngineConfig, VolatilityBreakoutV2Engine, enforce_training_year


class ResearchBoundaryTest(unittest.TestCase):
    def test_training_year_is_allowed(self) -> None:
        self.assertEqual(enforce_training_year(Path("H4_2023.csv")), 2023)

    def test_oos_year_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "frozen OOS year 2024"):
            enforce_training_year(Path("H4_2024.csv"))


class RiskSizingTest(unittest.TestCase):
    def engine(self) -> VolatilityBreakoutV2Engine:
        return VolatilityBreakoutV2Engine(
            EngineConfig(
                h4_file=Path("H4_2023.csv"),
                h1_file=Path("H1_2023.csv"),
                initial_balance=10_000.0,
                risk_per_trade_pct=1.0,
            )
        )

    def test_lot_is_rounded_down_to_step(self) -> None:
        self.assertEqual(self.engine().lot_size(10_000.0, 30.0), 0.03)

    def test_trade_below_minimum_lot_is_skipped(self) -> None:
        self.assertEqual(self.engine().lot_size(1_000.0, 200.0), 0.0)

    def test_required_margin_uses_lot_contract_and_leverage(self) -> None:
        self.assertEqual(self.engine().required_margin(2_000.0, 0.1), 200.0)


class TimingAndRiskIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[3]
        cls.engine = VolatilityBreakoutV2Engine(
            EngineConfig(
                h4_file=root / "xau" / "marketdata" / "H4" / "H4_2023.csv",
                h1_file=root / "xau" / "marketdata" / "H1" / "H1_2023.csv",
            )
        )
        cls.data = cls.engine.load_data()
        cls.report = cls.engine.run()

    def test_trade_entry_atr_comes_from_completed_signal_bar(self) -> None:
        trade = self.report["trade_details"][0]
        signal_row = self.data.loc[
            self.data["time"] == trade["signal_time"]
        ].iloc[0]
        self.assertAlmostEqual(trade["entry_atr"], signal_row["atr"])

    def test_actual_initial_risk_never_exceeds_budget(self) -> None:
        for trade in self.report["trade_details"]:
            self.assertLessEqual(trade["initial_risk_pct"], 1.0 + 1e-9)

    def test_annual_report_has_no_unclosed_position(self) -> None:
        self.assertIsNone(self.report["open_position_at_end"])


if __name__ == "__main__":
    unittest.main()
