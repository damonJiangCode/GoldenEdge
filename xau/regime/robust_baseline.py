from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "xau" / "reports" / "regime_baseline" / "trades_all.csv"
OUTPUT = REPO_ROOT / "xau" / "reports" / "regime_baseline_robust"

SLEEVE_INITIAL_BALANCE = 1000.0
PORTFOLIO_INITIAL_BALANCE = 2000.0
EXECUTABLE_SLEEVE_CAPITAL = 10000.0
EXECUTABLE_PORTFOLIO_CAPITAL = EXECUTABLE_SLEEVE_CAPITAL * 2.0
RISK_BUDGET_PCT = 1.0
RISK_BUDGET_MONEY = SLEEVE_INITIAL_BALANCE * RISK_BUDGET_PCT / 100.0
BASE_SLIPPAGE_TICKS = 1.0
POINT_VALUE = 0.01

SCENARIOS = {
    "base": {"slippage_ticks": 1.0, "commission_round_turn": 0.05},
    "stress": {"slippage_ticks": 10.0, "commission_round_turn": 0.10},
    "severe": {"slippage_ticks": 20.0, "commission_round_turn": 0.20},
}


def max_drawdown(
    values: pd.Series, initial_balance: float = PORTFOLIO_INITIAL_BALANCE
) -> tuple[float, float]:
    equity = initial_balance + values.cumsum()
    equity = pd.concat(
        [pd.Series([initial_balance]), equity], ignore_index=True
    )
    peak = equity.cummax()
    drawdown = peak - equity
    drawdown_pct = drawdown / peak.replace(0.0, np.nan)
    return float(drawdown.max()), float(drawdown_pct.max() * 100.0)


def annual_stats(group: pd.DataFrame, scenario: str) -> dict[str, Any]:
    pnl = group[f"{scenario}_normalized_net_pnl"]
    gross_profit = float(pnl[pnl > 0.0].sum())
    gross_loss = float(-pnl[pnl < 0.0].sum())
    dd_abs, dd_pct = max_drawdown(pnl)
    return {
        "year": int(group["year"].iloc[0]),
        "scenario": scenario,
        "trades": int(len(group)),
        "net_pnl": float(pnl.sum()),
        "return_pct": float(pnl.sum() / PORTFOLIO_INITIAL_BALANCE * 100.0),
        "profit_factor": gross_profit / gross_loss if gross_loss > 0.0 else 0.0,
        "max_closed_trade_drawdown_abs": dd_abs,
        "max_closed_trade_drawdown_pct": dd_pct,
    }


def scenario_overview(annual: pd.DataFrame, scenario: str) -> dict[str, Any]:
    rows = annual[annual["scenario"] == scenario]
    return {
        "positive_years": int((rows["return_pct"] > 0.0).sum()),
        "average_annual_return_pct": float(rows["return_pct"].mean()),
        "median_annual_return_pct": float(rows["return_pct"].median()),
        "worst_annual_return_pct": float(rows["return_pct"].min()),
        "best_annual_return_pct": float(rows["return_pct"].max()),
        "average_annual_max_closed_trade_drawdown_pct": float(
            rows["max_closed_trade_drawdown_pct"].mean()
        ),
        "worst_annual_max_closed_trade_drawdown_pct": float(
            rows["max_closed_trade_drawdown_pct"].max()
        ),
        "simple_sum_net_pnl": float(rows["net_pnl"].sum()),
    }


def robust_score(overview: dict[str, Any]) -> float:
    stress = overview["stress"]
    severe = overview["severe"]
    return float(
        stress["median_annual_return_pct"]
        + stress["worst_annual_return_pct"]
        + 0.5 * severe["median_annual_return_pct"]
        - stress["worst_annual_max_closed_trade_drawdown_pct"]
    )


def executable_capital_view(trades: pd.DataFrame) -> dict[str, Any]:
    annual = []
    for year, group in trades.groupby("year", sort=True):
        pnl = pd.to_numeric(group["net_pnl"], errors="coerce")
        dd_abs, dd_pct = max_drawdown(pnl, EXECUTABLE_PORTFOLIO_CAPITAL)
        annual.append(
            {
                "year": int(year),
                "net_pnl": float(pnl.sum()),
                "return_pct": float(pnl.sum() / EXECUTABLE_PORTFOLIO_CAPITAL * 100.0),
                "max_closed_trade_drawdown_abs": dd_abs,
                "max_closed_trade_drawdown_pct": dd_pct,
            }
        )
    rows = pd.DataFrame(annual)
    return {
        "sleeve_capital": EXECUTABLE_SLEEVE_CAPITAL,
        "portfolio_capital": EXECUTABLE_PORTFOLIO_CAPITAL,
        "position_size": "original executable fixed 0.01 lot",
        "maximum_observed_initial_risk_pct_of_sleeve": float(
            trades["initial_risk_money"].max() / EXECUTABLE_SLEEVE_CAPITAL * 100.0
        ),
        "positive_years": int((rows["return_pct"] > 0.0).sum()),
        "average_annual_return_pct": float(rows["return_pct"].mean()),
        "median_annual_return_pct": float(rows["return_pct"].median()),
        "worst_annual_return_pct": float(rows["return_pct"].min()),
        "best_annual_return_pct": float(rows["return_pct"].max()),
        "worst_annual_max_closed_trade_drawdown_pct": float(
            rows["max_closed_trade_drawdown_pct"].max()
        ),
        "annual": annual,
    }


def main() -> None:
    trades = pd.read_csv(SOURCE)
    trades["exit_time_utc"] = pd.to_datetime(trades["exit_time_utc"], utc=True)
    trades.sort_values(["exit_time_utc", "trade_id"], inplace=True, ignore_index=True)
    trades["year"] = trades["exit_time_utc"].dt.year
    risk = pd.to_numeric(trades["initial_risk_money"], errors="coerce")
    if risk.isna().any() or (risk <= 0.0).any():
        raise ValueError("All unified trades must have positive initial_risk_money.")

    trades["original_lot_size"] = 0.01
    trades["risk_budget_money"] = RISK_BUDGET_MONEY
    trades["size_scale"] = np.minimum(1.0, RISK_BUDGET_MONEY / risk)
    trades["normalized_lot_size"] = trades["original_lot_size"] * trades["size_scale"]
    trades["normalized_initial_risk_money"] = risk * trades["size_scale"]

    for name, settings in SCENARIOS.items():
        extra_slippage = (
            2.0
            * (settings["slippage_ticks"] - BASE_SLIPPAGE_TICKS)
            * POINT_VALUE
        )
        extra_commission = settings["commission_round_turn"] - 0.05
        trades[f"{name}_normalized_net_pnl"] = trades["size_scale"] * (
            pd.to_numeric(trades["net_pnl"], errors="coerce")
            - extra_slippage
            - extra_commission
        )

    annual_rows = []
    for _, group in trades.groupby("year", sort=True):
        for scenario in SCENARIOS:
            annual_rows.append(annual_stats(group, scenario))
    annual = pd.DataFrame(annual_rows)
    overview = {
        scenario: scenario_overview(annual, scenario) for scenario in SCENARIOS
    }
    executable = executable_capital_view(trades)

    original_net = float(pd.to_numeric(trades["net_pnl"], errors="coerce").sum())
    top_10_share = float(
        pd.to_numeric(trades["net_pnl"], errors="coerce")
        .sort_values(ascending=False)
        .head(10)
        .sum()
        / original_net
    )
    report = {
        "engine": "regime_baseline_robust_audit",
        "source": str(SOURCE),
        "method": {
            "sleeve_initial_balance": SLEEVE_INITIAL_BALANCE,
            "portfolio_initial_balance": PORTFOLIO_INITIAL_BALANCE,
            "risk_budget_pct_per_sleeve_trade": RISK_BUDGET_PCT,
            "risk_budget_money_per_sleeve_trade": RISK_BUDGET_MONEY,
            "position_sizing": "original 0.01 lot scaled down only; never scaled up",
            "drawdown": "closed-trade event curve; excludes intratrade MTM",
            "scenarios": SCENARIOS,
        },
        "exposure_audit": {
            "trades": int(len(trades)),
            "trades_scaled_down": int((trades["size_scale"] < 1.0).sum()),
            "trades_scaled_down_pct": float((trades["size_scale"] < 1.0).mean() * 100.0),
            "median_size_scale": float(trades["size_scale"].median()),
            "minimum_size_scale": float(trades["size_scale"].min()),
            "original_top_10_winner_share_pct": top_10_share * 100.0,
        },
        "overview": overview,
        "executable_capital_view": executable,
        "robust_score": robust_score(overview),
        "optimization_gate": {
            "required_positive_stress_years": 8,
            "required_positive_severe_years": 6,
            "candidate_must_beat_baseline_robust_score": True,
            "candidate_must_not_worsen_stress_worst_drawdown": True,
            "final_2025_result_is_reported_but_not_used_for_parameter_selection": True,
        },
        "notes": [
            "This is an optimization comparison baseline, not a replacement execution engine.",
            "The executable capital view keeps the original 0.01 lot and uses 10000 per sleeve.",
            "Risk normalization removes much of the fixed-lot exposure drift across gold price regimes.",
            "Risk-normalized fractional lots are analytical and may be below a broker's minimum lot.",
            "Stress scenarios penalize MR's high turnover and sensitivity to execution costs.",
            "Closed-trade drawdown understates intratrade MTM drawdown and is marked accordingly.",
        ],
    }

    OUTPUT.mkdir(parents=True, exist_ok=True)
    trades.to_csv(OUTPUT / "risk_normalized_trades.csv", index=False)
    annual.to_csv(OUTPUT / "annual_scenarios.csv", index=False)
    (OUTPUT / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Robust Regime Optimization Baseline",
        "",
        "The original fixed-lot baseline is reproducible, but its cross-year risk exposure is not stable.",
        "This report scales positions down so each strategy trade risks at most 1% of its 1000 sleeve.",
        "",
        "## Exposure Audit",
        "",
        f"- Trades: `{report['exposure_audit']['trades']}`",
        f"- Trades scaled down: `{report['exposure_audit']['trades_scaled_down']}` "
        f"(`{report['exposure_audit']['trades_scaled_down_pct']:.2f}%`)",
        f"- Median / minimum size scale: `{report['exposure_audit']['median_size_scale']:.3f}` / "
        f"`{report['exposure_audit']['minimum_size_scale']:.3f}`",
        f"- Original top-10 winner share of all net PnL: "
        f"`{report['exposure_audit']['original_top_10_winner_share_pct']:.2f}%`",
        "",
        "## Executable Capital View",
        "",
        "- Keep the original fixed `0.01 lot`; use `10000` capital per strategy sleeve.",
        f"- Maximum observed initial risk: `{executable['maximum_observed_initial_risk_pct_of_sleeve']:.2f}%` "
        "of one sleeve.",
        f"- Positive years: `{executable['positive_years']}/11`",
        f"- Average / median annual return: `{executable['average_annual_return_pct']:.2f}%` / "
        f"`{executable['median_annual_return_pct']:.2f}%`",
        f"- Worst / best annual return: `{executable['worst_annual_return_pct']:.2f}%` / "
        f"`{executable['best_annual_return_pct']:.2f}%`",
        "",
        "## Scenario Summary",
        "",
        "| Scenario | Positive years | Avg return % | Median return % | Worst return % | "
        "Best return % | Worst closed-trade DD % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for scenario in SCENARIOS:
        row = overview[scenario]
        lines.append(
            f"| {scenario} | {row['positive_years']}/11 | "
            f"{row['average_annual_return_pct']:.2f} | "
            f"{row['median_annual_return_pct']:.2f} | "
            f"{row['worst_annual_return_pct']:.2f} | "
            f"{row['best_annual_return_pct']:.2f} | "
            f"{row['worst_annual_max_closed_trade_drawdown_pct']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Optimization Gate",
            "",
            f"- Baseline robust score: `{report['robust_score']:.3f}`",
            "- Require at least `8/11` positive stress years and `6/11` positive severe years.",
            "- Candidate robust score must beat this baseline.",
            "- Candidate stress worst drawdown must not exceed this baseline.",
            "- 2025 is reported, but must not be used for parameter or Regime-rule selection.",
            "",
            "## Important Limitation",
            "",
            "Risk-normalized fractional lots are an analytical optimization score and may not be executable "
            "when the broker minimum lot is 0.01. The executable capital view is the primary money-return "
            "reference.",
            "",
            "Drawdown in this report is calculated at closed-trade events and excludes intratrade MTM. "
            "Final Regime candidates must be rerun through a portfolio engine with full equity curves.",
            "",
        ]
    )
    (OUTPUT / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
