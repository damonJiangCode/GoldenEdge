from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.engines.volatility_breakout.v1 import (  # noqa: E402
    EngineConfig,
    VolatilityBreakoutV1Engine,
)


DATA_DIR = PROJECT_ROOT / "data" / "historical" / "H4"
REPORT_DIR = PROJECT_ROOT / "data" / "reports" / "volatility_breakout" / "v1_h4_candidate"
VALIDATION_DIR = PROJECT_ROOT / "data" / "validation" / "volatility_breakout" / "v1_h4_candidate"


@dataclass(frozen=True)
class CandidateParams:
    donchian_breakout_period: int = 18
    donchian_exit_period: int = 10
    sl_atr_mult: float = 2.2
    trail_atr_mult: float = 3.2
    h1_adx_min: float = 18.0
    atr_ratio_min: float = 1.0


@dataclass(frozen=True)
class Scenario:
    name: str
    spread_mult: float
    slippage_ticks: float


def year_from_path(path: Path) -> int:
    match = re.search(r"(19|20)\d{2}", path.stem)
    if not match:
        raise ValueError(f"Cannot find year in filename: {path}")
    return int(match.group(0))


def resolve_h4_files(data_dir: Path) -> dict[int, Path]:
    files = {year_from_path(path): path for path in sorted(data_dir.glob("*.csv"))}
    if not files:
        raise FileNotFoundError(f"No H4 CSV files found under {data_dir}")
    return files


def run_engine(
    input_file: Path,
    params: CandidateParams,
    args: argparse.Namespace,
    *,
    slippage_ticks: float,
) -> dict[str, Any]:
    config = EngineConfig(
        input_file=input_file,
        initial_balance=args.initial_balance,
        lot_size=args.lot_size,
        contract_size=args.contract_size,
        leverage=args.leverage,
        donchian_breakout_period=params.donchian_breakout_period,
        donchian_exit_period=params.donchian_exit_period,
        atr_period=args.atr_period,
        atr_ratio_lookback=args.atr_ratio_lookback,
        atr_ratio_min=params.atr_ratio_min,
        enable_h1_adx_filter=not args.disable_h1_adx_filter,
        adx_period=args.adx_period,
        h1_adx_min=params.h1_adx_min,
        spread_max_points=args.spread_max_points,
        session_start_hour_utc=args.session_start_hour_utc,
        session_end_hour_utc=args.session_end_hour_utc,
        sl_atr_mult=params.sl_atr_mult,
        trail_mode=args.trail_mode,
        trail_atr_mult=params.trail_atr_mult,
        point_value=args.point_value,
        pip_value=args.pip_value,
        slippage_ticks=slippage_ticks,
        commission_per_trade=args.commission_per_trade,
        swap_long_per_lot_per_night=args.swap_long_per_lot_per_night,
        swap_short_per_lot_per_night=args.swap_short_per_lot_per_night,
    )
    engine = VolatilityBreakoutV1Engine(config)
    engine.load_data()
    return engine.run()


def run_engine_with_spread(
    input_file: Path,
    params: CandidateParams,
    args: argparse.Namespace,
    scenario: Scenario,
    tmp_dir: Path,
) -> dict[str, Any]:
    if scenario.spread_mult == 1.0:
        report = run_engine(
            input_file,
            params,
            args,
            slippage_ticks=scenario.slippage_ticks,
        )
    else:
        df = pd.read_csv(input_file)
        df["spread"] = pd.to_numeric(df["spread"], errors="coerce") * scenario.spread_mult
        stressed_input = tmp_dir / f"{input_file.stem}_{scenario.name}.csv"
        df.to_csv(stressed_input, index=False)
        report = run_engine(
            stressed_input,
            params,
            args,
            slippage_ticks=scenario.slippage_ticks,
        )
        report["original_input_file"] = str(input_file)

    report["stress_scenario"] = {
        "name": scenario.name,
        "spread_mult": scenario.spread_mult,
        "slippage_ticks": scenario.slippage_ticks,
    }
    return report


def mean(values: list[float] | list[int]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    return float(math.sqrt(variance))


def summarize_reports(reports: list[dict[str, Any]], years: list[int]) -> dict[str, Any]:
    returns = [float(r["performance"]["return_pct"]) for r in reports]
    pfs = [float(r["performance"]["profit_factor"]) for r in reports]
    dds = [float(r["performance"]["max_drawdown_pct"]) for r in reports]
    trades = [int(r["trades"]) for r in reports]
    win_rates = [float(r["win_rate"]) * 100.0 for r in reports]
    finite_pfs = [pf for pf in pfs if math.isfinite(pf)]
    total_return = sum(returns)
    best_return = max(returns) if returns else 0.0
    return {
        "years": ",".join(str(year) for year in years),
        "year_count": len(years),
        "avg_return_pct": mean(returns),
        "total_return_pct": total_return,
        "avg_pf": mean(finite_pfs),
        "avg_maxdd_pct": mean(dds),
        "avg_win_rate_pct": mean(win_rates),
        "avg_trades": mean(trades),
        "positive_years": sum(1 for value in returns if value > 0.0),
        "pf_gt_1_years": sum(1 for value in pfs if value > 1.0),
        "worst_return_pct": min(returns) if returns else 0.0,
        "best_return_pct": best_return,
        "return_std_pct": stdev(returns),
        "best_year_share": best_return / total_return if total_return > 0 else 0.0,
    }


def report_to_year_row(year: int, report: dict[str, Any]) -> dict[str, Any]:
    perf = report["performance"]
    return {
        "year": year,
        "trades": int(report["trades"]),
        "win_rate_pct": round(float(report["win_rate"]) * 100.0, 6),
        "return_pct": round(float(perf["return_pct"]), 6),
        "profit_factor": round(float(perf["profit_factor"]), 6),
        "max_drawdown_pct": round(float(perf["max_drawdown_pct"]), 6),
        "sharpe_per_trade": round(float(perf["sharpe_per_trade"]), 6),
        "net_pnl": round(float(perf["net_pnl"]), 6),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def flatten_summary(prefix: str, summary: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key, value in summary.items():
        if isinstance(value, float):
            out[f"{prefix}_{key}"] = round(value, 6)
        else:
            out[f"{prefix}_{key}"] = value
    return out


def save_formal_reports(
    reports_by_year: dict[int, dict[str, Any]],
    output_dir: Path,
    params: CandidateParams,
) -> None:
    yearly_dir = output_dir / "H4"
    yearly_dir.mkdir(parents=True, exist_ok=True)
    yearly_rows = []
    for year, report in sorted(reports_by_year.items()):
        report_path = yearly_dir / f"report_{year}.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        yearly_rows.append(report_to_year_row(year, report))
    write_csv(output_dir / "tables" / "H4_summary.csv", yearly_rows)

    summary = summarize_reports(
        [reports_by_year[year] for year in sorted(reports_by_year)],
        sorted(reports_by_year),
    )
    md = [
        "# XAUUSD VB/H4 Candidate Annual Report",
        "",
        "Parameters:",
        "",
        f"- donchian_breakout_period: `{params.donchian_breakout_period}`",
        f"- donchian_exit_period: `{params.donchian_exit_period}`",
        f"- sl_atr_mult: `{params.sl_atr_mult}`",
        f"- trail_atr_mult: `{params.trail_atr_mult}`",
        f"- h1_adx_min: `{params.h1_adx_min}`",
        f"- atr_ratio_min: `{params.atr_ratio_min}`",
        "",
        "Full-period summary:",
        "",
        f"- Avg Return: `{summary['avg_return_pct']:.2f}%`",
        f"- Avg PF: `{summary['avg_pf']:.2f}`",
        f"- Avg MaxDD: `{summary['avg_maxdd_pct']:.2f}%`",
        f"- Positive Years: `{summary['positive_years']}/{summary['year_count']}`",
        f"- Avg Trades: `{summary['avg_trades']:.2f}`",
        "",
    ]
    (output_dir / "summary.md").write_text("\n".join(md), encoding="utf-8")


def build_stress_rows(
    files_by_year: dict[int, Path],
    params: CandidateParams,
    args: argparse.Namespace,
    scenarios: list[Scenario],
    output_dir: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="vb_h4_stress_") as tmp:
        tmp_dir = Path(tmp)
        for scenario in scenarios:
            reports_by_year = {
                year: run_engine_with_spread(path, params, args, scenario, tmp_dir)
                for year, path in sorted(files_by_year.items())
            }
            scenario_dir = output_dir / "scenarios" / scenario.name
            for year, report in reports_by_year.items():
                path = scenario_dir / "H4" / f"report_{year}.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(report, indent=2), encoding="utf-8")

            summary = summarize_reports(
                [reports_by_year[year] for year in sorted(reports_by_year)],
                sorted(reports_by_year),
            )
            row = {
                "scenario": scenario.name,
                "spread_mult": scenario.spread_mult,
                "slippage_ticks": scenario.slippage_ticks,
            }
            row.update(flatten_summary("full", summary))
            rows.append(row)
    write_csv(output_dir / "cost_stress_summary.csv", rows)
    return rows


def build_walk_forward_rows(
    reports_by_year: dict[int, dict[str, Any]],
    output_dir: Path,
) -> list[dict[str, Any]]:
    windows = [
        ("wf_2015_2019__2020_2021", range(2015, 2020), range(2020, 2022)),
        ("wf_2016_2020__2021_2022", range(2016, 2021), range(2021, 2023)),
        ("wf_2017_2021__2022_2023", range(2017, 2022), range(2022, 2024)),
        ("wf_2018_2022__2023_2024", range(2018, 2023), range(2023, 2025)),
        ("wf_2019_2023__2024_2025", range(2019, 2024), range(2024, 2026)),
    ]
    rows: list[dict[str, Any]] = []
    for name, train_years_raw, test_years_raw in windows:
        train_years = [year for year in train_years_raw if year in reports_by_year]
        test_years = [year for year in test_years_raw if year in reports_by_year]
        train_summary = summarize_reports([reports_by_year[y] for y in train_years], train_years)
        test_summary = summarize_reports([reports_by_year[y] for y in test_years], test_years)
        row = {"window": name}
        row.update(flatten_summary("train", train_summary))
        row.update(flatten_summary("test", test_summary))
        rows.append(row)
    write_csv(output_dir / "walk_forward_summary.csv", rows)
    return rows


def write_validation_summary(
    output_dir: Path,
    formal_summary: dict[str, Any],
    stress_rows: list[dict[str, Any]],
    walk_rows: list[dict[str, Any]],
    params: CandidateParams,
) -> None:
    lines = [
        "# XAUUSD VB/H4 Candidate Validation",
        "",
        "Candidate parameters:",
        "",
        f"- N: `{params.donchian_breakout_period}`",
        f"- Exit: `{params.donchian_exit_period}`",
        f"- SL ATR: `{params.sl_atr_mult}`",
        f"- Trail ATR: `{params.trail_atr_mult}`",
        f"- H1 ADX min: `{params.h1_adx_min}`",
        f"- ATR ratio min: `{params.atr_ratio_min}`",
        "",
        "## Formal Annual Report",
        "",
        f"- Avg Return: `{formal_summary['avg_return_pct']:.2f}%`",
        f"- Avg PF: `{formal_summary['avg_pf']:.2f}`",
        f"- Avg MaxDD: `{formal_summary['avg_maxdd_pct']:.2f}%`",
        f"- Positive Years: `{formal_summary['positive_years']}/{formal_summary['year_count']}`",
        "",
        "## Cost Stress",
        "",
        "| Scenario | Spread x | Slippage | Avg Ret | Avg PF | Avg DD | Pos Years | Worst Year |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in stress_rows:
        lines.append(
            "| "
            f"{row['scenario']} | {row['spread_mult']} | {row['slippage_ticks']} | "
            f"{row['full_avg_return_pct']:.2f}% | {row['full_avg_pf']:.2f} | "
            f"{row['full_avg_maxdd_pct']:.2f}% | "
            f"{row['full_positive_years']}/{row['full_year_count']} | "
            f"{row['full_worst_return_pct']:.2f}% |"
        )

    lines.extend(
        [
            "",
            "## Walk Forward",
            "",
            "| Window | Train Ret | Train PF | Test Ret | Test PF | Test Pos Years | Test Worst Year |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in walk_rows:
        lines.append(
            "| "
            f"{row['window']} | "
            f"{row['train_avg_return_pct']:.2f}% | {row['train_avg_pf']:.2f} | "
            f"{row['test_avg_return_pct']:.2f}% | {row['test_avg_pf']:.2f} | "
            f"{row['test_positive_years']}/{row['test_year_count']} | "
            f"{row['test_worst_return_pct']:.2f}% |"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "validation_summary.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate formal reports, cost stress tests, and walk-forward checks for XAUUSD VB/H4 candidate."
    )
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--report-dir", default=str(REPORT_DIR))
    parser.add_argument("--validation-dir", default=str(VALIDATION_DIR))

    parser.add_argument("--donchian-breakout-period", type=int, default=18)
    parser.add_argument("--donchian-exit-period", type=int, default=10)
    parser.add_argument("--sl-atr-mult", type=float, default=2.2)
    parser.add_argument("--trail-atr-mult", type=float, default=3.2)
    parser.add_argument("--h1-adx-min", type=float, default=18.0)
    parser.add_argument("--atr-ratio-min", type=float, default=1.0)

    parser.add_argument("--initial-balance", type=float, default=1000.0)
    parser.add_argument("--lot-size", type=float, default=0.01)
    parser.add_argument("--contract-size", type=int, default=100)
    parser.add_argument("--leverage", type=float, default=100.0)
    parser.add_argument("--atr-period", type=int, default=14)
    parser.add_argument("--atr-ratio-lookback", type=int, default=100)
    parser.add_argument("--disable-h1-adx-filter", action="store_true")
    parser.add_argument("--adx-period", type=int, default=14)
    parser.add_argument("--spread-max-points", type=float, default=30.0)
    parser.add_argument("--session-start-hour-utc", type=int, default=0)
    parser.add_argument("--session-end-hour-utc", type=int, default=24)
    parser.add_argument("--trail-mode", choices=["chandelier", "donchian"], default="chandelier")
    parser.add_argument("--point-value", type=float, default=0.01)
    parser.add_argument("--pip-value", type=float, default=0.01)
    parser.add_argument("--slippage-ticks", type=float, default=1.0)
    parser.add_argument("--commission-per-trade", type=float, default=0.05)
    parser.add_argument("--swap-long-per-lot-per-night", type=float, default=0.0)
    parser.add_argument("--swap-short-per-lot-per-night", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = Path(args.data_dir).expanduser()
    report_dir = Path(args.report_dir).expanduser()
    validation_dir = Path(args.validation_dir).expanduser()
    if not data_dir.is_absolute():
        data_dir = (Path.cwd() / data_dir).resolve()
    if not report_dir.is_absolute():
        report_dir = (Path.cwd() / report_dir).resolve()
    if not validation_dir.is_absolute():
        validation_dir = (Path.cwd() / validation_dir).resolve()

    params = CandidateParams(
        donchian_breakout_period=args.donchian_breakout_period,
        donchian_exit_period=args.donchian_exit_period,
        sl_atr_mult=args.sl_atr_mult,
        trail_atr_mult=args.trail_atr_mult,
        h1_adx_min=args.h1_adx_min,
        atr_ratio_min=args.atr_ratio_min,
    )
    files_by_year = resolve_h4_files(data_dir)

    baseline_reports = {
        year: run_engine(path, params, args, slippage_ticks=args.slippage_ticks)
        for year, path in sorted(files_by_year.items())
    }
    save_formal_reports(baseline_reports, report_dir, params)
    formal_summary = summarize_reports(
        [baseline_reports[year] for year in sorted(baseline_reports)],
        sorted(baseline_reports),
    )

    scenarios = [
        Scenario("base", 1.0, args.slippage_ticks),
        Scenario("spread_1_25x", 1.25, args.slippage_ticks),
        Scenario("spread_1_50x", 1.50, args.slippage_ticks),
        Scenario("slippage_2x", 1.0, args.slippage_ticks * 2.0),
        Scenario("spread_1_50x_slippage_2x", 1.50, args.slippage_ticks * 2.0),
    ]
    stress_rows = build_stress_rows(files_by_year, params, args, scenarios, validation_dir)
    walk_rows = build_walk_forward_rows(baseline_reports, validation_dir)
    write_validation_summary(validation_dir, formal_summary, stress_rows, walk_rows, params)

    print(f"Saved formal reports to {report_dir}")
    print(f"Saved validation outputs to {validation_dir}")
    print(json.dumps(formal_summary, indent=2))


if __name__ == "__main__":
    main()
