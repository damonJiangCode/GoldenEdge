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

from xau.tp.v1.engine import EngineConfig, TrendPullbackVolFilterV1Engine  # noqa: E402

RESULT_ROOT = Path(__file__).resolve().parent / "results"
MARKET_ROOT = REPO_ROOT / "xau" / "marketdata" / "H1"
TRAIN_YEARS = list(range(2015, 2025))
HOLDOUT_YEAR = 2025
ANCHOR_YEARS = [2017, 2020, 2024]
SEED = 20260611

# These are the only EngineConfig parameters that affect entries or exits.
PARAM_SPACE: dict[str, list[Any]] = {
    "ema_fast_period": [10, 20, 30, 40, 50, 65, 80, 100],
    "ema_slow_period": [80, 120, 160, 200, 260, 320, 400],
    "atr_period": [5, 7, 10, 14, 20, 28, 40],
    "pullback_depth_atr_mult": [0.0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0],
    "atr_sl_mult": [0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0],
    "tp_rr": [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0],
}

BOUNDARY_SPACE: dict[str, list[Any]] = {
    "ema_fast_period": [3, 5, 10, 15, 20, 30, 40, 50, 65, 80, 100, 120, 150],
    "ema_slow_period": [25, 30, 40, 50, 60, 80, 100, 120, 160, 200, 260, 320, 400, 500, 650],
    "atr_period": [3, 5, 7, 10, 14, 20, 28, 40, 60, 80, 100],
    "pullback_depth_atr_mult": [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.25, 1.5],
    "atr_sl_mult": [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0],
    "tp_rr": [0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0],
}

INACTIVE_PERFORMANCE_PARAMS = {
    "adx_period": "used only for regime labels",
    "atr_pct_window": "used only for regime labels",
    "slope_th_norm": "used only for regime labels",
}


def input_file(year: int) -> Path:
    return MARKET_ROOT / f"H1_{year}.csv"


def baseline_params() -> dict[str, Any]:
    cfg = EngineConfig(input_file=input_file(TRAIN_YEARS[0]))
    return {key: getattr(cfg, key) for key in PARAM_SPACE}


def valid(params: dict[str, Any]) -> bool:
    return int(params["ema_fast_period"]) < int(params["ema_slow_period"])


def param_key(params: dict[str, Any]) -> str:
    return json.dumps(params, sort_keys=True, separators=(",", ":"))


def dedupe(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result = []
    for params in candidates:
        key = param_key(params)
        if valid(params) and key not in seen:
            seen.add(key)
            result.append(params)
    return result


def random_grid_candidate(rng: random.Random) -> dict[str, Any]:
    while True:
        params = {key: rng.choice(values) for key, values in PARAM_SPACE.items()}
        if valid(params):
            return params


def nearest_index(values: list[Any], current: Any) -> int:
    return min(range(len(values)), key=lambda idx: abs(values[idx] - current))


def island_neighbors(
    centers: list[dict[str, Any]], rng: random.Random, per_center: int
) -> list[dict[str, Any]]:
    results = list(centers)
    keys = list(PARAM_SPACE)
    for center in centers:
        for key, values in PARAM_SPACE.items():
            idx = nearest_index(values, center[key])
            for delta in (-2, -1, 1, 2):
                candidate = dict(center)
                candidate[key] = values[max(0, min(len(values) - 1, idx + delta))]
                results.append(candidate)
        for _ in range(per_center):
            candidate = dict(center)
            for key in rng.sample(keys, k=rng.choice([2, 3, 4])):
                values = PARAM_SPACE[key]
                idx = nearest_index(values, candidate[key])
                candidate[key] = values[
                    max(0, min(len(values) - 1, idx + rng.choice([-2, -1, 1, 2])))
                ]
            results.append(candidate)
    return dedupe(results)


def boundary_candidates(
    centers: list[dict[str, Any]], rng: random.Random, random_count: int
) -> list[dict[str, Any]]:
    results = list(centers)
    keys = list(BOUNDARY_SPACE)
    for center in centers:
        for key, values in BOUNDARY_SPACE.items():
            for value in values:
                candidate = dict(center)
                candidate[key] = value
                results.append(candidate)
    for _ in range(random_count):
        candidate = dict(rng.choice(centers))
        for key in rng.sample(keys, k=rng.choice([2, 3, 4, 5])):
            values = BOUNDARY_SPACE[key]
            idx = nearest_index(values, candidate[key])
            candidate[key] = values[
                max(0, min(len(values) - 1, idx + rng.choice([-3, -2, -1, 1, 2, 3])))
            ]
        results.append(candidate)
    return dedupe(results)


def build_config(year: int, params: dict[str, Any]) -> EngineConfig:
    cfg = EngineConfig(input_file=input_file(year))
    for key, value in params.items():
        setattr(cfg, key, value)
    return cfg


def run_one(task: tuple[int, dict[str, Any]]) -> dict[str, Any]:
    year, params = task
    engine = TrendPullbackVolFilterV1Engine(build_config(year, params))
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
        "payoff_ratio": float(perf["payoff_ratio"]),
        "avg_holding_bars": float(perf["avg_holding_bars"]),
    }


def score_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    returns = np.array([row["return_pct"] for row in rows], dtype=float)
    raw_pfs = np.array([row["profit_factor"] for row in rows], dtype=float)
    dds = np.array([row["max_drawdown_pct"] for row in rows], dtype=float)
    trades = np.array([row["trades"] for row in rows], dtype=float)
    positive = int(np.sum(returns > 0.0))
    low_trade_penalty = float(np.mean(np.maximum(20.0 - trades, 0.0))) * 0.15
    score = (
        float(np.median(returns))
        + 0.35 * float(np.mean(returns))
        + 0.45 * float(np.min(returns))
        + 0.50 * positive
        + 1.50 * (float(np.mean(np.minimum(raw_pfs, 3.0))) - 1.0)
        - 0.20 * float(np.mean(dds))
        - low_trade_penalty
    )
    return {
        "score": score,
        "avg_return_pct": float(np.mean(returns)),
        "median_return_pct": float(np.median(returns)),
        "worst_return_pct": float(np.min(returns)),
        "return_std_pct": float(np.std(returns)),
        "avg_profit_factor": float(np.mean(raw_pfs)),
        "avg_max_drawdown_pct": float(np.mean(dds)),
        "positive_years": positive,
        "avg_trades": float(np.mean(trades)),
        "rows": sorted(rows, key=lambda row: row["year"]),
    }


def evaluate_candidates(
    candidates: list[dict[str, Any]], years: list[int], workers: int, stage: str
) -> list[dict[str, Any]]:
    tasks = [(year, params) for params in candidates for year in years]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        raw = list(pool.map(run_one, tasks, chunksize=1))
    width = len(years)
    evaluated = []
    for idx, params in enumerate(candidates):
        summary = score_rows(raw[idx * width : (idx + 1) * width])
        summary.update(
            {"stage": stage, "candidate_id": f"{stage}_{idx:04d}", "params": params}
        )
        evaluated.append(summary)
    return sorted(evaluated, key=lambda item: item["score"], reverse=True)


def dedupe_evaluated(evaluated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result = []
    for item in sorted(evaluated, key=lambda row: row["score"], reverse=True):
        key = param_key(item["params"])
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def flat_rows(evaluated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "rank": rank,
            "candidate_id": item["candidate_id"],
            "stage": item["stage"],
            "score": item["score"],
            "avg_return_pct": item["avg_return_pct"],
            "median_return_pct": item["median_return_pct"],
            "worst_return_pct": item["worst_return_pct"],
            "return_std_pct": item["return_std_pct"],
            "avg_profit_factor": item["avg_profit_factor"],
            "avg_max_drawdown_pct": item["avg_max_drawdown_pct"],
            "positive_years": item["positive_years"],
            "avg_trades": item["avg_trades"],
            **item["params"],
        }
        for rank, item in enumerate(evaluated, start=1)
    ]


def load_ranked_candidates(path: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(path)
    integer_params = {"ema_fast_period", "ema_slow_period", "atr_period"}
    result = []
    for _, row in df.iterrows():
        params = {
            key: int(row[key]) if key in integer_params else float(row[key])
            for key in PARAM_SPACE
        }
        result.append(
            {
                "candidate_id": str(row["candidate_id"]),
                "stage": str(row["stage"]),
                "score": float(row["score"]),
                "avg_return_pct": float(row["avg_return_pct"]),
                "median_return_pct": float(row["median_return_pct"]),
                "worst_return_pct": float(row["worst_return_pct"]),
                "return_std_pct": float(row["return_std_pct"]),
                "avg_profit_factor": float(row["avg_profit_factor"]),
                "avg_max_drawdown_pct": float(row["avg_max_drawdown_pct"]),
                "positive_years": int(row["positive_years"]),
                "avg_trades": float(row["avg_trades"]),
                "params": params,
            }
        )
    return result


def run_variant(params: dict[str, Any], years: list[int]) -> dict[str, Any]:
    return score_rows([run_one((year, params)) for year in years])


def sensitivity_rows(evaluated: list[dict[str, Any]], top_n: int = 100) -> list[dict[str, Any]]:
    rows = []
    top = evaluated[:top_n]
    for param in PARAM_SPACE:
        groups: dict[Any, list[dict[str, Any]]] = {}
        for item in top:
            groups.setdefault(item["params"][param], []).append(item)
        for value, items in groups.items():
            rows.append(
                {
                    "parameter": param,
                    "value": value,
                    "candidates": len(items),
                    "avg_score": float(np.mean([item["score"] for item in items])),
                    "best_score": max(item["score"] for item in items),
                    "avg_return_pct": float(
                        np.mean([item["avg_return_pct"] for item in items])
                    ),
                    "avg_positive_years": float(
                        np.mean([item["positive_years"] for item in items])
                    ),
                }
            )
    return rows


def write_markdown(result: dict[str, Any]) -> None:
    best = result["best_train"]
    holdout = result["holdout_2025"]
    baseline = result["baseline_train"]
    baseline_holdout = result["baseline_holdout_2025"]
    params = best["params"]
    lines = [
        "# TP V1 Parameter-Island Grid Test",
        "",
        "Timeframe: `H1`; train: `2015-2024`; untouched holdout: `2025`.",
        "",
        "## Winner",
        "",
        f"- Train score: `{best['score']:.4f}`",
        f"- Train average / median / worst return: `{best['avg_return_pct']:.4f}%` / "
        f"`{best['median_return_pct']:.4f}%` / `{best['worst_return_pct']:.4f}%`",
        f"- Train positive years: `{best['positive_years']}/10`",
        f"- Train average PF / drawdown: `{best['avg_profit_factor']:.4f}` / "
        f"`{best['avg_max_drawdown_pct']:.4f}%`",
        f"- Holdout 2025 return / PF / drawdown: `{holdout['avg_return_pct']:.4f}%` / "
        f"`{holdout['avg_profit_factor']:.4f}` / `{holdout['avg_max_drawdown_pct']:.4f}%`",
        "",
        "```json",
        json.dumps(params, indent=2),
        "```",
        "",
        "## Baseline Comparison",
        "",
        f"- Baseline train average return / positive years: "
        f"`{baseline['avg_return_pct']:.4f}%` / `{baseline['positive_years']}/10`",
        f"- Baseline holdout return / PF: `{baseline_holdout['avg_return_pct']:.4f}%` / "
        f"`{baseline_holdout['avg_profit_factor']:.4f}`",
        "",
        "## Important Engine Finding",
        "",
        "- `adx_period`, `atr_pct_window`, and `slope_th_norm` do not affect entries or exits.",
        "- They only change regime labels, so they were excluded from performance optimization.",
        "- H1 OHLC cannot determine SL/TP ordering inside a bar; the engine conservatively checks SL first.",
        "- The winner's 2025 holdout drawdown is high; treat the parameters as a research winner, not a production risk setting.",
        "",
        "See `best_summary.json`, `top_candidates.csv`, `sensitivity_top100.csv`, "
        "`top20_holdout_diagnostic.csv`, `execution_cost_stress.csv`, and stage CSVs.",
    ]
    (RESULT_ROOT / "RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="TP v1 robust parameter-island grid optimizer")
    parser.add_argument("--workers", type=int, default=max(1, min(os.cpu_count() or 1, 8)))
    parser.add_argument("--broad-candidates", type=int, default=700)
    parser.add_argument("--stage2-top", type=int, default=60)
    parser.add_argument("--island-centers", type=int, default=10)
    parser.add_argument("--neighbors-per-center", type=int, default=30)
    parser.add_argument("--boundary-random", type=int, default=250)
    parser.add_argument("--resume-boundary", action="store_true")
    args = parser.parse_args()

    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    if args.resume_boundary:
        stage1 = load_ranked_candidates(RESULT_ROOT / "stage1_broad_grid.csv")
        stage2 = load_ranked_candidates(RESULT_ROOT / "stage2_full_train.csv")
        stage3 = load_ranked_candidates(RESULT_ROOT / "stage3_island.csv")
        combined = dedupe_evaluated(stage2 + stage3)
    else:
        broad = dedupe(
            [baseline_params()]
            + [random_grid_candidate(rng) for _ in range(args.broad_candidates)]
        )
        print(f"stage1 broad-grid candidates={len(broad)} anchors={ANCHOR_YEARS}", flush=True)
        stage1 = evaluate_candidates(broad, ANCHOR_YEARS, args.workers, "broad_grid")
        pd.DataFrame(flat_rows(stage1)).to_csv(RESULT_ROOT / "stage1_broad_grid.csv", index=False)

        stage2_params = [item["params"] for item in stage1[: args.stage2_top]]
        print(f"stage2 candidates={len(stage2_params)} train={TRAIN_YEARS}", flush=True)
        stage2 = evaluate_candidates(stage2_params, TRAIN_YEARS, args.workers, "full_train")
        pd.DataFrame(flat_rows(stage2)).to_csv(RESULT_ROOT / "stage2_full_train.csv", index=False)

        island = island_neighbors(
            [item["params"] for item in stage2[: args.island_centers]],
            rng,
            args.neighbors_per_center,
        )
        print(f"stage3 island candidates={len(island)} train={TRAIN_YEARS}", flush=True)
        stage3 = evaluate_candidates(island, TRAIN_YEARS, args.workers, "island")
        pd.DataFrame(flat_rows(stage3)).to_csv(RESULT_ROOT / "stage3_island.csv", index=False)

        combined = dedupe_evaluated(stage2 + stage3)
    boundary = boundary_candidates(
        [item["params"] for item in combined[:5]], rng, args.boundary_random
    )
    print(f"stage4 boundary candidates={len(boundary)} train={TRAIN_YEARS}", flush=True)
    stage4 = evaluate_candidates(boundary, TRAIN_YEARS, args.workers, "boundary")
    pd.DataFrame(flat_rows(stage4)).to_csv(RESULT_ROOT / "stage4_boundary.csv", index=False)

    combined = dedupe_evaluated(combined + stage4)
    pd.DataFrame(flat_rows(combined[:100])).to_csv(
        RESULT_ROOT / "top_candidates.csv", index=False
    )
    pd.DataFrame(sensitivity_rows(combined)).to_csv(
        RESULT_ROOT / "sensitivity_top100.csv", index=False
    )

    best = combined[0]
    best_train = run_variant(best["params"], TRAIN_YEARS)
    best_train["params"] = best["params"]
    holdout = run_variant(best["params"], [HOLDOUT_YEAR])
    baseline_train = run_variant(baseline_params(), TRAIN_YEARS)
    baseline_holdout = run_variant(baseline_params(), [HOLDOUT_YEAR])
    result = {
        "method": {
            "seed": SEED,
            "timeframe": "H1",
            "train_years": TRAIN_YEARS,
            "holdout_year": HOLDOUT_YEAR,
            "anchor_years": ANCHOR_YEARS,
            "stage1_candidates": len(stage1),
            "stage2_candidates": len(stage2),
            "stage3_candidates": len(stage3),
            "stage4_candidates": len(stage4),
            "inactive_performance_params": INACTIVE_PERFORMANCE_PARAMS,
            "score_formula": "median_return + .35*avg_return + .45*worst_return + "
            ".5*positive_years + 1.5*(capped_avg_pf-1) - .2*avg_dd - low_trade_penalty",
        },
        "best_train": best_train,
        "holdout_2025": holdout,
        "baseline_train": baseline_train,
        "baseline_holdout_2025": baseline_holdout,
        "top_10": combined[:10],
    }
    (RESULT_ROOT / "best_summary.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    write_markdown(result)
    print(json.dumps({"best_train": best_train, "holdout_2025": holdout}, indent=2))


if __name__ == "__main__":
    main()
