from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path
from typing import Any

import pandas as pd

from param_island_v1 import (
    INACTIVE_PERFORMANCE_PARAMS,
    PARAM_SPACE,
    baseline_params,
    boundary_candidates,
    dedupe,
    dedupe_evaluated,
    evaluate_candidates,
    flat_rows,
    island_neighbors,
    param_key,
    random_grid_candidate,
    run_variant,
)

RESULT_ROOT = Path(__file__).resolve().parent / "results_strict_walk_forward"
DEVELOPMENT_YEARS = list(range(2015, 2020))
VALIDATION_YEARS = list(range(2020, 2023))
CONFIRMATION_YEARS = [2023, 2024]
FINAL_HOLDOUT_YEAR = 2025
SEED = 20260611


def selection_row(
    development: dict[str, Any], validation: dict[str, Any]
) -> dict[str, Any]:
    eligible = (
        development["positive_years"] >= 4
        and validation["positive_years"] >= 2
        and development["avg_trades"] >= 15
        and validation["avg_trades"] >= 15
    )
    # The weaker segment dominates; the small average term only breaks close ties.
    selection_score = min(development["score"], validation["score"]) + 0.15 * (
        development["score"] + validation["score"]
    )
    return {
        "eligible": eligible,
        "selection_score": selection_score if eligible else float("-inf"),
        "development": development,
        "validation": validation,
        "params": development["params"],
    }


def flat_selection_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for rank, item in enumerate(rows, start=1):
        dev = item["development"]
        val = item["validation"]
        result.append(
            {
                "rank": rank,
                "eligible": item["eligible"],
                "selection_score": item["selection_score"],
                "development_score": dev["score"],
                "development_avg_return_pct": dev["avg_return_pct"],
                "development_worst_return_pct": dev["worst_return_pct"],
                "development_positive_years": dev["positive_years"],
                "development_avg_dd_pct": dev["avg_max_drawdown_pct"],
                "validation_score": val["score"],
                "validation_avg_return_pct": val["avg_return_pct"],
                "validation_worst_return_pct": val["worst_return_pct"],
                "validation_positive_years": val["positive_years"],
                "validation_avg_dd_pct": val["avg_max_drawdown_pct"],
                **item["params"],
            }
        )
    return result


def write_markdown(result: dict[str, Any]) -> None:
    winner = result["winner"]
    params = winner["params"]
    dev = winner["development"]
    val = winner["validation"]
    confirm = result["confirmation_2023_2024"]
    final = result["final_holdout_2025"]
    lines = [
        "# TP V1 Strict Walk-Forward Result",
        "",
        "No parameter changes are allowed after validation selection inside this run.",
        "",
        "> Research caveat: 2023-2025 had already been observed in an earlier experiment.",
        "> They are isolated from this run's selection code, but are no longer pristine holdouts.",
        "",
        "## Fixed Time Split",
        "",
        "- Development/search: `2015-2019`",
        "- Validation/selection: `2020-2022`",
        "- Untouched confirmation: `2023-2024`",
        "- Untouched final holdout: `2025`",
        "",
        "## Selected Parameters",
        "",
        "```json",
        json.dumps(params, indent=2),
        "```",
        "",
        "## Segment Results",
        "",
        f"- Development average / worst / positive years: `{dev['avg_return_pct']:.4f}%` / "
        f"`{dev['worst_return_pct']:.4f}%` / `{dev['positive_years']}/5`",
        f"- Validation average / worst / positive years: `{val['avg_return_pct']:.4f}%` / "
        f"`{val['worst_return_pct']:.4f}%` / `{val['positive_years']}/3`",
        f"- Confirmation average / worst / positive years: `{confirm['avg_return_pct']:.4f}%` / "
        f"`{confirm['worst_return_pct']:.4f}%` / `{confirm['positive_years']}/2`",
        f"- Final 2025 return / PF / drawdown: `{final['avg_return_pct']:.4f}%` / "
        f"`{final['avg_profit_factor']:.4f}` / `{final['avg_max_drawdown_pct']:.4f}%`",
        "",
        "## Interpretation",
        "",
        "- This run did not use 2023-2025 to generate, filter, rank, or change parameters.",
        "- Because those years were previously observed, passing this test reduces selection bias but is not a clean out-of-sample proof.",
        "- `adx_period`, `atr_pct_window`, and `slope_th_norm` remain excluded because they do not affect trades.",
    ]
    (RESULT_ROOT / "RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="TP v1 strict chronological optimizer")
    parser.add_argument("--workers", type=int, default=max(1, min(os.cpu_count() or 1, 8)))
    parser.add_argument("--broad-candidates", type=int, default=700)
    parser.add_argument("--broad-top", type=int, default=80)
    parser.add_argument("--island-centers", type=int, default=12)
    parser.add_argument("--neighbors-per-center", type=int, default=35)
    parser.add_argument("--boundary-centers", type=int, default=8)
    parser.add_argument("--boundary-random", type=int, default=300)
    parser.add_argument("--validation-candidates", type=int, default=250)
    args = parser.parse_args()

    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    broad = dedupe(
        [baseline_params()]
        + [random_grid_candidate(rng) for _ in range(args.broad_candidates)]
    )
    print(
        f"development broad candidates={len(broad)} years={DEVELOPMENT_YEARS}",
        flush=True,
    )
    broad_dev = evaluate_candidates(broad, DEVELOPMENT_YEARS, args.workers, "dev_broad")
    pd.DataFrame(flat_rows(broad_dev)).to_csv(
        RESULT_ROOT / "stage1_development_broad.csv", index=False
    )

    islands = island_neighbors(
        [item["params"] for item in broad_dev[: args.island_centers]],
        rng,
        args.neighbors_per_center,
    )
    print(
        f"development islands candidates={len(islands)} years={DEVELOPMENT_YEARS}",
        flush=True,
    )
    island_dev = evaluate_candidates(islands, DEVELOPMENT_YEARS, args.workers, "dev_island")
    pd.DataFrame(flat_rows(island_dev)).to_csv(
        RESULT_ROOT / "stage2_development_island.csv", index=False
    )

    dev_combined = dedupe_evaluated(broad_dev[: args.broad_top] + island_dev)
    boundary = boundary_candidates(
        [item["params"] for item in dev_combined[: args.boundary_centers]],
        rng,
        args.boundary_random,
    )
    print(
        f"development boundary candidates={len(boundary)} years={DEVELOPMENT_YEARS}",
        flush=True,
    )
    boundary_dev = evaluate_candidates(
        boundary, DEVELOPMENT_YEARS, args.workers, "dev_boundary"
    )
    pd.DataFrame(flat_rows(boundary_dev)).to_csv(
        RESULT_ROOT / "stage3_development_boundary.csv", index=False
    )

    dev_combined = dedupe_evaluated(dev_combined + boundary_dev)
    validation_params = [
        item["params"] for item in dev_combined[: args.validation_candidates]
    ]
    print(
        f"validation candidates={len(validation_params)} years={VALIDATION_YEARS}",
        flush=True,
    )
    validation = evaluate_candidates(
        validation_params, VALIDATION_YEARS, args.workers, "validation"
    )
    validation_by_key = {param_key(item["params"]): item for item in validation}
    selected = [
        selection_row(dev, validation_by_key[param_key(dev["params"])])
        for dev in dev_combined[: args.validation_candidates]
    ]
    selected.sort(key=lambda item: item["selection_score"], reverse=True)
    pd.DataFrame(flat_selection_rows(selected)).to_csv(
        RESULT_ROOT / "stage4_validation_selection.csv", index=False
    )
    eligible = [item for item in selected if item["eligible"]]
    if not eligible:
        raise RuntimeError("No candidate passed the predeclared eligibility rules.")

    winner = eligible[0]
    confirmation = run_variant(winner["params"], CONFIRMATION_YEARS)
    final_holdout = run_variant(winner["params"], [FINAL_HOLDOUT_YEAR])
    baseline = {
        "development": run_variant(baseline_params(), DEVELOPMENT_YEARS),
        "validation": run_variant(baseline_params(), VALIDATION_YEARS),
        "confirmation_2023_2024": run_variant(baseline_params(), CONFIRMATION_YEARS),
        "final_holdout_2025": run_variant(baseline_params(), [FINAL_HOLDOUT_YEAR]),
    }
    result = {
        "method": {
            "seed": SEED,
            "development_years": DEVELOPMENT_YEARS,
            "validation_years": VALIDATION_YEARS,
            "confirmation_years": CONFIRMATION_YEARS,
            "final_holdout_year": FINAL_HOLDOUT_YEAR,
            "development_broad_candidates": len(broad_dev),
            "development_island_candidates": len(island_dev),
            "development_boundary_candidates": len(boundary_dev),
            "validation_candidates": len(validation),
            "eligibility_rule": "dev positive >=4/5; validation positive >=2/3; "
            "both segments avg trades >=15",
            "selection_rule": "min(dev_score, validation_score) + "
            "0.15*(dev_score + validation_score)",
            "inactive_performance_params": INACTIVE_PERFORMANCE_PARAMS,
        },
        "winner": winner,
        "confirmation_2023_2024": confirmation,
        "final_holdout_2025": final_holdout,
        "baseline": baseline,
        "top_10_validation_selection": selected[:10],
    }
    (RESULT_ROOT / "best_summary.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    write_markdown(result)
    print(
        json.dumps(
            {
                "winner": winner,
                "confirmation_2023_2024": confirmation,
                "final_holdout_2025": final_holdout,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
