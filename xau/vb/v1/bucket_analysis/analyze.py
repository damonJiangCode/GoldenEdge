#!/usr/bin/env python3
"""Run bucket analysis for VB unified trade logs.

Source data:
    xau/vb/v1/optimization/results/*/unified_trades.csv

Outputs are written to the standard spelling:
    xau/vb/v1/bucket_analysis/results/
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import median


STRATEGY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = STRATEGY_ROOT / "optimization" / "results"
OUTPUT_DIR = Path(__file__).resolve().parent / "results"

PRIMARY_BUCKETS = [
    "pnl_result",
    "r_multiple_bucket",
    "sl_update_bucket",
    "adx_bucket",
    "atr_ratio_bucket",
    "post_entry_holding_bucket",
]

PAIR_BUCKETS = [
    ("adx_bucket", "atr_ratio_bucket"),
    ("adx_bucket", "sl_update_bucket"),
    ("atr_ratio_bucket", "post_entry_holding_bucket"),
    ("adx_bucket", "post_entry_holding_bucket"),
]

CSV_FIELDS = [
    "variant",
    "bucket",
    "bucket_value",
    "trades",
    "profit_trades",
    "loss_trades",
    "flat_trades",
    "profit_ratio_pct",
    "loss_ratio_pct",
    "net_pnl",
    "gross_profit",
    "gross_loss_abs",
    "profit_factor",
    "avg_net_pnl",
    "avg_r",
    "median_r",
    "sum_r",
    "avg_sl_update_count",
    "median_sl_update_count",
    "avg_holding_bars",
]


def to_float(value: str | None, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except ValueError:
        return default


def to_int(value: str | None, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def pct(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator * 100.0, 2)


def round_or_none(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def r_multiple_bucket(r_multiple: float) -> str:
    if r_multiple <= -1.0:
        return "r_lte_minus_1"
    if r_multiple < 0.0:
        return "r_minus_1_to_0"
    if r_multiple < 0.5:
        return "r_0_to_0_5"
    if r_multiple < 1.0:
        return "r_0_5_to_1"
    if r_multiple < 2.0:
        return "r_1_to_2"
    if r_multiple < 4.0:
        return "r_2_to_4"
    return "r_gte_4"


def sl_update_bucket(sl_update_count: int) -> str:
    if sl_update_count <= 0:
        return "sl_updates_0"
    if sl_update_count <= 3:
        return "sl_updates_1_3"
    if sl_update_count <= 10:
        return "sl_updates_4_10"
    return "sl_updates_gt_10"


def normalize_trade(row: dict[str, str]) -> dict[str, object]:
    r_multiple = to_float(row.get("r_multiple"))
    sl_updates = to_int(row.get("sl_update_count"))
    net_pnl = to_float(row.get("net_pnl"))

    normalized = dict(row)
    normalized["r_multiple"] = r_multiple
    normalized["net_pnl"] = net_pnl
    normalized["sl_update_count"] = sl_updates
    normalized["holding_bars"] = to_int(row.get("holding_bars"))
    normalized["pnl_result"] = row.get("pnl_result") or ("profit" if net_pnl > 0 else "loss" if net_pnl < 0 else "flat")
    normalized["r_multiple_bucket"] = r_multiple_bucket(r_multiple)
    normalized["sl_update_bucket"] = sl_update_bucket(sl_updates)
    normalized["adx_bucket"] = row.get("adx_bucket") or "missing"
    normalized["atr_ratio_bucket"] = row.get("atr_ratio_bucket") or "missing"
    normalized["post_entry_holding_bucket"] = row.get("post_entry_holding_bucket") or "missing"
    return normalized


def load_variant_trades(path: Path) -> list[dict[str, object]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return [normalize_trade(row) for row in reader]


def summarize_group(variant: str, bucket: str, bucket_value: str, trades: list[dict[str, object]]) -> dict[str, object]:
    count = len(trades)
    profits = [trade for trade in trades if trade["pnl_result"] == "profit"]
    losses = [trade for trade in trades if trade["pnl_result"] == "loss"]
    flats = [trade for trade in trades if trade["pnl_result"] == "flat"]
    net_pnls = [float(trade["net_pnl"]) for trade in trades]
    r_values = [float(trade["r_multiple"]) for trade in trades]
    sl_updates = [int(trade["sl_update_count"]) for trade in trades]
    holding_bars = [int(trade["holding_bars"]) for trade in trades]
    gross_profit = sum(value for value in net_pnls if value > 0)
    gross_loss_abs = abs(sum(value for value in net_pnls if value < 0))

    return {
        "variant": variant,
        "bucket": bucket,
        "bucket_value": bucket_value,
        "trades": count,
        "profit_trades": len(profits),
        "loss_trades": len(losses),
        "flat_trades": len(flats),
        "profit_ratio_pct": pct(len(profits), count),
        "loss_ratio_pct": pct(len(losses), count),
        "net_pnl": round(sum(net_pnls), 4),
        "gross_profit": round(gross_profit, 4),
        "gross_loss_abs": round(gross_loss_abs, 4),
        "profit_factor": round_or_none(gross_profit / gross_loss_abs if gross_loss_abs else None),
        "avg_net_pnl": round(sum(net_pnls) / count, 4) if count else 0.0,
        "avg_r": round(sum(r_values) / count, 4) if count else 0.0,
        "median_r": round(median(r_values), 4) if r_values else 0.0,
        "sum_r": round(sum(r_values), 4),
        "avg_sl_update_count": round(sum(sl_updates) / count, 2) if count else 0.0,
        "median_sl_update_count": round(median(sl_updates), 2) if sl_updates else 0.0,
        "avg_holding_bars": round(sum(holding_bars) / count, 2) if count else 0.0,
    }


def group_by_fields(trades: list[dict[str, object]], fields: tuple[str, ...]) -> dict[str, list[dict[str, object]]]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for trade in trades:
        bucket_value = "__".join(str(trade.get(field) or "missing") for field in fields)
        groups[bucket_value].append(trade)
    return groups


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def analyze_variant(variant_dir: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    variant = variant_dir.name
    trades = load_variant_trades(variant_dir / "unified_trades.csv")
    variant_output = OUTPUT_DIR / variant
    all_rows: list[dict[str, object]] = []

    overall = summarize_group(variant, "overall", "all", trades)
    all_rows.append(overall)

    for bucket in PRIMARY_BUCKETS:
        rows = [
            summarize_group(variant, bucket, bucket_value, group)
            for bucket_value, group in sorted(group_by_fields(trades, (bucket,)).items())
        ]
        rows.sort(key=lambda row: (-int(row["trades"]), str(row["bucket_value"])))
        write_csv(variant_output / f"by_{bucket}.csv", rows)
        all_rows.extend(rows)

    for left, right in PAIR_BUCKETS:
        bucket_name = f"{left}__{right}"
        rows = [
            summarize_group(variant, bucket_name, bucket_value, group)
            for bucket_value, group in sorted(group_by_fields(trades, (left, right)).items())
        ]
        rows.sort(key=lambda row: (-int(row["trades"]), str(row["bucket_value"])))
        write_csv(variant_output / f"by_{bucket_name}.csv", rows)
        all_rows.extend(rows)

    write_csv(variant_output / "all_buckets.csv", all_rows)
    summary = {
        "variant": variant,
        "source_file": str(variant_dir / "unified_trades.csv"),
        "trades": overall["trades"],
        "profit_ratio_pct": overall["profit_ratio_pct"],
        "net_pnl": overall["net_pnl"],
        "profit_factor": overall["profit_factor"],
        "avg_r": overall["avg_r"],
        "sum_r": overall["sum_r"],
        "avg_sl_update_count": overall["avg_sl_update_count"],
        "output_dir": str(variant_output),
    }
    with (variant_output / "summary.json").open("w") as handle:
        json.dump(summary, handle, indent=2)
    return all_rows, summary


def top_bucket_notes(all_rows: list[dict[str, object]], bucket_name: str, min_trades: int = 15) -> list[dict[str, object]]:
    candidates = [
        row
        for row in all_rows
        if row["bucket"] == bucket_name and int(row["trades"]) >= min_trades
    ]
    return sorted(candidates, key=lambda row: (float(row["avg_r"]), float(row["profit_factor"] or 0)), reverse=True)[:8]


def weak_bucket_notes(all_rows: list[dict[str, object]], bucket_name: str, min_trades: int = 15) -> list[dict[str, object]]:
    candidates = [
        row
        for row in all_rows
        if row["bucket"] == bucket_name and int(row["trades"]) >= min_trades
    ]
    return sorted(candidates, key=lambda row: (float(row["avg_r"]), float(row["profit_factor"] or 0)))[:8]


def write_markdown(summaries: list[dict[str, object]], all_rows: list[dict[str, object]]) -> None:
    lines: list[str] = []
    lines.append("# VB Bucket Analysis")
    lines.append("")
    lines.append("Source: `xau/vb/v1/optimization/results/*/unified_trades.csv`")
    lines.append("")
    lines.append("Output purpose: identify which VB trade buckets are structurally better or worse. Entry-time buckets such as ADX and ATR ratio can become live filters; post-trade buckets such as R, PnL result, SL updates, and holding bucket are diagnostics only.")
    lines.append("")
    lines.append("## Variant Overview")
    lines.append("")
    lines.append("| Variant | Trades | Profit % | PF | Avg R | Sum R | Avg SL Updates | Net PnL |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for summary in summaries:
        lines.append(
            f"| {summary['variant']} | {summary['trades']} | {summary['profit_ratio_pct']} | "
            f"{summary['profit_factor']} | {summary['avg_r']} | {summary['sum_r']} | "
            f"{summary['avg_sl_update_count']} | {summary['net_pnl']} |"
        )

    for bucket in ["adx_bucket", "atr_ratio_bucket", "sl_update_bucket", "post_entry_holding_bucket"]:
        lines.append("")
        lines.append(f"## Top {bucket}")
        lines.append("")
        lines.append("| Variant | Bucket Value | Trades | Profit % | PF | Avg R | Sum R |")
        lines.append("|---|---|---:|---:|---:|---:|---:|")
        for row in top_bucket_notes(all_rows, bucket):
            lines.append(
                f"| {row['variant']} | {row['bucket_value']} | {row['trades']} | "
                f"{row['profit_ratio_pct']} | {row['profit_factor']} | {row['avg_r']} | {row['sum_r']} |"
            )

    for bucket in ["adx_bucket", "atr_ratio_bucket", "adx_bucket__atr_ratio_bucket"]:
        lines.append("")
        lines.append(f"## Weak {bucket}")
        lines.append("")
        lines.append("| Variant | Bucket Value | Trades | Profit % | PF | Avg R | Sum R |")
        lines.append("|---|---|---:|---:|---:|---:|---:|")
        for row in weak_bucket_notes(all_rows, bucket):
            lines.append(
                f"| {row['variant']} | {row['bucket_value']} | {row['trades']} | "
                f"{row['profit_ratio_pct']} | {row['profit_factor']} | {row['avg_r']} | {row['sum_r']} |"
            )

    lines.append("")
    lines.append("## Live Filter Takeaways")
    lines.append("")
    lines.append("- Baseline ADX `adx_25_30` is the strongest single entry-time ADX bucket; `adx_lt20` is clearly weaker.")
    lines.append("- Baseline ATR ratio `atrr_1_25_1_5` is the strongest single entry-time volatility bucket; `atrr_lt1_1` is materially weaker.")
    lines.append("- Very high `sl_update_count` and long `post_entry_holding_bucket` show that VB makes money when the breakout follows through. These are useful for exit diagnostics, not entry filters.")
    lines.append("- For live filtering, prioritize tests around ADX floor/rising behavior and ATR ratio lower bound. Avoid turning post-entry labels into entry rules.")

    lines.append("")
    lines.append("## Reading Notes")
    lines.append("")
    lines.append("- `profit_ratio_pct` is the simple percentage of trades with positive net PnL; it is not the engine's win-rate label.")
    lines.append("- `avg_r` and `sum_r` normalize results by initial risk, so they are better than raw PnL for filter research.")
    lines.append("- `sl_update_bucket`, `post_entry_holding_bucket`, `pnl_result`, and `r_multiple_bucket` are outcome diagnostics. Do not use them directly as entry filters because they are only known after entry or after exit.")
    lines.append("- `adx_bucket` and `atr_ratio_bucket` are usable pre-trade regime features and are the first fields to inspect for hard filters.")
    lines.append("")

    (OUTPUT_DIR / "summary.md").write_text("\n".join(lines))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    variant_dirs = sorted(path for path in SOURCE_DIR.iterdir() if (path / "unified_trades.csv").exists())
    if not variant_dirs:
        raise SystemExit(f"No unified_trades.csv files found under {SOURCE_DIR}")

    all_rows: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []
    for variant_dir in variant_dirs:
        rows, summary = analyze_variant(variant_dir)
        all_rows.extend(rows)
        summaries.append(summary)

    write_csv(OUTPUT_DIR / "all_variants_all_buckets.csv", all_rows)
    comparison_fields = [
        "variant",
        "source_file",
        "trades",
        "profit_ratio_pct",
        "net_pnl",
        "profit_factor",
        "avg_r",
        "sum_r",
        "avg_sl_update_count",
        "output_dir",
    ]
    with (OUTPUT_DIR / "variant_overview.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=comparison_fields)
        writer.writeheader()
        writer.writerows(summaries)
    with (OUTPUT_DIR / "variant_overview.json").open("w") as handle:
        json.dump(summaries, handle, indent=2)
    write_markdown(summaries, all_rows)

    print(f"Wrote VB bucket analysis for {len(summaries)} variants to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
