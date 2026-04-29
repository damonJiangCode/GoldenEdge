from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.engines.volatility_breakout.v1 import (  # noqa: E402
    EngineConfig,
    VolatilityBreakoutV1Engine,
)


DATA_DIR = PROJECT_ROOT / "data" / "market_data" / "H4"
OUTPUT_DIR = PROJECT_ROOT / "data" / "optimizations" / "volatility_breakout" / "v1" / "H4"


@dataclass(frozen=True)
class ParamSet:
    donchian_breakout_period: int
    donchian_exit_period: int
    sl_atr_mult: float
    trail_atr_mult: float
    h1_adx_min: float
    atr_ratio_min: float


@dataclass(frozen=True)
class Split:
    name: str
    years: tuple[int, ...]


def parse_csv_values(raw: str, cast: type[int] | type[float]) -> list[int] | list[float]:
    values = [item.strip() for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("Grid values cannot be empty.")
    return [cast(value) for value in values]


def parse_years(raw: str) -> tuple[int, ...]:
    years: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start_raw, end_raw = chunk.split("-", 1)
            start = int(start_raw)
            end = int(end_raw)
            if end < start:
                raise ValueError(f"Invalid year range: {chunk}")
            years.extend(range(start, end + 1))
        else:
            years.append(int(chunk))
    if not years:
        raise ValueError("Year split cannot be empty.")
    return tuple(sorted(set(years)))


def year_from_path(path: Path) -> int:
    match = re.search(r"(19|20)\d{2}", path.stem)
    if not match:
        raise ValueError(f"Cannot find year in filename: {path}")
    return int(match.group(0))


def resolve_h4_files(data_dir: Path) -> dict[int, Path]:
    files = {}
    for path in sorted(data_dir.glob("*.csv")):
        files[year_from_path(path)] = path
    if not files:
        raise FileNotFoundError(f"No H4 CSV files found under {data_dir}")
    return files


def run_year(input_file: Path, params: ParamSet, args: argparse.Namespace) -> dict[str, Any]:
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
        slippage_ticks=args.slippage_ticks,
        commission_per_trade=args.commission_per_trade,
        swap_long_per_lot_per_night=args.swap_long_per_lot_per_night,
        swap_short_per_lot_per_night=args.swap_short_per_lot_per_night,
    )
    engine = VolatilityBreakoutV1Engine(config)
    engine.load_data()
    return engine.run()


def summarize_reports(reports: list[dict[str, Any]]) -> dict[str, float | int | str]:
    returns = [float(r["performance"]["return_pct"]) for r in reports]
    pfs = [float(r["performance"]["profit_factor"]) for r in reports]
    dds = [float(r["performance"]["max_drawdown_pct"]) for r in reports]
    trades = [int(r["trades"]) for r in reports]
    win_rates = [float(r["win_rate"]) * 100.0 for r in reports]
    years = [int(year_from_path(Path(r["input_file"]))) for r in reports]

    avg_return = mean(returns)
    avg_pf = mean([pf for pf in pfs if math.isfinite(pf)])
    avg_dd = mean(dds)
    avg_trades = mean(trades)
    pos_years = sum(1 for value in returns if value > 0.0)
    pf_gt_1_years = sum(1 for value in pfs if value > 1.0)
    worst_return = min(returns) if returns else 0.0
    best_return = max(returns) if returns else 0.0
    total_return = sum(returns)
    return_std = stdev(returns)
    best_year_share = best_return / total_return if total_return > 0 and best_return > 0 else 0.0

    return {
        "years": ",".join(str(year) for year in sorted(years)),
        "year_count": len(reports),
        "avg_return_pct": avg_return,
        "total_return_pct": total_return,
        "avg_pf": avg_pf,
        "avg_maxdd_pct": avg_dd,
        "avg_win_rate_pct": mean(win_rates),
        "avg_trades": avg_trades,
        "positive_years": pos_years,
        "pf_gt_1_years": pf_gt_1_years,
        "worst_return_pct": worst_return,
        "best_return_pct": best_return,
        "return_std_pct": return_std,
        "best_year_share": best_year_share,
    }


def mean(values: list[float] | list[int]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    return float(math.sqrt(variance))


def score_row(row: dict[str, Any]) -> float:
    dev = row["dev"]
    val = row["validation"]
    oos = row["oos"]
    full = row["full"]

    score = 0.0
    score += float(oos["avg_return_pct"]) * 1.8
    score += float(val["avg_return_pct"]) * 1.2
    score += float(dev["avg_return_pct"]) * 0.5
    score += min(float(oos["avg_pf"]), 3.0) * 18.0
    score += min(float(val["avg_pf"]), 3.0) * 12.0
    score += int(full["positive_years"]) * 4.0
    score += int(full["pf_gt_1_years"]) * 2.0
    score -= float(full["avg_maxdd_pct"]) * 1.4
    score -= abs(float(oos["avg_return_pct"]) - float(dev["avg_return_pct"])) * 0.25
    score -= max(0.0, float(full["best_year_share"]) - 0.35) * 80.0
    score -= max(0.0, 12.0 - float(full["avg_trades"])) * 3.0

    if float(oos["avg_pf"]) < 1.0:
        score -= 35.0
    if float(val["avg_pf"]) < 1.0:
        score -= 25.0
    if int(oos["positive_years"]) == 0:
        score -= 50.0
    if float(oos["worst_return_pct"]) < -15.0:
        score -= 20.0
    return float(score)


def evaluate_param_set(
    params: ParamSet,
    files_by_year: dict[int, Path],
    full_years: tuple[int, ...],
    splits: tuple[Split, ...],
    args: argparse.Namespace,
) -> dict[str, Any]:
    yearly_reports = {
        year: run_year(files_by_year[year], params, args)
        for year in full_years
    }

    row: dict[str, Any] = {"params": params}
    for split in splits:
        reports = [yearly_reports[year] for year in split.years]
        row[split.name] = summarize_reports(reports)
    row["full"] = summarize_reports([yearly_reports[year] for year in full_years])
    row["score"] = score_row(row)
    return row


def flatten_row(row: dict[str, Any]) -> dict[str, Any]:
    params = asdict(row["params"])
    out: dict[str, Any] = {"rank": row["rank"], "score": round(float(row["score"]), 6), **params}
    for split_name in ("dev", "validation", "oos", "full"):
        for key, value in row[split_name].items():
            if key == "years":
                out[f"{split_name}_{key}"] = value
            elif isinstance(value, float):
                out[f"{split_name}_{key}"] = round(value, 6)
            else:
                out[f"{split_name}_{key}"] = value
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path: Path, rows: list[dict[str, Any]], splits: list[Split], args: argparse.Namespace) -> None:
    top = rows[: args.top_n]
    lines = [
        "# XAUUSD VB/H4 Optimization Summary",
        "",
        f"- Engine: `volatility_breakout/v1`",
        f"- Timeframe: `H4`",
        f"- Dev years: `{splits[0].years}`",
        f"- Validation years: `{splits[1].years}`",
        f"- OOS years: `{splits[2].years}`",
        f"- Grid size: `{len(rows)}`",
        "",
        "## Top Candidates",
        "",
        "| Rank | Score | Params | OOS Avg Ret | OOS PF | Full Avg Ret | Full PF | Full DD | Pos Years | Best Year Share |",
        "| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in top:
        params = row["params"]
        params_text = (
            f"N={params.donchian_breakout_period}, exit={params.donchian_exit_period}, "
            f"SL={params.sl_atr_mult}, trail={params.trail_atr_mult}, "
            f"ADX={params.h1_adx_min}, ATRr={params.atr_ratio_min}"
        )
        lines.append(
            "| "
            f"{row['rank']} | {row['score']:.2f} | `{params_text}` | "
            f"{row['oos']['avg_return_pct']:.2f}% | {row['oos']['avg_pf']:.2f} | "
            f"{row['full']['avg_return_pct']:.2f}% | {row['full']['avg_pf']:.2f} | "
            f"{row['full']['avg_maxdd_pct']:.2f}% | "
            f"{row['full']['positive_years']}/{row['full']['year_count']} | "
            f"{row['full']['best_year_share']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Reading The Score",
            "",
            "The score favors OOS and validation strength, PF, positive-year count, and lower drawdown. It penalizes unstable train/OOS gaps, overdependence on one best year, too few trades, and weak OOS PF.",
            "",
            "Use the top rows as candidates, not as final truth. A robust candidate should have nearby parameter combinations with similar results.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build_param_grid(args: argparse.Namespace) -> list[ParamSet]:
    return [
        ParamSet(
            donchian_breakout_period=n,
            donchian_exit_period=exit_n,
            sl_atr_mult=sl,
            trail_atr_mult=trail,
            h1_adx_min=adx,
            atr_ratio_min=atr_ratio,
        )
        for n, exit_n, sl, trail, adx, atr_ratio in itertools.product(
            parse_csv_values(args.donchian_breakout_periods, int),
            parse_csv_values(args.donchian_exit_periods, int),
            parse_csv_values(args.sl_atr_mults, float),
            parse_csv_values(args.trail_atr_mults, float),
            parse_csv_values(args.h1_adx_mins, float),
            parse_csv_values(args.atr_ratio_mins, float),
        )
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Grid optimize XAUUSD volatility_breakout/v1 on H4 with dev/validation/OOS splits."
    )
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--dev-years", default="2015-2021")
    parser.add_argument("--validation-years", default="2022-2023")
    parser.add_argument("--oos-years", default="2024-2025")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, min(4, (os.cpu_count() or 2) - 1)),
        help="Parallel worker processes. Default: up to 4.",
    )

    parser.add_argument("--donchian-breakout-periods", default="20,35,55")
    parser.add_argument("--donchian-exit-periods", default="10,20")
    parser.add_argument("--sl-atr-mults", default="1.8,2.0,2.2,2.5")
    parser.add_argument("--trail-atr-mults", default="2.5,3.0,3.5,4.0")
    parser.add_argument("--h1-adx-mins", default="18,20,25")
    parser.add_argument("--atr-ratio-mins", default="0.9,1.0,1.1")

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
    output_dir = Path(args.output_dir).expanduser()
    if not data_dir.is_absolute():
        data_dir = (Path.cwd() / data_dir).resolve()
    if not output_dir.is_absolute():
        output_dir = (Path.cwd() / output_dir).resolve()

    files_by_year = resolve_h4_files(data_dir)
    splits = (
        Split("dev", parse_years(args.dev_years)),
        Split("validation", parse_years(args.validation_years)),
        Split("oos", parse_years(args.oos_years)),
    )
    full_years = tuple(sorted(set().union(*(set(split.years) for split in splits))))
    for year in full_years:
        if year not in files_by_year:
            raise FileNotFoundError(f"Missing H4 data for year {year} under {data_dir}")

    param_grid = build_param_grid(args)
    rows: list[dict[str, Any]] = []
    workers = max(1, int(args.workers))

    if workers == 1:
        for idx, params in enumerate(param_grid, start=1):
            row = evaluate_param_set(params, files_by_year, full_years, splits, args)
            rows.append(row)
            if idx == 1 or idx % 25 == 0 or idx == len(param_grid):
                print(f"[{idx}/{len(param_grid)}] evaluated {params}")
    else:
        completed = 0
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(evaluate_param_set, params, files_by_year, full_years, splits, args)
                for params in param_grid
            ]
            for future in as_completed(futures):
                rows.append(future.result())
                completed += 1
                if completed == 1 or completed % 25 == 0 or completed == len(param_grid):
                    print(f"[{completed}/{len(param_grid)}] evaluated")

    rows.sort(key=lambda item: item["score"], reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank

    flat_rows = [flatten_row(row) for row in rows]
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "grid_results.csv", flat_rows)
    write_csv(output_dir / "top_candidates.csv", flat_rows[: args.top_n])
    write_summary(output_dir / "summary.md", rows, list(splits), args)

    config_payload = {
        "splits": {split.name: split.years for split in splits},
        "full_years": full_years,
        "grid_size": len(param_grid),
        "args": vars(args),
    }
    (output_dir / "run_config.json").write_text(
        json.dumps(config_payload, indent=2, default=list),
        encoding="utf-8",
    )
    print(f"Saved optimization outputs to {output_dir}")
    print("Top candidate:")
    print(json.dumps(flat_rows[0], indent=2))


if __name__ == "__main__":
    main()
