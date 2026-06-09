from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORTS_ROOT = REPO_ROOT / "xau" / "data" / "reports"


def finite(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def year_from_report(report: dict[str, Any]) -> str:
    return Path(str(report["input_file"])).stem.split("_")[-1]


def trade_details(report: dict[str, Any]) -> list[dict[str, Any]]:
    return list(report.get("trade_details") or report.get("sample_trades") or [])


def pooled_stats(trades: list[dict[str, Any]]) -> dict[str, Any]:
    pnls = [finite(trade.get("net_pnl")) for trade in trades]
    gross_profit = sum(value for value in pnls if value > 0.0)
    gross_loss_abs = -sum(value for value in pnls if value < 0.0)
    wins = sum(value > 0.0 for value in pnls)
    losses = sum(value < 0.0 for value in pnls)
    flats = len(pnls) - wins - losses
    winning_pnls = [value for value in pnls if value > 0.0]
    losing_pnls = [value for value in pnls if value < 0.0]
    avg_win = statistics.mean(winning_pnls) if winning_pnls else 0.0
    avg_loss_abs = -statistics.mean(losing_pnls) if losing_pnls else 0.0
    holding = [int(trade.get("holding_bars", 0)) for trade in trades]
    commissions = [
        finite(trade.get("entry_commission")) + finite(trade.get("exit_commission"))
        for trade in trades
    ]
    swaps = [finite(trade.get("swap_total")) for trade in trades]
    r_values = [
        finite(trade.get("r_multiple"))
        for trade in trades
        if trade.get("r_multiple") is not None
    ]
    return {
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "flats": flats,
        "win_rate_pct": wins / len(trades) * 100.0 if trades else 0.0,
        "net_pnl": sum(pnls),
        "gross_profit": gross_profit,
        "gross_loss_abs": gross_loss_abs,
        "profit_factor": gross_profit / gross_loss_abs if gross_loss_abs else 0.0,
        "expectancy_per_trade": statistics.mean(pnls) if pnls else 0.0,
        "median_pnl": statistics.median(pnls) if pnls else 0.0,
        "avg_win": avg_win,
        "avg_loss_abs": avg_loss_abs,
        "payoff_ratio": avg_win / avg_loss_abs if avg_loss_abs else 0.0,
        "best_trade": max(pnls, default=0.0),
        "worst_trade": min(pnls, default=0.0),
        "avg_holding_bars": statistics.mean(holding) if holding else 0.0,
        "median_holding_bars": statistics.median(holding) if holding else 0.0,
        "max_holding_bars": max(holding, default=0),
        "total_commission": sum(commissions),
        "total_swap": sum(swaps),
        "avg_r_multiple": statistics.mean(r_values) if r_values else None,
        "sum_r_multiple": sum(r_values) if r_values else None,
    }


def grouped_trade_stats(
    trades: list[dict[str, Any]], field: str
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trade in trades:
        grouped[str(trade.get(field, "UNKNOWN"))].append(trade)
    return {
        key: pooled_stats(values)
        for key, values in sorted(grouped.items(), key=lambda item: item[0])
    }


def common_values(reports: list[dict[str, Any]], field: str) -> dict[str, Any]:
    if not reports:
        return {}
    first = reports[0].get(field, {})
    result = {}
    for key, value in first.items():
        if all(report.get(field, {}).get(key) == value for report in reports[1:]):
            result[key] = value
    return result


def changed_values(reports: list[dict[str, Any]], field: str) -> dict[str, list[Any]]:
    keys = sorted({key for report in reports for key in report.get(field, {})})
    result = {}
    for key in keys:
        values = []
        for report in reports:
            value = report.get(field, {}).get(key)
            if value not in values:
                values.append(value)
        if len(values) > 1:
            result[key] = values
    return result


def summarize_directory(report_dir: Path) -> dict[str, Any]:
    paths = sorted(report_dir.glob("report_*.json"))
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    if not reports:
        raise ValueError(f"No report_*.json files found in {report_dir}")

    annual = []
    all_trades = []
    compound_growth = 1.0
    for report in reports:
        year = year_from_report(report)
        perf = report["performance"]
        trades = trade_details(report)
        all_trades.extend(trades)
        closed_trade_net_pnl = sum(finite(trade.get("net_pnl")) for trade in trades)
        report_net_pnl = finite(perf.get("net_pnl"))
        return_pct = finite(perf.get("return_pct"))
        compound_growth *= 1.0 + return_pct / 100.0
        annual.append(
            {
                "year": year,
                "bars": int(report.get("bars", 0)),
                "trades": int(report.get("trades", 0)),
                "win_rate_pct": finite(report.get("win_rate")) * 100.0,
                "net_pnl": report_net_pnl,
                "closed_trade_net_pnl": closed_trade_net_pnl,
                "open_position_effect": report_net_pnl - closed_trade_net_pnl,
                "open_position_at_end": bool(report.get("open_position_at_end")),
                "return_pct": return_pct,
                "profit_factor": finite(perf.get("profit_factor")),
                "expectancy_per_trade": finite(perf.get("expectancy_per_trade")),
                "sharpe_per_trade": finite(perf.get("sharpe_per_trade")),
                "max_drawdown_abs": finite(perf.get("max_drawdown_abs")),
                "max_drawdown_pct": finite(perf.get("max_drawdown_pct")),
                "gross_profit": finite(perf.get("gross_profit")),
                "gross_loss_abs": finite(perf.get("gross_loss_abs")),
                "commission": finite(report.get("costs", {}).get("total_commission")),
                "swap": finite(report.get("costs", {}).get("total_realized_swap")),
                "spread_mean_points": finite(
                    report.get("costs", {}).get("spread_mean_points")
                ),
                "time_start_utc": report.get("time_start_utc"),
                "time_end_utc": report.get("time_end_utc"),
            }
        )

    returns = [row["return_pct"] for row in annual]
    pfs = [row["profit_factor"] for row in annual]
    drawdowns = [row["max_drawdown_pct"] for row in annual]
    filter_totals: dict[str, float] = defaultdict(float)
    for report in reports:
        for key, value in report.get("filters", {}).items():
            if (
                key.endswith("_count")
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
            ):
                filter_totals[key] += finite(value)

    pooled = pooled_stats(all_trades)
    overview = {
        "engine": reports[0].get("engine"),
        "timeframe": report_dir.name,
        "report_directory": str(report_dir),
        "years": len(annual),
        "year_start": annual[0]["year"],
        "year_end": annual[-1]["year"],
        "positive_years": sum(value > 0.0 for value in returns),
        "negative_years": sum(value < 0.0 for value in returns),
        "avg_annual_return_pct": statistics.mean(returns),
        "median_annual_return_pct": statistics.median(returns),
        "simple_sum_return_pct": sum(returns),
        "hypothetical_compounded_return_pct": (compound_growth - 1.0) * 100.0,
        "avg_annual_profit_factor": statistics.mean(pfs),
        "avg_annual_max_drawdown_pct": statistics.mean(drawdowns),
        "worst_annual_max_drawdown_pct": max(drawdowns),
        "best_year": max(annual, key=lambda row: row["return_pct"]),
        "worst_year": min(annual, key=lambda row: row["return_pct"]),
        "sum_report_net_pnl": sum(row["net_pnl"] for row in annual),
        "sum_closed_trade_net_pnl": sum(row["closed_trade_net_pnl"] for row in annual),
        "sum_open_position_effect": sum(row["open_position_effect"] for row in annual),
        "reports_with_open_position_at_end": sum(
            row["open_position_at_end"] for row in annual
        ),
        "pooled": pooled,
    }
    return {
        "overview": overview,
        "annual": annual,
        "trade_breakdown": {
            "by_side": grouped_trade_stats(all_trades, "side"),
            "by_exit_reason": grouped_trade_stats(all_trades, "exit_reason"),
        },
        "costs": {
            "total_commission": sum(row["commission"] for row in annual),
            "total_swap": sum(row["swap"] for row in annual),
            "avg_spread_mean_points": statistics.mean(
                row["spread_mean_points"] for row in annual
            ),
            "common_settings": common_values(reports, "costs"),
            "changed_settings": changed_values(reports, "costs"),
        },
        "filters": {
            "common_settings": common_values(reports, "filters"),
            "changed_settings": changed_values(reports, "filters"),
            "numeric_totals": dict(sorted(filter_totals.items())),
        },
        "parameters": {
            "common": common_values(reports, "params"),
            "changed": changed_values(reports, "params"),
        },
        "report_files": [str(path) for path in paths],
        "notes": [
            "Each annual report resets to its own initial balance.",
            "Simple-sum and compounded returns are research summaries, not one continuous portfolio simulation.",
            "Annual report net PnL/return uses final equity and may include an open position at year end.",
            "Pooled trade PF is calculated from all closed trade net PnL across the included annual reports.",
            "OHLC backtests cannot reproduce tick-level intrabar ordering or production execution exactly.",
        ],
    }


def fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}"
    if isinstance(value, (list, dict)):
        return f"`{json.dumps(value, ensure_ascii=False, separators=(',', ':'))}`"
    return str(value)


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---:" if idx else "---" for idx in range(len(headers))) + "|",
    ]
    lines.extend("| " + " | ".join(fmt(value) for value in row) + " |" for row in rows)
    return lines


def grouped_markdown(title: str, grouped: dict[str, dict[str, Any]]) -> list[str]:
    rows = []
    for name, stats in grouped.items():
        rows.append(
            [
                name,
                stats["trades"],
                stats["win_rate_pct"],
                stats["net_pnl"],
                stats["profit_factor"],
                stats["expectancy_per_trade"],
                stats["avg_holding_bars"],
            ]
        )
    return [
        f"## {title}",
        "",
        *markdown_table(
            ["Group", "Trades", "Win %", "Net PnL", "PF", "Expectancy", "Avg Hold"],
            rows,
        ),
        "",
    ]


def render_markdown(summary: dict[str, Any]) -> str:
    overview = summary["overview"]
    pooled = overview["pooled"]
    lines = [
        f"# {overview['engine']} {overview['timeframe']} Report Summary",
        "",
        f"Source: `{overview['report_directory']}/report_*.json`",
        "",
        "## Executive Summary",
        "",
        f"- Coverage: `{overview['year_start']}-{overview['year_end']}` ({overview['years']} annual reports).",
        f"- Positive years: `{overview['positive_years']}/{overview['years']}`.",
        f"- Average / median annual return: `{overview['avg_annual_return_pct']:.2f}%` / `{overview['median_annual_return_pct']:.2f}%`.",
        f"- Best year: `{overview['best_year']['year']}` at `{overview['best_year']['return_pct']:.2f}%`.",
        f"- Worst year: `{overview['worst_year']['year']}` at `{overview['worst_year']['return_pct']:.2f}%`.",
        f"- Average / worst annual max drawdown: `{overview['avg_annual_max_drawdown_pct']:.2f}%` / `{overview['worst_annual_max_drawdown_pct']:.2f}%`.",
        f"- Pooled trades: `{pooled['trades']}`; pooled net PnL: `{pooled['net_pnl']:.2f}`; pooled PF: `{pooled['profit_factor']:.3f}`.",
        f"- Reports ending with an open position: `{overview['reports_with_open_position_at_end']}/{overview['years']}`; combined year-end open-position effect: `{overview['sum_open_position_effect']:.2f}`.",
        "",
        "## Aggregate Metrics",
        "",
        *markdown_table(
            ["Metric", "Value"],
            [
                ["Simple sum return %", overview["simple_sum_return_pct"]],
                ["Hypothetical compounded return %", overview["hypothetical_compounded_return_pct"]],
                ["Average annual PF", overview["avg_annual_profit_factor"]],
                ["Sum report net PnL", overview["sum_report_net_pnl"]],
                ["Sum closed-trade net PnL", overview["sum_closed_trade_net_pnl"]],
                ["Year-end open-position effect", overview["sum_open_position_effect"]],
                ["Pooled win rate %", pooled["win_rate_pct"]],
                ["Pooled expectancy / trade", pooled["expectancy_per_trade"]],
                ["Median trade PnL", pooled["median_pnl"]],
                ["Average winning trade", pooled["avg_win"]],
                ["Average losing trade abs", pooled["avg_loss_abs"]],
                ["Average win / average loss", pooled["payoff_ratio"]],
                ["Best trade", pooled["best_trade"]],
                ["Worst trade", pooled["worst_trade"]],
                ["Average holding bars", pooled["avg_holding_bars"]],
                ["Median holding bars", pooled["median_holding_bars"]],
                ["Maximum holding bars", pooled["max_holding_bars"]],
                ["Total commission", pooled["total_commission"]],
                ["Total swap", pooled["total_swap"]],
                ["Average R multiple", pooled["avg_r_multiple"]],
                ["Sum R multiple", pooled["sum_r_multiple"]],
            ],
        ),
        "",
        "## Annual Performance",
        "",
        *markdown_table(
            [
                "Year", "Trades", "Win %", "Report Net", "Closed Net", "Open Δ",
                "Return %", "PF", "Expectancy", "Max DD %", "Commission",
            ],
            [
                [
                    row["year"], row["trades"], row["win_rate_pct"], row["net_pnl"],
                    row["closed_trade_net_pnl"], row["open_position_effect"],
                    row["return_pct"], row["profit_factor"], row["expectancy_per_trade"],
                    row["max_drawdown_pct"], row["commission"],
                ]
                for row in summary["annual"]
            ],
        ),
        "",
        *grouped_markdown("Trade Breakdown By Side", summary["trade_breakdown"]["by_side"]),
        *grouped_markdown(
            "Trade Breakdown By Exit Reason", summary["trade_breakdown"]["by_exit_reason"]
        ),
        "## Filter Activity Totals",
        "",
        *markdown_table(
            ["Filter / Counter", "Total"],
            [[key, value] for key, value in summary["filters"]["numeric_totals"].items()],
        ),
        "",
        "## Common Parameters",
        "",
        *markdown_table(
            ["Parameter", "Value"],
            [[key, value] for key, value in summary["parameters"]["common"].items()],
        ),
        "",
        "## Common Cost Settings",
        "",
        *markdown_table(
            ["Setting", "Value"],
            [[key, value] for key, value in summary["costs"]["common_settings"].items()],
        ),
        "",
        "## Reading Notes",
        "",
        *[f"- {note}" for note in summary["notes"]],
        "",
    ]
    if summary["parameters"]["changed"]:
        lines.extend(
            [
                "## Parameter Differences Across Reports",
                "",
                *markdown_table(
                    ["Parameter", "Observed Values"],
                    [
                        [key, value]
                        for key, value in summary["parameters"]["changed"].items()
                    ],
                ),
                "",
            ]
        )
    return "\n".join(lines)


def write_summary(report_dir: Path) -> None:
    summary = summarize_directory(report_dir)
    (report_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    pd.DataFrame(summary["annual"]).to_csv(report_dir / "summary.csv", index=False)
    (report_dir / "summary.md").write_text(render_markdown(summary), encoding="utf-8")
    print(f"wrote {report_dir / 'summary.md'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize annual XAU report JSON files")
    parser.add_argument("report_dirs", nargs="*", type=Path)
    args = parser.parse_args()
    report_dirs = args.report_dirs or sorted(
        {path.parent for path in REPORTS_ROOT.rglob("report_*.json")}
    )
    for report_dir in report_dirs:
        write_summary(report_dir.resolve())


if __name__ == "__main__":
    main()
