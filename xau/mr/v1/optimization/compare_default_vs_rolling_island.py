from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xau.mr.v1.engine import EngineConfig, MeanReversionV1Engine  # noqa: E402
from xau.mr.v1.optimization.param_island_v1 import baseline_params, input_file  # noqa: E402

RESULT_ROOT = Path(__file__).resolve().parent / "results_default_vs_rolling_island"
YEARS = list(range(2015, 2026))

ROLLING_ISLAND_PARAMS: dict[str, Any] = {
    "ema_period": 50,
    "atr_period": 7,
    "band_atr_mult": 2.25,
    "sl_atr_mult": 10.0,
    "adx_period": 28,
    "h1_adx_limit": 28.0,
    "atr_ratio_lookback": 40,
    "atr_ratio_min": 0.0,
    "atr_ratio_max": 2.0,
    "wick_body_ratio": 3.0,
    "fat_tail_body_lookback": 13,
    "fat_tail_body_mult": 5.0,
    "breakeven_retrace_ratio": 2.0,
    "session_start_hour_utc": 0,
    "session_end_hour_utc": 24,
}


def build_config(year: int, params: dict[str, Any]) -> EngineConfig:
    cfg = EngineConfig(input_file=input_file(year))
    for key, value in params.items():
        setattr(cfg, key, value)
    return cfg


def run_variant(name: str, params: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    annual = []
    all_trades = []
    total_commission = 0.0
    total_swap = 0.0
    for year in YEARS:
        engine = MeanReversionV1Engine(build_config(year, params))
        engine.load_data()
        report = engine.run()
        perf = report["performance"]
        trades = report["trade_details"]
        all_trades.extend(trades)
        total_commission += float(report["costs"]["total_commission"])
        total_swap += float(report["costs"]["total_realized_swap"])
        annual.append(
            {
                "variant": name,
                "year": year,
                "trades": int(report["trades"]),
                "win_rate_pct": float(report["win_rate"] * 100.0),
                "net_pnl": float(perf["net_pnl"]),
                "return_pct": float(perf["return_pct"]),
                "profit_factor": float(perf["profit_factor"]),
                "expectancy_per_trade": float(perf["expectancy_per_trade"]),
                "max_drawdown_pct": float(perf["max_drawdown_pct"]),
                "avg_holding_bars": float(
                    np.mean([trade["holding_bars"] for trade in trades])
                )
                if trades
                else 0.0,
                "commission": float(report["costs"]["total_commission"]),
            }
        )

    pnls = np.array([float(trade["net_pnl"]) for trade in all_trades], dtype=float)
    gross_profit = float(np.sum(pnls[pnls > 0.0]))
    gross_loss_abs = float(-np.sum(pnls[pnls < 0.0]))
    returns = np.array([row["return_pct"] for row in annual], dtype=float)
    pfs = np.array([row["profit_factor"] for row in annual], dtype=float)
    dds = np.array([row["max_drawdown_pct"] for row in annual], dtype=float)
    trades_per_year = np.array([row["trades"] for row in annual], dtype=float)
    hypothetical_compounded = float(
        (np.prod(1.0 + returns / 100.0) - 1.0) * 100.0
    )
    summary = {
        "variant": name,
        "params": params,
        "years": YEARS,
        "positive_years": int(np.sum(returns > 0.0)),
        "simple_sum_return_pct": float(np.sum(returns)),
        "hypothetical_compounded_return_pct": hypothetical_compounded,
        "avg_annual_return_pct": float(np.mean(returns)),
        "median_annual_return_pct": float(np.median(returns)),
        "worst_annual_return_pct": float(np.min(returns)),
        "best_annual_return_pct": float(np.max(returns)),
        "avg_annual_profit_factor": float(np.mean(pfs)),
        "pooled_profit_factor": gross_profit / gross_loss_abs
        if gross_loss_abs > 0
        else float("inf"),
        "avg_annual_max_drawdown_pct": float(np.mean(dds)),
        "worst_annual_max_drawdown_pct": float(np.max(dds)),
        "total_trades": int(len(all_trades)),
        "avg_trades_per_year": float(np.mean(trades_per_year)),
        "pooled_win_rate_pct": float(np.mean(pnls > 0.0) * 100.0),
        "pooled_expectancy_per_trade": float(np.mean(pnls)),
        "pooled_net_pnl": float(np.sum(pnls)),
        "total_commission": total_commission,
        "total_swap": total_swap,
        "avg_holding_bars": float(
            np.mean([float(trade["holding_bars"]) for trade in all_trades])
        ),
    }
    return annual, summary


def parameter_comparison(
    default: dict[str, Any], rolling: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        {
            "parameter": key,
            "default": default[key],
            "rolling_island": rolling[key],
            "same": default[key] == rolling[key],
        }
        for key in default
    ]


def fmt(value: float) -> str:
    return f"{value:.2f}"


def render_markdown(
    annual: pd.DataFrame,
    summaries: list[dict[str, Any]],
    params: list[dict[str, Any]],
) -> str:
    default = summaries[0]
    rolling = summaries[1]
    annual_default = annual[annual["variant"] == "current_default"].set_index("year")
    annual_rolling = annual[annual["variant"] == "rolling_consensus"].set_index("year")
    lines = [
        "# MR V1 Default vs Rolling-Island Comparison",
        "",
        "Coverage: `2015-2025`, M15. Each year resets to initial balance `1000`.",
        "Hypothetical compounded return is shown only as a research comparison.",
        "",
        "## Overall Comparison",
        "",
        "| Metric | Current Default | Rolling Consensus |",
        "| --- | ---: | ---: |",
    ]
    metrics = [
        ("Positive years", f"{default['positive_years']}/11", f"{rolling['positive_years']}/11"),
        ("Average annual return %", fmt(default["avg_annual_return_pct"]), fmt(rolling["avg_annual_return_pct"])),
        ("Median annual return %", fmt(default["median_annual_return_pct"]), fmt(rolling["median_annual_return_pct"])),
        ("Worst annual return %", fmt(default["worst_annual_return_pct"]), fmt(rolling["worst_annual_return_pct"])),
        ("Best annual return %", fmt(default["best_annual_return_pct"]), fmt(rolling["best_annual_return_pct"])),
        ("Simple-sum return %", fmt(default["simple_sum_return_pct"]), fmt(rolling["simple_sum_return_pct"])),
        ("Hypothetical compounded return %", fmt(default["hypothetical_compounded_return_pct"]), fmt(rolling["hypothetical_compounded_return_pct"])),
        ("Average annual PF", fmt(default["avg_annual_profit_factor"]), fmt(rolling["avg_annual_profit_factor"])),
        ("Pooled trade PF", fmt(default["pooled_profit_factor"]), fmt(rolling["pooled_profit_factor"])),
        ("Average annual max DD %", fmt(default["avg_annual_max_drawdown_pct"]), fmt(rolling["avg_annual_max_drawdown_pct"])),
        ("Worst annual max DD %", fmt(default["worst_annual_max_drawdown_pct"]), fmt(rolling["worst_annual_max_drawdown_pct"])),
        ("Total trades", str(default["total_trades"]), str(rolling["total_trades"])),
        ("Pooled win rate %", fmt(default["pooled_win_rate_pct"]), fmt(rolling["pooled_win_rate_pct"])),
        ("Pooled expectancy / trade", fmt(default["pooled_expectancy_per_trade"]), fmt(rolling["pooled_expectancy_per_trade"])),
        ("Pooled net PnL", fmt(default["pooled_net_pnl"]), fmt(rolling["pooled_net_pnl"])),
        ("Total commission", fmt(default["total_commission"]), fmt(rolling["total_commission"])),
        ("Average holding bars", fmt(default["avg_holding_bars"]), fmt(rolling["avg_holding_bars"])),
    ]
    lines.extend(f"| {label} | {left} | {right} |" for label, left, right in metrics)
    lines.extend(
        [
            "",
            "## Annual Comparison",
            "",
            "| Year | Default Return % | Rolling Return % | Δ Return | Default PF | Rolling PF | Default DD % | Rolling DD % |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for year in YEARS:
        left = annual_default.loc[year]
        right = annual_rolling.loc[year]
        lines.append(
            f"| {year} | {left['return_pct']:.2f} | {right['return_pct']:.2f} | "
            f"{right['return_pct'] - left['return_pct']:+.2f} | "
            f"{left['profit_factor']:.2f} | {right['profit_factor']:.2f} | "
            f"{left['max_drawdown_pct']:.2f} | {right['max_drawdown_pct']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Parameter Differences",
            "",
            "| Parameter | Current Default | Rolling Consensus | Same |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    lines.extend(
        f"| {row['parameter']} | {row['default']} | {row['rolling_island']} | "
        f"{'yes' if row['same'] else 'no'} |"
        for row in params
    )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "- The rolling consensus has higher total and average return.",
            "- The current defaults have materially higher PF, lower drawdown, and a better worst year.",
            "- The rolling consensus creates more trades and pays more commission.",
            "- The current defaults remain the preferred production candidate.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    default_params = baseline_params()
    variants = [
        ("current_default", default_params),
        ("rolling_consensus", ROLLING_ISLAND_PARAMS),
    ]
    annual_rows = []
    summaries = []
    for name, params in variants:
        print(f"running {name} 2015-2025", flush=True)
        annual, summary = run_variant(name, params)
        annual_rows.extend(annual)
        summaries.append(summary)

    annual_df = pd.DataFrame(annual_rows)
    params = parameter_comparison(default_params, ROLLING_ISLAND_PARAMS)
    annual_df.to_csv(RESULT_ROOT / "annual_comparison.csv", index=False)
    pd.DataFrame(summaries).drop(columns=["params", "years"]).to_csv(
        RESULT_ROOT / "overall_comparison.csv", index=False
    )
    pd.DataFrame(params).to_csv(RESULT_ROOT / "parameter_comparison.csv", index=False)
    result = {
        "method": {
            "timeframe": "M15",
            "years": YEARS,
            "annual_initial_balance": 1000.0,
            "annual_reset": True,
            "notes": [
                "All years were previously observed.",
                "Hypothetical compounding is not a continuous portfolio simulation.",
                "M15 OHLC cannot reproduce tick-level fill ordering.",
            ],
        },
        "summaries": summaries,
        "annual": annual_rows,
        "parameter_comparison": params,
    }
    (RESULT_ROOT / "comparison.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    (RESULT_ROOT / "REPORT.md").write_text(
        render_markdown(annual_df, summaries, params), encoding="utf-8"
    )
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
