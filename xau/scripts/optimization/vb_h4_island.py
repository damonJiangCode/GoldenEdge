from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GRID_SCRIPT = PROJECT_ROOT / "scripts" / "optimization" / "vb_h4_grid.py"
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "optimizations"
    / "volatility_breakout"
    / "v1"
    / "H4_island"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Second-pass parameter-island scan for XAUUSD VB/H4."
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--top-n", type=int, default=50)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))

    parser.add_argument("--dev-years", default="2015-2021")
    parser.add_argument("--validation-years", default="2022-2023")
    parser.add_argument("--oos-years", default="2024-2025")

    parser.add_argument("--donchian-breakout-periods", default="18,20,22,25")
    parser.add_argument("--donchian-exit-periods", default="10,20")
    parser.add_argument("--sl-atr-mults", default="2.0,2.1,2.2,2.3,2.5")
    parser.add_argument("--trail-atr-mults", default="2.8,3.0,3.2,3.5")
    parser.add_argument("--h1-adx-mins", default="16,18,20")
    parser.add_argument("--atr-ratio-mins", default="0.95,1.0,1.05")
    return parser.parse_args()


def run_grid(args: argparse.Namespace) -> None:
    cmd = [
        sys.executable,
        str(GRID_SCRIPT),
        "--workers",
        str(args.workers),
        "--top-n",
        str(args.top_n),
        "--output-dir",
        args.output_dir,
        "--dev-years",
        args.dev_years,
        "--validation-years",
        args.validation_years,
        "--oos-years",
        args.oos_years,
        "--donchian-breakout-periods",
        args.donchian_breakout_periods,
        "--donchian-exit-periods",
        args.donchian_exit_periods,
        "--sl-atr-mults",
        args.sl_atr_mults,
        "--trail-atr-mults",
        args.trail_atr_mults,
        "--h1-adx-mins",
        args.h1_adx_mins,
        "--atr-ratio-mins",
        args.atr_ratio_mins,
    ]
    subprocess.run(cmd, check=True)


def write_island_readme(output_dir: Path) -> None:
    grid_path = output_dir / "grid_results.csv"
    if not grid_path.exists():
        return

    with grid_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    robust = [
        row
        for row in rows
        if int(row["full_positive_years"]) >= 10
        and float(row["oos_avg_pf"]) >= 1.5
        and float(row["validation_avg_pf"]) >= 1.3
        and float(row["full_avg_maxdd_pct"]) <= 12.0
        and float(row["full_avg_trades"]) >= 18.0
    ]

    by_core: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in robust:
        key = (
            row["donchian_breakout_period"],
            row["sl_atr_mult"],
            row["trail_atr_mult"],
            row["atr_ratio_min"],
        )
        by_core.setdefault(key, []).append(row)

    clusters = []
    for key, items in by_core.items():
        clusters.append(
            {
                "key": key,
                "count": len(items),
                "best_rank": min(int(item["rank"]) for item in items),
                "avg_full_return": sum(float(item["full_avg_return_pct"]) for item in items)
                / len(items),
                "avg_full_pf": sum(float(item["full_avg_pf"]) for item in items) / len(items),
                "avg_oos_return": sum(float(item["oos_avg_return_pct"]) for item in items)
                / len(items),
            }
        )
    clusters.sort(key=lambda item: (item["count"], item["avg_full_return"]), reverse=True)

    lines = [
        "# XAUUSD VB/H4 Parameter Island Notes",
        "",
        "This is a second-pass scan around the current VB/H4 baseline and top candidates.",
        "",
        "Robust filter used here:",
        "",
        "- Full positive years >= 10",
        "- OOS average PF >= 1.5",
        "- Validation average PF >= 1.3",
        "- Full average max drawdown <= 12%",
        "- Full average trades >= 18/year",
        "",
        f"Robust rows: `{len(robust)}` / `{len(rows)}`",
        "",
        "## Top Robust Rows",
        "",
        "| Rank | Score | N | Exit | SL | Trail | ADX | ATRr | Full Ret | Full PF | Full DD | Pos Years | OOS Ret |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in robust[:20]:
        lines.append(
            "| "
            f"{row['rank']} | {float(row['score']):.2f} | "
            f"{row['donchian_breakout_period']} | {row['donchian_exit_period']} | "
            f"{row['sl_atr_mult']} | {row['trail_atr_mult']} | "
            f"{row['h1_adx_min']} | {row['atr_ratio_min']} | "
            f"{float(row['full_avg_return_pct']):.2f}% | "
            f"{float(row['full_avg_pf']):.2f} | "
            f"{float(row['full_avg_maxdd_pct']):.2f}% | "
            f"{row['full_positive_years']}/{row['full_year_count']} | "
            f"{float(row['oos_avg_return_pct']):.2f}% |"
        )

    lines.extend(
        [
            "",
            "## Strongest Parameter Clusters",
            "",
            "| Count | Best Rank | N | SL | Trail | ATRr | Avg Full Ret | Avg Full PF | Avg OOS Ret |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for cluster in clusters[:15]:
        n, sl, trail, atrr = cluster["key"]
        lines.append(
            "| "
            f"{cluster['count']} | {cluster['best_rank']} | {n} | {sl} | {trail} | {atrr} | "
            f"{cluster['avg_full_return']:.2f}% | {cluster['avg_full_pf']:.2f} | "
            f"{cluster['avg_oos_return']:.2f}% |"
        )

    (output_dir / "island_notes.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = (Path.cwd() / output_dir).resolve()

    run_grid(args)
    write_island_readme(output_dir)
    print(f"Island notes saved to {output_dir / 'island_notes.md'}")


if __name__ == "__main__":
    main()
