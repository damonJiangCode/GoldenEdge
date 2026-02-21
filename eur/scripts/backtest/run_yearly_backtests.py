from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path
from typing import Any

from EUR_backtesting import EngineConfig, EURSimpleBacktestEngine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "historical"
DEFAULT_RUN_DIR = PROJECT_ROOT / "data" / "backtest_results" / "runs" / "2026-02-21-base"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run EUR M15 base strategy backtests year by year."
    )
    parser.add_argument("--start-year", type=int, default=2017)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument(
        "--train-end-year",
        type=int,
        default=2021,
        help="Train set ends at this year (inclusive).",
    )
    parser.add_argument(
        "--validation-end-year",
        type=int,
        default=2023,
        help="Validation set ends at this year (inclusive).",
    )
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--run-dir", default=str(DEFAULT_RUN_DIR))
    parser.add_argument("--initial-balance", type=float, default=1000.0)
    parser.add_argument("--lot-size", type=float, default=0.005)
    parser.add_argument("--contract-size", type=int, default=100000)
    parser.add_argument("--slippage-pips", type=float, default=0.2)
    parser.add_argument("--commission-per-lot-per-side", type=float, default=3.5)
    parser.add_argument(
        "--confirm-use-rsi",
        action="store_true",
        help="Use RSI direction as an extra confirmation filter.",
    )
    return parser.parse_args()


def ensure_dirs(run_dir: Path) -> dict[str, Path]:
    reports_dir = run_dir / "reports"
    summary_dir = run_dir / "summary"
    config_dir = run_dir / "config"
    reports_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    return {"reports": reports_dir, "summary": summary_dir, "config": config_dir}


def resolve_code_version(project_root: Path) -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=project_root, text=True
            )
            .strip()
        )
    except Exception:
        return "unknown"


def assign_split(year: int, train_end_year: int, validation_end_year: int) -> str:
    if year <= train_end_year:
        return "train"
    if year <= validation_end_year:
        return "validation"
    return "test"


def as_summary_row(year: int, split: str, report: dict[str, Any]) -> dict[str, Any]:
    initial_balance = float(report["initial_balance"])
    final_balance = float(report["final_balance"])
    net_pnl = final_balance - initial_balance
    return {
        "year": year,
        "split": split,
        "input_file": report["input_file"],
        "bars": int(report["bars"]),
        "time_start_utc": report["time_start_utc"],
        "time_end_utc": report["time_end_utc"],
        "initial_balance": initial_balance,
        "final_balance": final_balance,
        "net_pnl": net_pnl,
        "return_pct": (net_pnl / initial_balance) * 100.0 if initial_balance else 0.0,
        "trades": int(report["trades"]),
        "win_rate": float(report["win_rate"]),
        "profit_factor": float(report["performance"]["profit_factor"]),
        "sharpe_per_trade": float(report["performance"]["sharpe_per_trade"]),
        "max_drawdown_pct": float(report["performance"]["max_drawdown_pct"]),
        "spread_mean_points": float(report["costs"]["spread_mean_points"]),
        "slippage_pips": float(report["costs"]["slippage_pips"]),
        "commission_per_lot_per_side": float(
            report["costs"]["commission_per_lot_per_side"]
        ),
        "confirm_use_rsi": bool(report["params"]["confirm_use_rsi"]),
    }


def write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "year",
        "split",
        "input_file",
        "bars",
        "time_start_utc",
        "time_end_utc",
        "initial_balance",
        "final_balance",
        "net_pnl",
        "return_pct",
        "trades",
        "win_rate",
        "profit_factor",
        "sharpe_per_trade",
        "max_drawdown_pct",
        "spread_mean_points",
        "slippage_pips",
        "commission_per_lot_per_side",
        "confirm_use_rsi",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary_readme(path: Path, rows: list[dict[str, Any]], run_dir: Path) -> None:
    if not rows:
        content = "# EUR Yearly Backtest Summary\n\nNo reports generated.\n"
        path.write_text(content, encoding="utf-8")
        return

    best = max(rows, key=lambda r: float(r["return_pct"]))
    worst = min(rows, key=lambda r: float(r["return_pct"]))
    total_net = sum(float(r["net_pnl"]) for r in rows)
    avg_return = sum(float(r["return_pct"]) for r in rows) / len(rows)
    oos_rows = [r for r in rows if r["split"] in {"validation", "test"}]
    oos_consistency = (
        sum(1 for r in oos_rows if float(r["return_pct"]) > 0) / len(oos_rows)
        if oos_rows
        else 0.0
    )

    lines = [
        "# EUR Yearly Backtest Summary",
        "",
        f"- Run folder: `{run_dir}`",
        f"- Years: {rows[0]['year']} to {rows[-1]['year']}",
        f"- Reports generated: {len(rows)}",
        f"- Total net PnL: {total_net:.6f}",
        f"- Average yearly return: {avg_return:.4f}%",
        f"- OOS consistency (validation+test positive years): {oos_consistency:.2%}",
        f"- Best year: {best['year']} ({float(best['return_pct']):.4f}%)",
        f"- Worst year: {worst['year']} ({float(worst['return_pct']):.4f}%)",
        "",
        "See `yearly_summary.csv` and `yearly_summary.json` for details.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.start_year > args.end_year:
        raise ValueError("--start-year must be <= --end-year")
    if not (args.start_year <= args.train_end_year <= args.validation_end_year <= args.end_year):
        raise ValueError(
            "Split years must satisfy: start_year <= train_end_year <= validation_end_year <= end_year"
        )

    data_dir = Path(args.data_dir).expanduser().resolve()
    run_dir = Path(args.run_dir).expanduser().resolve()
    dirs = ensure_dirs(run_dir)
    code_version = resolve_code_version(PROJECT_ROOT)

    years = list(range(args.start_year, args.end_year + 1))
    summary_rows: list[dict[str, Any]] = []
    missing_files: list[str] = []

    run_config = {
        "engine": "eur_simple_adx_bb_rsi_atr",
        "data_dir": str(data_dir),
        "run_dir": str(run_dir),
        "start_year": args.start_year,
        "end_year": args.end_year,
        "code_version": code_version,
        "split": {
            "train_years": [args.start_year, args.train_end_year],
            "validation_years": [args.train_end_year + 1, args.validation_end_year],
            "test_years": [args.validation_end_year + 1, args.end_year],
        },
        "params": {
            "initial_balance": args.initial_balance,
            "lot_size": args.lot_size,
            "contract_size": args.contract_size,
            "slippage_pips": args.slippage_pips,
            "commission_per_lot_per_side": args.commission_per_lot_per_side,
            "confirm_use_rsi": bool(args.confirm_use_rsi),
        },
    }
    (dirs["config"] / "run_config.json").write_text(
        json.dumps(run_config, indent=2), encoding="utf-8"
    )

    for year in years:
        input_file = data_dir / f"M15_{year}.csv"
        if not input_file.exists():
            missing_files.append(str(input_file))
            continue

        config = EngineConfig(
            input_file=input_file,
            initial_balance=args.initial_balance,
            lot_size=args.lot_size,
            contract_size=args.contract_size,
            slippage_pips=args.slippage_pips,
            commission_per_lot_per_side=args.commission_per_lot_per_side,
            confirm_use_rsi=args.confirm_use_rsi,
        )

        engine = EURSimpleBacktestEngine(config)
        engine.load_data()
        report = engine.run()
        report["dataset_split"] = assign_split(
            year, args.train_end_year, args.validation_end_year
        )
        report["code_version"] = code_version

        report_path = dirs["reports"] / f"EUR_M15_{year}_report.json"
        engine.save_report(report, output_path=report_path)
        summary_rows.append(
            as_summary_row(
                year,
                report["dataset_split"],
                report,
            )
        )
        print(
            f"[{year}] split={report['dataset_split']}, "
            f"return={report['performance']['return_pct']:.4f}%, "
            f"max_dd={report['performance']['max_drawdown_pct']:.4f}%, "
            f"trades={report['trades']}"
        )

    summary_rows.sort(key=lambda r: int(r["year"]))
    oos_rows = [r for r in summary_rows if r["split"] in {"validation", "test"}]
    oos_consistency = (
        sum(1 for r in oos_rows if float(r["return_pct"]) > 0) / len(oos_rows)
        if oos_rows
        else 0.0
    )
    summary_json = {
        "run_dir": str(run_dir),
        "code_version": code_version,
        "years_requested": years,
        "years_completed": [int(r["year"]) for r in summary_rows],
        "missing_files": missing_files,
        "data_split": {
            "train_years": [args.start_year, args.train_end_year],
            "validation_years": [args.train_end_year + 1, args.validation_end_year],
            "test_years": [args.validation_end_year + 1, args.end_year],
        },
        "aggregate": {
            "total_net_pnl": float(sum(float(r["net_pnl"]) for r in summary_rows)),
            "avg_return_pct": float(
                sum(float(r["return_pct"]) for r in summary_rows) / len(summary_rows)
            )
            if summary_rows
            else 0.0,
            "oos_consistency": float(oos_consistency),
        },
        "results": summary_rows,
    }

    (dirs["summary"] / "yearly_summary.json").write_text(
        json.dumps(summary_json, indent=2), encoding="utf-8"
    )
    write_summary_csv(dirs["summary"] / "yearly_summary.csv", summary_rows)
    write_summary_readme(dirs["summary"] / "README.md", summary_rows, run_dir)

    print(f"Run completed. Output folder: {run_dir}")
    print(f"Reports: {dirs['reports']}")
    print(f"Summary: {dirs['summary']}")
    if missing_files:
        print("Missing input files:")
        for m in missing_files:
            print(f"- {m}")


if __name__ == "__main__":
    main()
