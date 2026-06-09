from __future__ import annotations

import argparse
import json
import os
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xau.scripts.engines.mean_reversion.v1 import (  # noqa: E402
    EngineConfig,
    MeanReversionV1Engine,
)

DATA_ROOT = REPO_ROOT / "xau" / "data" / "optimization" / "mr"
MARKET_ROOT = REPO_ROOT / "xau" / "data" / "market_data" / "M15"
TRAIN_YEARS = list(range(2015, 2025))
HOLDOUT_YEAR = 2025
ANCHOR_YEARS = [2017, 2020, 2024]
SEED = 20260608

PARAM_SPACE: dict[str, list[Any]] = {
    "ema_period": [10, 14, 20, 28, 36, 50],
    "atr_period": [7, 10, 14, 20, 28],
    "band_atr_mult": [1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 3.0],
    "sl_atr_mult": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0],
    "adx_period": [7, 10, 14, 20, 28],
    "h1_adx_limit": [15.0, 18.0, 20.0, 22.0, 25.0, 28.0, 32.0, 40.0],
    "atr_ratio_lookback": [40, 60, 100, 160, 240],
    "atr_ratio_min": [0.5, 0.65, 0.8, 0.9, 1.0, 1.1],
    "atr_ratio_max": [1.1, 1.25, 1.4, 1.6, 2.0, 3.0],
    "wick_body_ratio": [0.0, 0.5, 1.0, 1.5, 2.0, 3.0],
    "fat_tail_body_lookback": [3, 5, 8, 13, 21],
    "fat_tail_body_mult": [1.25, 1.5, 2.0, 2.5, 3.0, 5.0],
    "breakeven_retrace_ratio": [0.0, 0.25, 0.5, 0.75, 1.0, 1.5],
}

EXTENDED_SPACE: dict[str, list[Any]] = {
    "ema_period": [3, 5, 7, 10, 14, 20, 28, 36, 50, 72],
    "atr_period": [3, 5, 7, 10, 14, 20, 28, 40],
    "band_atr_mult": [0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0],
    "sl_atr_mult": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, 8.0, 10.0, 12.0, 16.0],
    "adx_period": [5, 7, 10, 14, 20, 28, 40],
    "h1_adx_limit": [15.0, 20.0, 25.0, 32.0, 40.0, 50.0, 100.0],
    "atr_ratio_lookback": [20, 40, 60, 100, 160, 240, 400],
    "atr_ratio_min": [0.0, 0.1, 0.2, 0.3, 0.5, 0.65, 0.8, 0.9, 1.0, 1.1],
    "atr_ratio_max": [1.1, 1.4, 1.6, 2.0, 3.0, 5.0, 10.0],
    "wick_body_ratio": [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0],
    "fat_tail_body_lookback": [2, 3, 5, 8, 13, 21, 34],
    "fat_tail_body_mult": [1.1, 1.25, 1.5, 2.0, 2.5, 3.0, 5.0, 10.0],
    "breakeven_retrace_ratio": [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0],
}

SESSIONS = [
    (0, 4),
    (0, 6),
    (0, 8),
    (0, 12),
    (0, 16),
    (0, 24),
    (2, 6),
    (2, 8),
    (4, 8),
    (4, 12),
    (6, 12),
    (6, 16),
    (8, 16),
    (8, 20),
    (12, 20),
    (12, 24),
    (16, 24),
]

UNIFIED_COLUMNS = [
    "trade_id", "strategy", "engine_version", "symbol", "timeframe", "side",
    "signal_time_utc", "entry_time_utc", "exit_time_utc", "entry_price",
    "exit_price", "initial_sl", "final_sl", "exit_reason", "gross_pnl",
    "commission", "swap", "net_pnl", "pnl_result", "initial_risk_price",
    "initial_risk_money", "r_multiple", "holding_bars", "holding_hours",
    "entry_atr", "entry_atr_ratio", "entry_spread_points", "entry_adx",
    "entry_h1_adx", "entry_h1_adx_slope", "entry_ema_fast", "entry_ema_slow",
    "entry_ema_slope", "entry_donchian_high", "entry_donchian_low",
    "entry_donchian_width_atr", "entry_bb_width_atr", "entry_close_to_ema_atr",
    "entry_range_efficiency", "regime_trend_strength", "regime_volatility",
    "regime_direction", "regime_strategy_fit", "adx_bucket", "atr_ratio_bucket",
    "spread_bucket", "session_utc", "weekday", "is_win",
    "return_pct_on_initial_balance", "max_favorable_excursion_r",
    "max_adverse_excursion_r", "post_entry_holding_bucket", "sl_update_count",
    "trail_updates_json",
]


def input_file(year: int) -> Path:
    return MARKET_ROOT / f"M15_{year}.csv"


def baseline_params() -> dict[str, Any]:
    cfg = EngineConfig(input_file=input_file(TRAIN_YEARS[0]))
    result = {key: getattr(cfg, key) for key in PARAM_SPACE}
    result["session_start_hour_utc"] = cfg.session_start_hour_utc
    result["session_end_hour_utc"] = cfg.session_end_hour_utc
    return result


def param_key(params: dict[str, Any]) -> str:
    return json.dumps(params, sort_keys=True, separators=(",", ":"))


def random_candidate(rng: random.Random) -> dict[str, Any]:
    params = {key: rng.choice(values) for key, values in PARAM_SPACE.items()}
    while params["atr_ratio_min"] >= params["atr_ratio_max"]:
        params["atr_ratio_min"] = rng.choice(PARAM_SPACE["atr_ratio_min"])
        params["atr_ratio_max"] = rng.choice(PARAM_SPACE["atr_ratio_max"])
    start, end = rng.choice(SESSIONS)
    params["session_start_hour_utc"] = start
    params["session_end_hour_utc"] = end
    return params


def neighbors(center: dict[str, Any], rng: random.Random, count: int) -> list[dict[str, Any]]:
    results = []
    keys = list(PARAM_SPACE)
    for _ in range(count):
        candidate = dict(center)
        for key in rng.sample(keys, k=rng.choice([1, 2, 3, 4])):
            values = PARAM_SPACE[key]
            idx = values.index(candidate[key])
            delta = rng.choice([-2, -1, 1, 2])
            candidate[key] = values[max(0, min(len(values) - 1, idx + delta))]
        if rng.random() < 0.35:
            current = (
                candidate["session_start_hour_utc"],
                candidate["session_end_hour_utc"],
            )
            idx = SESSIONS.index(current)
            idx = max(0, min(len(SESSIONS) - 1, idx + rng.choice([-2, -1, 1, 2])))
            candidate["session_start_hour_utc"], candidate["session_end_hour_utc"] = SESSIONS[idx]
        if candidate["atr_ratio_min"] < candidate["atr_ratio_max"]:
            results.append(candidate)
    return results


def extended_neighbors(
    centers: list[dict[str, Any]], rng: random.Random, count: int
) -> list[dict[str, Any]]:
    results = list(centers)
    keys = list(EXTENDED_SPACE)
    for center in centers[:2]:
        for key, values in EXTENDED_SPACE.items():
            for value in values:
                candidate = dict(center)
                candidate[key] = value
                if candidate["atr_ratio_min"] < candidate["atr_ratio_max"]:
                    results.append(candidate)
    for _ in range(count):
        candidate = dict(rng.choice(centers))
        for key in rng.sample(keys, k=rng.choice([1, 2, 3, 4, 5])):
            values = EXTENDED_SPACE[key]
            current = candidate[key]
            nearest = min(range(len(values)), key=lambda idx: abs(values[idx] - current))
            delta = rng.choice([-3, -2, -1, 1, 2, 3])
            candidate[key] = values[max(0, min(len(values) - 1, nearest + delta))]
        if rng.random() < 0.5:
            candidate["session_start_hour_utc"], candidate["session_end_hour_utc"] = rng.choice(
                SESSIONS
            )
        if candidate["atr_ratio_min"] < candidate["atr_ratio_max"]:
            results.append(candidate)
    return dedupe(results)


def build_config(year: int, params: dict[str, Any]) -> EngineConfig:
    cfg = EngineConfig(input_file=input_file(year))
    for key, value in params.items():
        setattr(cfg, key, value)
    return cfg


def run_one(task: tuple[int, dict[str, Any]]) -> dict[str, Any]:
    year, params = task
    engine = MeanReversionV1Engine(build_config(year, params))
    engine.load_data()
    report = engine.run()
    perf = report["performance"]
    return {
        "year": year,
        "return_pct": float(perf["return_pct"]),
        "profit_factor": float(perf["profit_factor"]),
        "max_drawdown_pct": float(perf["max_drawdown_pct"]),
        "trades": int(report["trades"]),
        "win_rate": float(report["win_rate"]),
    }


def score_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    returns = np.array([row["return_pct"] for row in rows], dtype=float)
    raw_pfs = np.array([row["profit_factor"] for row in rows], dtype=float)
    score_pfs = np.minimum(raw_pfs, 3.0)
    dds = np.array([row["max_drawdown_pct"] for row in rows], dtype=float)
    trades = np.array([row["trades"] for row in rows], dtype=float)
    positive = int(np.sum(returns > 0.0))
    low_trade_penalty = float(np.mean(np.maximum(20.0 - trades, 0.0))) * 0.15
    score = (
        float(np.median(returns))
        + 0.35 * float(np.mean(returns))
        + 0.45 * float(np.min(returns))
        + 0.50 * positive
        + 1.50 * (float(np.mean(score_pfs)) - 1.0)
        - 0.20 * float(np.mean(dds))
        - low_trade_penalty
    )
    return {
        "score": score,
        "avg_return_pct": float(np.mean(returns)),
        "median_return_pct": float(np.median(returns)),
        "worst_return_pct": float(np.min(returns)),
        "avg_profit_factor": float(np.mean(raw_pfs)),
        "avg_max_drawdown_pct": float(np.mean(dds)),
        "positive_years": positive,
        "avg_trades": float(np.mean(trades)),
        "rows": sorted(rows, key=lambda row: row["year"]),
    }


def evaluate_candidates(
    candidates: list[dict[str, Any]],
    years: list[int],
    workers: int,
    stage: str,
) -> list[dict[str, Any]]:
    tasks = [(year, params) for params in candidates for year in years]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        raw = list(pool.map(run_one, tasks, chunksize=1))
    evaluated = []
    width = len(years)
    for idx, params in enumerate(candidates):
        summary = score_rows(raw[idx * width : (idx + 1) * width])
        summary["stage"] = stage
        summary["candidate_id"] = f"{stage}_{idx:04d}"
        summary["params"] = params
        evaluated.append(summary)
    return sorted(evaluated, key=lambda item: item["score"], reverse=True)


def dedupe(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for params in candidates:
        key = param_key(params)
        if key not in seen:
            seen.add(key)
            result.append(params)
    return result


def flat_rows(evaluated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for rank, item in enumerate(evaluated, start=1):
        result.append(
            {
                "rank": rank,
                "candidate_id": item["candidate_id"],
                "stage": item["stage"],
                "score": item["score"],
                "avg_return_pct": item["avg_return_pct"],
                "median_return_pct": item["median_return_pct"],
                "worst_return_pct": item["worst_return_pct"],
                "avg_profit_factor": item["avg_profit_factor"],
                "avg_max_drawdown_pct": item["avg_max_drawdown_pct"],
                "positive_years": item["positive_years"],
                "avg_trades": item["avg_trades"],
                **item["params"],
            }
        )
    return result


def dedupe_evaluated(evaluated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for item in sorted(evaluated, key=lambda row: row["score"], reverse=True):
        key = param_key(item["params"])
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def load_ranked_candidates(path: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(path)
    param_columns = list(PARAM_SPACE) + [
        "session_start_hour_utc",
        "session_end_hour_utc",
    ]
    integer_params = {
        "ema_period",
        "atr_period",
        "adx_period",
        "atr_ratio_lookback",
        "fat_tail_body_lookback",
        "session_start_hour_utc",
        "session_end_hour_utc",
    }
    result = []
    for _, row in df.iterrows():
        params = {
            key: int(row[key]) if key in integer_params else float(row[key])
            for key in param_columns
        }
        result.append(
            {
                "candidate_id": str(row["candidate_id"]),
                "stage": str(row["stage"]),
                "score": float(row["score"]),
                "avg_return_pct": float(row["avg_return_pct"]),
                "median_return_pct": float(row["median_return_pct"]),
                "worst_return_pct": float(row["worst_return_pct"]),
                "avg_profit_factor": float(row["avg_profit_factor"]),
                "avg_max_drawdown_pct": float(row["avg_max_drawdown_pct"]),
                "positive_years": int(row["positive_years"]),
                "avg_trades": float(row["avg_trades"]),
                "params": params,
            }
        )
    return result


def bucket_adx(value: float) -> str:
    return "adx_lt20" if value < 20 else "adx_20_25" if value < 25 else "adx_25_30" if value < 30 else "adx_ge30"


def bucket_atr(value: float) -> str:
    return "atrr_lt1_1" if value < 1.1 else "atrr_1_1_1_25" if value < 1.25 else "atrr_1_25_1_5" if value < 1.5 else "atrr_ge1_5"


def unified_rows(report: dict[str, Any], variant: str) -> list[dict[str, Any]]:
    rows = []
    year = Path(report["input_file"]).stem.split("_")[-1]
    for idx, trade in enumerate(report["trade_details"], start=1):
        entry = pd.Timestamp(trade["entry_time"])
        exit_time = pd.Timestamp(trade["exit_time"])
        spread = float(trade["entry_spread_points"])
        row = {column: "" for column in UNIFIED_COLUMNS}
        row.update(
            {
                "trade_id": f"MR_mean_reversion_v1_{variant}_{year}_{idx:04d}",
                "strategy": "MR",
                "engine_version": "mean_reversion_v1",
                "symbol": "XAUUSD",
                "timeframe": "M15",
                "side": trade["side"],
                "signal_time_utc": trade["signal_time"],
                "entry_time_utc": trade["entry_time"],
                "exit_time_utc": trade["exit_time"],
                "entry_price": trade["entry_price"],
                "exit_price": trade["exit_price"],
                "initial_sl": trade["initial_sl"],
                "final_sl": trade["sl"],
                "exit_reason": trade["exit_reason"],
                "gross_pnl": trade["gross_pnl"],
                "commission": trade["entry_commission"] + trade["exit_commission"],
                "swap": trade["swap_total"],
                "net_pnl": trade["net_pnl"],
                "pnl_result": trade["pnl_result"],
                "initial_risk_price": trade["initial_risk_price"],
                "initial_risk_money": trade["initial_risk_money"],
                "r_multiple": trade["r_multiple"],
                "holding_bars": trade["holding_bars"],
                "holding_hours": (exit_time - entry).total_seconds() / 3600.0,
                "entry_atr": trade["entry_atr"],
                "entry_atr_ratio": trade["entry_atr_ratio"],
                "entry_spread_points": spread,
                "entry_h1_adx": trade["entry_h1_adx"],
                "adx_bucket": bucket_adx(float(trade["entry_h1_adx"])),
                "atr_ratio_bucket": bucket_atr(float(trade["entry_atr_ratio"])),
                "spread_bucket": "spread_le15" if spread <= 15 else "spread_15_30" if spread <= 30 else "spread_gt30",
                "session_utc": f"{entry.hour:02d}:00",
                "weekday": entry.weekday(),
                "is_win": trade["net_pnl"] > 0,
                "return_pct_on_initial_balance": trade["net_pnl"] / report["initial_balance"] * 100.0,
                "post_entry_holding_bucket": "hold_1_7" if trade["holding_bars"] < 8 else "hold_8_24" if trade["holding_bars"] < 25 else "hold_25_plus",
                "sl_update_count": trade["sl_update_count"],
                "trail_updates_json": "[]",
            }
        )
        rows.append(row)
    return rows


def run_full_variant(name: str, params: dict[str, Any], years: list[int]) -> dict[str, Any]:
    reports = []
    trades = []
    for year in years:
        engine = MeanReversionV1Engine(build_config(year, params))
        engine.load_data()
        report = engine.run()
        reports.append(report)
        trades.extend(unified_rows(report, name))
    summary = score_rows(
        [
            {
                "year": year,
                "return_pct": report["performance"]["return_pct"],
                "profit_factor": report["performance"]["profit_factor"],
                "max_drawdown_pct": report["performance"]["max_drawdown_pct"],
                "trades": report["trades"],
                "win_rate": report["win_rate"],
            }
            for year, report in zip(years, reports)
        ]
    )
    summary["params"] = params
    pd.DataFrame(trades, columns=UNIFIED_COLUMNS).to_csv(
        DATA_ROOT / f"unified_trades_{name}.csv", index=False
    )
    return summary


def write_markdown(result: dict[str, Any]) -> None:
    best = result["best_train"]
    holdout = result["holdout_2025"]
    baseline = result["baseline_all"]
    lines = [
        "# MR V1 Param Island Result",
        "",
        "Timeframe: `M15`; train: `2015-2024`; holdout: `2025`.",
        "",
        "## Winner",
        "",
        f"- Train score: `{best['score']:.4f}`",
        f"- Train avg return: `{best['avg_return_pct']:.4f}%`",
        f"- Train positive years: `{best['positive_years']}/10`",
        f"- Train worst year return: `{best['worst_return_pct']:.4f}%`",
        f"- Holdout 2025 return: `{holdout['avg_return_pct']:.4f}%`",
        f"- Holdout 2025 PF: `{holdout['avg_profit_factor']:.4f}`",
        "",
        "```json",
        json.dumps(best["params"], indent=2),
        "```",
        "",
        "## Baseline Comparison",
        "",
        f"- Baseline train avg return: `{baseline['avg_return_pct']:.4f}%`",
        f"- Baseline train positive years: `{baseline['positive_years']}/10`",
        f"- Baseline holdout return: `{result['baseline_holdout']['avg_return_pct']:.4f}%`",
        "",
        "## Island And Risk Notes",
        "",
        "- The leading island is concentrated around `EMA 36`, `ATR 7`, `band 2.25`, `SL 8-10 ATR`, `ADX 28`, and full-day entry.",
        "- The winner uses a wide initial stop and a low win-rate / many-small-loss payoff shape.",
        "- M15 OHLC cannot reproduce tick-level fill ordering. Validate the winner on tick data and harsher execution costs before production use.",
        "",
        "See `top_candidates.csv`, `best_summary.json`, and unified trade CSV files for details.",
    ]
    (DATA_ROOT / "RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="MR v1 robust param-island optimizer")
    parser.add_argument("--workers", type=int, default=max(1, min(os.cpu_count() or 1, 8)))
    parser.add_argument("--random-candidates", type=int, default=420)
    parser.add_argument("--stage2-top", type=int, default=36)
    parser.add_argument("--island-centers", type=int, default=8)
    parser.add_argument("--neighbors-per-center", type=int, default=24)
    parser.add_argument("--boundary-candidates", type=int, default=180)
    parser.add_argument("--resume-boundary", action="store_true")
    args = parser.parse_args()

    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    if args.resume_boundary:
        combined = load_ranked_candidates(DATA_ROOT / "top_candidates.csv")
        stage1_count = len(pd.read_csv(DATA_ROOT / "stage1_broad.csv"))
        stage2_count = len(pd.read_csv(DATA_ROOT / "stage2_full_train.csv"))
        stage3_count = len(pd.read_csv(DATA_ROOT / "stage3_island.csv"))
    else:
        broad = dedupe([baseline_params()] + [random_candidate(rng) for _ in range(args.random_candidates)])
        print(f"stage1 broad candidates={len(broad)} anchors={ANCHOR_YEARS}")
        stage1 = evaluate_candidates(broad, ANCHOR_YEARS, args.workers, "broad")
        pd.DataFrame(flat_rows(stage1)).to_csv(DATA_ROOT / "stage1_broad.csv", index=False)

        stage2_params = [item["params"] for item in stage1[: args.stage2_top]]
        print(f"stage2 candidates={len(stage2_params)} train={TRAIN_YEARS}")
        stage2 = evaluate_candidates(stage2_params, TRAIN_YEARS, args.workers, "full_train")
        pd.DataFrame(flat_rows(stage2)).to_csv(DATA_ROOT / "stage2_full_train.csv", index=False)

        island_params = []
        for center in stage2[: args.island_centers]:
            island_params.append(center["params"])
            island_params.extend(neighbors(center["params"], rng, args.neighbors_per_center))
        island_params = dedupe(island_params)
        print(f"stage3 island candidates={len(island_params)} train={TRAIN_YEARS}")
        stage3 = evaluate_candidates(island_params, TRAIN_YEARS, args.workers, "island")
        pd.DataFrame(flat_rows(stage3)).to_csv(DATA_ROOT / "stage3_island.csv", index=False)
        combined = dedupe_evaluated(stage2 + stage3)

    if args.boundary_candidates >= 0:
        boundary_params = extended_neighbors(
            [item["params"] for item in combined[:8]],
            rng,
            args.boundary_candidates,
        )
        print(f"stage4 boundary candidates={len(boundary_params)} train={TRAIN_YEARS}")
        stage4 = evaluate_candidates(boundary_params, TRAIN_YEARS, args.workers, "boundary")
        pd.DataFrame(flat_rows(stage4)).to_csv(DATA_ROOT / "stage4_boundary.csv", index=False)
    else:
        stage4 = []
    stage4_count = (
        len(stage4)
        if stage4
        else len(pd.read_csv(DATA_ROOT / "stage4_boundary.csv"))
        if (DATA_ROOT / "stage4_boundary.csv").exists()
        else 0
    )

    combined = dedupe_evaluated(combined + stage4)
    pd.DataFrame(flat_rows(combined[:100])).to_csv(DATA_ROOT / "top_candidates.csv", index=False)
    best = combined[0]
    baseline = run_full_variant("baseline", baseline_params(), TRAIN_YEARS)
    baseline_holdout = run_full_variant("baseline_2025", baseline_params(), [HOLDOUT_YEAR])
    best_train = run_full_variant("best_train", best["params"], TRAIN_YEARS)
    holdout = run_full_variant("best_2025", best["params"], [HOLDOUT_YEAR])

    result = {
        "method": {
            "seed": SEED,
            "timeframe": "M15",
            "train_years": TRAIN_YEARS,
            "holdout_year": HOLDOUT_YEAR,
            "anchor_years": ANCHOR_YEARS,
            "stage1_candidates": stage1_count if args.resume_boundary else len(stage1),
            "stage2_candidates": stage2_count if args.resume_boundary else len(stage2),
            "stage3_candidates": stage3_count if args.resume_boundary else len(stage3),
            "stage4_candidates": stage4_count,
            "score_formula": "median_return + .35*avg_return + .45*worst_return + .5*positive_years + 1.5*(avg_pf-1) - .2*avg_dd - low_trade_penalty",
        },
        "best_train": best_train,
        "holdout_2025": holdout,
        "baseline_all": baseline,
        "baseline_holdout": baseline_holdout,
        "top_10": combined[:10],
    }
    (DATA_ROOT / "best_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_markdown(result)
    print(json.dumps({"best_train": best_train, "holdout_2025": holdout}, indent=2))


if __name__ == "__main__":
    main()
