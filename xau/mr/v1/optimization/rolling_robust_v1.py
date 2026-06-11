from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xau.mr.v1.optimization.param_island_v1 import (  # noqa: E402
    baseline_params,
    build_config,
    evaluate_candidates,
    param_key,
    run_one,
    score_rows,
)
from xau.mr.v1.engine import MeanReversionV1Engine  # noqa: E402

DEFAULT_RESULT_ROOT = Path(__file__).resolve().parent / "results_rolling_robust"
SEED = 20260611

FOLDS = [
    {"fold": 1, "train": [2015, 2016, 2017, 2018], "validation": 2019, "test": 2020},
    {"fold": 2, "train": [2016, 2017, 2018, 2019], "validation": 2020, "test": 2021},
    {"fold": 3, "train": [2017, 2018, 2019, 2020], "validation": 2021, "test": 2022},
    {"fold": 4, "train": [2018, 2019, 2020, 2021], "validation": 2022, "test": 2023},
    {"fold": 5, "train": [2019, 2020, 2021, 2022], "validation": 2023, "test": 2024},
    {"fold": 6, "train": [2020, 2021, 2022, 2023], "validation": 2024, "test": 2025},
]

# Fixed before any fold is evaluated. Values are deliberately coarse.
COARSE_SPACE: dict[str, list[Any]] = {
    "ema_period": [7, 14, 20, 36, 50],
    "atr_period": [5, 7, 14, 28],
    "band_atr_mult": [1.0, 1.5, 2.0, 2.25, 2.5, 3.0],
    "sl_atr_mult": [2.0, 4.0, 6.0, 8.0, 10.0, 12.0],
    "adx_period": [7, 14, 28, 40],
    "h1_adx_limit": [20.0, 28.0, 40.0, 100.0],
    "atr_ratio_lookback": [40, 100, 160, 240],
    "atr_ratio_min": [0.0, 0.3, 0.65, 0.9],
    "atr_ratio_max": [1.4, 2.0, 3.0, 5.0],
    "wick_body_ratio": [0.0, 1.0, 1.5, 3.0],
    "fat_tail_body_lookback": [3, 5, 13],
    "fat_tail_body_mult": [1.5, 2.5, 5.0],
    "breakeven_retrace_ratio": [0.0, 0.5, 1.0, 2.0],
}

SESSIONS = [(0, 24), (0, 8), (8, 16), (16, 24), (0, 12), (12, 24)]
INTEGER_PARAMS = {
    "ema_period",
    "atr_period",
    "adx_period",
    "atr_ratio_lookback",
    "fat_tail_body_lookback",
    "session_start_hour_utc",
    "session_end_hour_utc",
}


def valid(params: dict[str, Any]) -> bool:
    return params["atr_ratio_min"] < params["atr_ratio_max"]


def random_center(rng: random.Random) -> dict[str, Any]:
    while True:
        params = {key: rng.choice(values) for key, values in COARSE_SPACE.items()}
        start, end = rng.choice(SESSIONS)
        params["session_start_hour_utc"] = start
        params["session_end_hour_utc"] = end
        if valid(params):
            return params


def one_axis_neighbors(center: dict[str, Any]) -> list[dict[str, Any]]:
    results = [dict(center)]
    for key, values in COARSE_SPACE.items():
        idx = values.index(center[key])
        for delta in (-1, 1):
            next_idx = idx + delta
            if 0 <= next_idx < len(values):
                candidate = dict(center)
                candidate[key] = values[next_idx]
                if valid(candidate):
                    results.append(candidate)
    session = (center["session_start_hour_utc"], center["session_end_hour_utc"])
    session_idx = SESSIONS.index(session)
    for delta in (-1, 1):
        next_idx = session_idx + delta
        if 0 <= next_idx < len(SESSIONS):
            candidate = dict(center)
            candidate["session_start_hour_utc"], candidate["session_end_hour_utc"] = (
                SESSIONS[next_idx]
            )
            results.append(candidate)
    return results


def fixed_candidate_pool(center_count: int) -> tuple[list[dict[str, Any]], dict[str, str]]:
    rng = random.Random(SEED)
    centers = [baseline_params()]
    while len(centers) < center_count:
        candidate = random_center(rng)
        if param_key(candidate) not in {param_key(center) for center in centers}:
            centers.append(candidate)

    candidates: list[dict[str, Any]] = []
    island_by_key: dict[str, str] = {}
    for idx, center in enumerate(centers):
        island_id = f"island_{idx:02d}"
        for candidate in one_axis_neighbors(center):
            key = param_key(candidate)
            if key not in island_by_key:
                candidates.append(candidate)
                island_by_key[key] = island_id
    return candidates, island_by_key


def candidate_pool_rows(
    candidates: list[dict[str, Any]], island_by_key: dict[str, str]
) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": f"fixed_{idx:04d}",
            "island_id": island_by_key[param_key(params)],
            **params,
        }
        for idx, params in enumerate(candidates)
    ]


def robust_fold_rows(
    train_results: list[dict[str, Any]],
    validation_results: list[dict[str, Any]],
    island_by_key: dict[str, str],
    train_year_count: int,
) -> list[dict[str, Any]]:
    validation_by_key = {
        param_key(item["params"]): item for item in validation_results
    }
    train_island_scores: dict[str, list[float]] = {}
    validation_island_scores: dict[str, list[float]] = {}
    for item in train_results:
        island = island_by_key[param_key(item["params"])]
        train_island_scores.setdefault(island, []).append(item["score"])
    for item in validation_results:
        island = island_by_key[param_key(item["params"])]
        validation_island_scores.setdefault(island, []).append(item["score"])

    result = []
    for train in train_results:
        key = param_key(train["params"])
        validation = validation_by_key[key]
        island = island_by_key[key]
        island_train_median = float(np.median(train_island_scores[island]))
        island_validation_median = float(
            np.median(validation_island_scores[island])
        )
        components = [
            train["score"],
            validation["score"],
            island_train_median,
            island_validation_median,
        ]
        eligible = (
            train["positive_years"] >= train_year_count - 1
            and validation["positive_years"] == 1
            and train["avg_trades"] >= 100
            and validation["avg_trades"] >= 100
        )
        robust_score = min(components) + 0.10 * float(np.mean(components))
        result.append(
            {
                "eligible": eligible,
                "robust_score": robust_score if eligible else float("-inf"),
                "island_id": island,
                "train": train,
                "validation": validation,
                "island_train_median_score": island_train_median,
                "island_validation_median_score": island_validation_median,
                "params": train["params"],
            }
        )
    return sorted(result, key=lambda item: item["robust_score"], reverse=True)


def flat_fold_candidates(fold: int, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for rank, item in enumerate(rows, start=1):
        train = item["train"]
        validation = item["validation"]
        result.append(
            {
                "fold": fold,
                "rank": rank,
                "eligible": item["eligible"],
                "robust_score": item["robust_score"],
                "island_id": item["island_id"],
                "train_score": train["score"],
                "train_avg_return_pct": train["avg_return_pct"],
                "train_worst_return_pct": train["worst_return_pct"],
                "train_positive_years": train["positive_years"],
                "train_avg_dd_pct": train["avg_max_drawdown_pct"],
                "validation_score": validation["score"],
                "validation_return_pct": validation["avg_return_pct"],
                "validation_pf": validation["avg_profit_factor"],
                "validation_dd_pct": validation["avg_max_drawdown_pct"],
                "island_train_median_score": item["island_train_median_score"],
                "island_validation_median_score": item[
                    "island_validation_median_score"
                ],
                **item["params"],
            }
        )
    return result


def aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return score_rows(rows)


def selected_frequency_rows(selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    keys = list(COARSE_SPACE) + ["session_start_hour_utc", "session_end_hour_utc"]
    for key in keys:
        counts = Counter(item["params"][key] for item in selected)
        for value, count in counts.most_common():
            rows.append(
                {
                    "parameter": key,
                    "value": value,
                    "selected_folds": count,
                    "share": count / len(selected),
                }
            )
    return rows


def consensus_params(selected_params: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(param_key(params) for params in selected_params)
    winner_key, _ = counts.most_common(1)[0]
    return next(params for params in selected_params if param_key(params) == winner_key)


def run_cost_one(task: tuple[str, int, dict[str, Any], int]) -> dict[str, Any]:
    variant, year, params, multiplier = task
    cfg = build_config(year, params)
    cfg.slippage_ticks *= multiplier
    cfg.commission_per_trade *= multiplier
    engine = MeanReversionV1Engine(cfg)
    engine.load_data()
    report = engine.run()
    perf = report["performance"]
    return {
        "variant": variant,
        "cost_multiplier": multiplier,
        "year": year,
        "return_pct": float(perf["return_pct"]),
        "profit_factor": float(perf["profit_factor"]),
        "max_drawdown_pct": float(perf["max_drawdown_pct"]),
        "trades": int(report["trades"]),
    }


def write_cost_stress(
    result_root: Path, selected_params: list[dict[str, Any]], workers: int
) -> None:
    variants = {
        "rolling_consensus": consensus_params(selected_params),
        "fixed_current_params": baseline_params(),
    }
    tasks = [
        (variant, year, params, multiplier)
        for variant, params in variants.items()
        for multiplier in (1, 2, 3, 5)
        for year in range(2015, 2026)
    ]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(run_cost_one, tasks, chunksize=1))
    pd.DataFrame(rows).to_csv(result_root / "execution_cost_stress_years.csv", index=False)

    summaries = []
    for variant in variants:
        for multiplier in (1, 2, 3, 5):
            group = [
                row
                for row in rows
                if row["variant"] == variant
                and row["cost_multiplier"] == multiplier
            ]
            summary = score_rows(group)
            summaries.append(
                {
                    "variant": variant,
                    "cost_multiplier": multiplier,
                    "avg_return_pct": summary["avg_return_pct"],
                    "worst_return_pct": summary["worst_return_pct"],
                    "positive_years": summary["positive_years"],
                    "avg_profit_factor": summary["avg_profit_factor"],
                    "avg_max_drawdown_pct": summary["avg_max_drawdown_pct"],
                    "avg_trades": summary["avg_trades"],
                }
            )
    pd.DataFrame(summaries).to_csv(
        result_root / "execution_cost_stress_summary.csv", index=False
    )


def write_markdown(result: dict[str, Any], result_root: Path) -> None:
    adaptive = result["adaptive_oos"]
    fixed = result["fixed_current_params_oos"]
    lines = [
        "# MR V1 Rolling Robust Parameter-Island Test",
        "",
        "This is a robustness diagnostic. The historical years were previously observed,",
        "so the OOS labels describe the protocol, not pristine project-level holdouts.",
        f"Current optimized parameter island excluded: "
        f"`{result['method'].get('exclude_current_island', False)}`.",
        "",
        "## Method",
        "",
        "- Six rolling folds use four training years, one validation year, and the next year as OOS test.",
        "- The coarse candidate pool and parameter islands are fixed once before all folds.",
        "- Every fold uses exactly the same candidates, eligibility rule, and score.",
        "- No candidates are created from validation or OOS results.",
        "",
        "## Selection Score",
        "",
        "Base score for a set of years:",
        "",
        "`median_return + 0.35*average_return + 0.45*worst_return + "
        "0.50*positive_years + 1.50*(capped_average_PF-1) - "
        "0.20*average_drawdown - low_trade_penalty`",
        "",
        "Robust fold selection score:",
        "",
        "`min(candidate_train, candidate_validation, island_train_median, "
        "island_validation_median) + 0.10*mean(the four components)`",
        "",
        "Eligibility requires at least `3/4` profitable training years, a profitable",
        "validation year, and at least `100` average trades in both segments.",
        "",
        "## OOS Results",
        "",
        f"- Adaptive rolling OOS average / worst return: `{adaptive['avg_return_pct']:.4f}%` / "
        f"`{adaptive['worst_return_pct']:.4f}%`",
        f"- Adaptive rolling OOS positive years: `{adaptive['positive_years']}/6`",
        f"- Adaptive rolling OOS average PF / drawdown: `{adaptive['avg_profit_factor']:.4f}` / "
        f"`{adaptive['avg_max_drawdown_pct']:.4f}%`",
        f"- Fixed current parameters OOS average / worst return: `{fixed['avg_return_pct']:.4f}%` / "
        f"`{fixed['worst_return_pct']:.4f}%`",
        f"- Fixed current parameters OOS positive years: `{fixed['positive_years']}/6`",
        "",
        "See `fold_summary.csv`, `oos_years.csv`, `fold_candidates.csv`,",
        "`selected_parameter_frequency.csv`, `execution_cost_stress_summary.csv`,",
        "and `best_summary.json`.",
    ]
    (result_root / "RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="MR v1 rolling robust island test")
    parser.add_argument("--workers", type=int, default=max(1, min(os.cpu_count() or 1, 8)))
    parser.add_argument("--island-centers", type=int, default=10)
    parser.add_argument("--exclude-current-island", action="store_true")
    parser.add_argument("--cost-stress-only", action="store_true")
    args = parser.parse_args()

    result_root = (
        Path(__file__).resolve().parent / "results_rolling_robust_no_current_island"
        if args.exclude_current_island
        else DEFAULT_RESULT_ROOT
    )
    result_root.mkdir(parents=True, exist_ok=True)
    if args.cost_stress_only:
        result = json.loads((result_root / "best_summary.json").read_text(encoding="utf-8"))
        write_cost_stress(result_root, result["selected_params"], args.workers)
        print(f"wrote cost stress results to {result_root}", flush=True)
        return

    candidates, island_by_key = fixed_candidate_pool(args.island_centers)
    if args.exclude_current_island:
        candidates = [
            params
            for params in candidates
            if island_by_key[param_key(params)] != "island_00"
        ]
        island_by_key = {
            param_key(params): island_by_key[param_key(params)] for params in candidates
        }
    pd.DataFrame(candidate_pool_rows(candidates, island_by_key)).to_csv(
        result_root / "candidate_pool.csv", index=False
    )
    print(
        f"fixed candidates={len(candidates)} "
        f"islands={len(set(island_by_key.values()))} "
        f"exclude_current_island={args.exclude_current_island}",
        flush=True,
    )

    fold_summary_rows = []
    all_fold_candidates = []
    adaptive_oos_rows = []
    fixed_oos_rows = []
    selected = []
    current_params = baseline_params()

    for fold in FOLDS:
        fold_id = fold["fold"]
        print(
            f"fold={fold_id} train={fold['train']} validation={fold['validation']} "
            f"test={fold['test']}",
            flush=True,
        )
        train_results = evaluate_candidates(
            candidates, fold["train"], args.workers, f"fold{fold_id}_train"
        )
        validation_results = evaluate_candidates(
            candidates, [fold["validation"]], args.workers, f"fold{fold_id}_validation"
        )
        robust_rows = robust_fold_rows(
            train_results, validation_results, island_by_key, len(fold["train"])
        )
        all_fold_candidates.extend(flat_fold_candidates(fold_id, robust_rows))
        eligible = [item for item in robust_rows if item["eligible"]]
        if not eligible:
            raise RuntimeError(f"Fold {fold_id} has no eligible candidates.")
        winner = eligible[0]
        selected.append(winner)

        adaptive_test = run_one((fold["test"], winner["params"]))
        fixed_test = run_one((fold["test"], current_params))
        adaptive_oos_rows.append(adaptive_test)
        fixed_oos_rows.append(fixed_test)
        fold_summary_rows.append(
            {
                "fold": fold_id,
                "train_years": "-".join(str(year) for year in fold["train"]),
                "validation_year": fold["validation"],
                "test_year": fold["test"],
                "eligible_candidates": len(eligible),
                "selected_island": winner["island_id"],
                "robust_score": winner["robust_score"],
                "train_score": winner["train"]["score"],
                "train_avg_return_pct": winner["train"]["avg_return_pct"],
                "train_worst_return_pct": winner["train"]["worst_return_pct"],
                "validation_return_pct": winner["validation"]["avg_return_pct"],
                "validation_pf": winner["validation"]["avg_profit_factor"],
                "test_return_pct": adaptive_test["return_pct"],
                "test_pf": adaptive_test["profit_factor"],
                "test_dd_pct": adaptive_test["max_drawdown_pct"],
                "test_trades": adaptive_test["trades"],
                **winner["params"],
            }
        )

    adaptive_oos = aggregate_rows(adaptive_oos_rows)
    fixed_oos = aggregate_rows(fixed_oos_rows)
    pd.DataFrame(fold_summary_rows).to_csv(result_root / "fold_summary.csv", index=False)
    pd.DataFrame(all_fold_candidates).to_csv(
        result_root / "fold_candidates.csv", index=False
    )
    oos_rows = [
        {"variant": "adaptive_rolling", **row} for row in adaptive_oos_rows
    ] + [{"variant": "fixed_current_params", **row} for row in fixed_oos_rows]
    pd.DataFrame(oos_rows).to_csv(result_root / "oos_years.csv", index=False)
    pd.DataFrame(selected_frequency_rows(selected)).to_csv(
        result_root / "selected_parameter_frequency.csv", index=False
    )

    result = {
        "method": {
            "seed": SEED,
            "folds": FOLDS,
            "candidate_pool_size": len(candidates),
            "island_count": len(set(island_by_key.values())),
            "exclude_current_island": args.exclude_current_island,
            "candidate_pool_rule": "fixed coarse-grid centers plus one-axis immediate neighbors",
            "eligibility_rule": "train positive >=3/4; validation positive; "
            "train and validation average trades >=100",
            "base_score": "median_return + .35*avg_return + .45*worst_return + "
            ".5*positive_years + 1.5*(capped_avg_pf-1) - .2*avg_dd - low_trade_penalty",
            "robust_selection_score": "min(candidate_train, candidate_validation, "
            "island_train_median, island_validation_median) + .10*mean(all four)",
        },
        "adaptive_oos": adaptive_oos,
        "fixed_current_params_oos": fixed_oos,
        "folds": fold_summary_rows,
        "selected_params": [item["params"] for item in selected],
    }
    (result_root / "best_summary.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    write_markdown(result, result_root)
    write_cost_stress(result_root, result["selected_params"], args.workers)
    print(
        json.dumps(
            {
                "adaptive_oos": adaptive_oos,
                "fixed_current_params_oos": fixed_oos,
                "selected_params": result["selected_params"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
