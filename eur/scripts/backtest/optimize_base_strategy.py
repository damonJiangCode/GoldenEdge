from __future__ import annotations

import argparse
import csv
import itertools
import json
import subprocess
from pathlib import Path
from typing import Any

from EUR_backtesting import EngineConfig, EURSimpleBacktestEngine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "historical"
DEFAULT_RUN_DIR = (
    PROJECT_ROOT / "data" / "backtest_results" / "optimizations" / "2026-02-21-priority0-opt1"
)


def parse_csv_floats(value: str) -> list[float]:
    return [float(v.strip()) for v in value.split(",") if v.strip()]


def parse_rsi_pairs(value: str) -> list[tuple[float, float]]:
    pairs: list[tuple[float, float]] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        ob, os = item.split(":")
        pairs.append((float(ob), float(os)))
    return pairs


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Grid optimization for EUR base strategy with train/validation/test scoring."
    )
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--run-dir", default=str(DEFAULT_RUN_DIR))
    parser.add_argument("--start-year", type=int, default=2017)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--train-end-year", type=int, default=2021)
    parser.add_argument("--validation-end-year", type=int, default=2023)
    parser.add_argument("--initial-balance", type=float, default=1000.0)
    parser.add_argument("--lot-size", type=float, default=0.005)
    parser.add_argument("--contract-size", type=int, default=100000)
    parser.add_argument("--slippage-pips", type=float, default=0.2)
    parser.add_argument("--commission-per-lot-per-side", type=float, default=3.5)
    parser.add_argument("--adx-grid", default="18,20,22")
    parser.add_argument("--rsi-grid", default="68:32,70:30,72:28")
    parser.add_argument("--atr-sl-grid", default="0.8,1.0")
    parser.add_argument("--atr-tp-grid", default="1.6,2.0,2.4")
    parser.add_argument(
        "--confirm-rsi-grid",
        default="false,true",
        help="Comma list from: false,true",
    )
    return parser.parse_args()


def assign_split(year: int, train_end_year: int, validation_end_year: int) -> str:
    if year <= train_end_year:
        return "train"
    if year <= validation_end_year:
        return "validation"
    return "test"


def split_mean(rows: list[dict[str, Any]], split_name: str, key: str) -> float:
    values = [float(r[key]) for r in rows if r["split"] == split_name]
    return float(sum(values) / len(values)) if values else 0.0


def compute_trial_score(rows: list[dict[str, Any]]) -> tuple[float, float]:
    train_return = split_mean(rows, "train", "return_pct")
    val_return = split_mean(rows, "validation", "return_pct")
    test_return = split_mean(rows, "test", "return_pct")
    val_dd = split_mean(rows, "validation", "max_drawdown_pct")
    test_dd = split_mean(rows, "test", "max_drawdown_pct")
    oos_rows = [r for r in rows if r["split"] in {"validation", "test"}]
    oos_consistency = (
        sum(1 for r in oos_rows if float(r["return_pct"]) > 0) / len(oos_rows)
        if oos_rows
        else 0.0
    )

    stability_penalty = abs(train_return - val_return) + abs(val_return - test_return)
    score = (
        0.10 * train_return
        + 0.40 * val_return
        + 0.50 * test_return
        - 0.08 * val_dd
        - 0.12 * test_dd
        + 4.0 * oos_consistency
        - 0.25 * stability_penalty
    )
    return float(score), float(oos_consistency)


def run_single_year(
    year: int,
    input_file: Path,
    shared_args: argparse.Namespace,
    param_set: dict[str, Any],
    train_end_year: int,
    validation_end_year: int,
) -> dict[str, Any]:
    config = EngineConfig(
        input_file=input_file,
        initial_balance=shared_args.initial_balance,
        lot_size=shared_args.lot_size,
        contract_size=shared_args.contract_size,
        slippage_pips=shared_args.slippage_pips,
        commission_per_lot_per_side=shared_args.commission_per_lot_per_side,
        adx_range_threshold=float(param_set["adx_range_threshold"]),
        rsi_overbought=float(param_set["rsi_overbought"]),
        rsi_oversold=float(param_set["rsi_oversold"]),
        atr_sl_mult=float(param_set["atr_sl_mult"]),
        atr_tp_mult=float(param_set["atr_tp_mult"]),
        confirm_use_rsi=bool(param_set["confirm_use_rsi"]),
    )
    engine = EURSimpleBacktestEngine(config)
    engine.load_data()
    report = engine.run()
    performance = report["performance"]
    return {
        "year": year,
        "split": assign_split(year, train_end_year, validation_end_year),
        "return_pct": float(performance["return_pct"]),
        "net_pnl": float(performance["net_pnl"]),
        "max_drawdown_pct": float(performance["max_drawdown_pct"]),
        "profit_factor": float(performance["profit_factor"]),
        "sharpe_per_trade": float(performance["sharpe_per_trade"]),
        "trades": int(report["trades"]),
        "win_rate": float(report["win_rate"]),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    if not (args.start_year <= args.train_end_year <= args.validation_end_year <= args.end_year):
        raise ValueError(
            "Split years must satisfy: start_year <= train_end_year <= validation_end_year <= end_year"
        )

    data_dir = Path(args.data_dir).expanduser().resolve()
    run_dir = Path(args.run_dir).expanduser().resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    trial_dir = run_dir / "trials"
    summary_dir = run_dir / "summary"
    config_dir = run_dir / "config"
    trial_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    years = list(range(args.start_year, args.end_year + 1))
    available_years = [y for y in years if (data_dir / f"M15_{y}.csv").exists()]
    missing_years = [y for y in years if y not in available_years]
    if not available_years:
        raise FileNotFoundError(f"No yearly CSV found under {data_dir}")

    adx_grid = parse_csv_floats(args.adx_grid)
    rsi_grid = parse_rsi_pairs(args.rsi_grid)
    atr_sl_grid = parse_csv_floats(args.atr_sl_grid)
    atr_tp_grid = parse_csv_floats(args.atr_tp_grid)
    confirm_grid = [
        item.strip().lower() == "true"
        for item in args.confirm_rsi_grid.split(",")
        if item.strip()
    ]
    if not confirm_grid:
        raise ValueError("--confirm-rsi-grid produced empty candidates")

    code_version = resolve_code_version(PROJECT_ROOT)
    run_config = {
        "code_version": code_version,
        "data_dir": str(data_dir),
        "run_dir": str(run_dir),
        "years_requested": years,
        "years_available": available_years,
        "years_missing": missing_years,
        "split": {
            "train_years": [args.start_year, args.train_end_year],
            "validation_years": [args.train_end_year + 1, args.validation_end_year],
            "test_years": [args.validation_end_year + 1, args.end_year],
        },
        "base_costs": {
            "initial_balance": args.initial_balance,
            "lot_size": args.lot_size,
            "contract_size": args.contract_size,
            "slippage_pips": args.slippage_pips,
            "commission_per_lot_per_side": args.commission_per_lot_per_side,
        },
        "grid": {
            "adx_range_threshold": adx_grid,
            "rsi_pairs": rsi_grid,
            "atr_sl_mult": atr_sl_grid,
            "atr_tp_mult": atr_tp_grid,
            "confirm_use_rsi": confirm_grid,
        },
        "score_formula": (
            "0.10*train_return + 0.40*val_return + 0.50*test_return "
            "- 0.08*val_dd - 0.12*test_dd + 4.0*oos_consistency "
            "- 0.25*stability_penalty"
        ),
    }
    (config_dir / "run_config.json").write_text(
        json.dumps(run_config, indent=2), encoding="utf-8"
    )

    trial_rows: list[dict[str, Any]] = []
    trial_details: list[dict[str, Any]] = []
    trial_id = 0
    combinations = list(
        itertools.product(adx_grid, rsi_grid, atr_sl_grid, atr_tp_grid, confirm_grid)
    )
    total_trials = len(combinations)

    for adx, (rsi_ob, rsi_os), atr_sl, atr_tp, confirm_rsi in combinations:
        trial_id += 1
        param_set = {
            "adx_range_threshold": adx,
            "rsi_overbought": rsi_ob,
            "rsi_oversold": rsi_os,
            "atr_sl_mult": atr_sl,
            "atr_tp_mult": atr_tp,
            "confirm_use_rsi": confirm_rsi,
        }
        yearly_rows: list[dict[str, Any]] = []
        for year in available_years:
            input_file = data_dir / f"M15_{year}.csv"
            yearly_rows.append(
                run_single_year(
                    year=year,
                    input_file=input_file,
                    shared_args=args,
                    param_set=param_set,
                    train_end_year=args.train_end_year,
                    validation_end_year=args.validation_end_year,
                )
            )

        score, oos_consistency = compute_trial_score(yearly_rows)
        row = {
            "trial_id": trial_id,
            "score": score,
            "oos_consistency": oos_consistency,
            "avg_return_train": split_mean(yearly_rows, "train", "return_pct"),
            "avg_return_validation": split_mean(yearly_rows, "validation", "return_pct"),
            "avg_return_test": split_mean(yearly_rows, "test", "return_pct"),
            "avg_max_dd_validation": split_mean(yearly_rows, "validation", "max_drawdown_pct"),
            "avg_max_dd_test": split_mean(yearly_rows, "test", "max_drawdown_pct"),
            "avg_profit_factor_train": split_mean(yearly_rows, "train", "profit_factor"),
            "avg_profit_factor_validation": split_mean(yearly_rows, "validation", "profit_factor"),
            "avg_profit_factor_test": split_mean(yearly_rows, "test", "profit_factor"),
            "avg_trades_train": split_mean(yearly_rows, "train", "trades"),
            "avg_trades_validation": split_mean(yearly_rows, "validation", "trades"),
            "avg_trades_test": split_mean(yearly_rows, "test", "trades"),
            "adx_range_threshold": adx,
            "rsi_overbought": rsi_ob,
            "rsi_oversold": rsi_os,
            "atr_sl_mult": atr_sl,
            "atr_tp_mult": atr_tp,
            "confirm_use_rsi": confirm_rsi,
        }
        trial_rows.append(row)
        trial_details.append(
            {
                "trial_id": trial_id,
                "params": param_set,
                "score": score,
                "oos_consistency": oos_consistency,
                "yearly_results": yearly_rows,
            }
        )
        print(
            f"[{trial_id}/{total_trials}] score={score:.4f}, "
            f"val={row['avg_return_validation']:.4f}%, test={row['avg_return_test']:.4f}%, "
            f"params={param_set}"
        )

    trial_rows.sort(key=lambda x: float(x["score"]), reverse=True)
    top_10 = trial_rows[:10]
    best = trial_rows[0]
    best_detail = next(d for d in trial_details if int(d["trial_id"]) == int(best["trial_id"]))

    write_csv(trial_dir / "trials_all.csv", trial_rows)
    (trial_dir / "trials_all.json").write_text(
        json.dumps(trial_details, indent=2), encoding="utf-8"
    )
    write_csv(summary_dir / "top10.csv", top_10)
    write_csv(summary_dir / "best_yearly_results.csv", best_detail["yearly_results"])
    (summary_dir / "best_params.json").write_text(
        json.dumps(best, indent=2), encoding="utf-8"
    )
    (summary_dir / "best_trial_detail.json").write_text(
        json.dumps(best_detail, indent=2), encoding="utf-8"
    )
    (summary_dir / "README.md").write_text(
        "\n".join(
            [
                "# EUR Base Strategy Optimization",
                "",
                f"- Code version: `{code_version}`",
                f"- Total trials: {total_trials}",
                f"- Years used: {available_years}",
                f"- Missing years: {missing_years}",
                f"- Best trial id: {int(best['trial_id'])}",
                f"- Best score: {float(best['score']):.6f}",
                f"- Best params: adx={best['adx_range_threshold']}, "
                f"rsi=({best['rsi_overbought']}/{best['rsi_oversold']}), "
                f"atr_sl={best['atr_sl_mult']}, atr_tp={best['atr_tp_mult']}, "
                f"confirm_use_rsi={best['confirm_use_rsi']}",
                "",
                "Files:",
                "- `trials/trials_all.csv`: all parameter sets sorted by score.",
                "- `summary/top10.csv`: top 10 sets.",
                "- `summary/best_yearly_results.csv`: yearly metrics for best set.",
                "- `summary/best_params.json`: best row with split-level aggregates.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Optimization completed. Output folder: {run_dir}")
    print(f"Best trial score: {best['score']:.6f}")
    print(
        "Best params: "
        f"adx={best['adx_range_threshold']}, "
        f"rsi=({best['rsi_overbought']}/{best['rsi_oversold']}), "
        f"atr_sl={best['atr_sl_mult']}, atr_tp={best['atr_tp_mult']}, "
        f"confirm_use_rsi={best['confirm_use_rsi']}"
    )


if __name__ == "__main__":
    main()
