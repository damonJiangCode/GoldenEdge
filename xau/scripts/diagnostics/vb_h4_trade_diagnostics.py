from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
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
OUTPUT_DIR = PROJECT_ROOT / "data" / "diagnostics" / "volatility_breakout" / "v1_h4_candidate"


@dataclass(frozen=True)
class CandidateParams:
    donchian_breakout_period: int = 18
    donchian_exit_period: int = 10
    sl_atr_mult: float = 2.2
    trail_atr_mult: float = 3.2
    h1_adx_min: float = 18.0
    atr_ratio_min: float = 1.0


def mean(values: list[float] | list[int]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    return float(math.sqrt(variance))


def profit_factor(pnls: list[float]) -> float:
    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = -sum(pnl for pnl in pnls if pnl < 0)
    if gross_loss > 0:
        return gross_profit / gross_loss
    return float("inf") if gross_profit > 0 else 0.0


def parse_time(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def year_from_path(path: Path) -> int:
    match = re.search(r"(19|20)\d{2}", path.stem)
    if not match:
        raise ValueError(f"Cannot find year in filename: {path}")
    return int(match.group(0))


def resolve_h4_files(data_dir: Path) -> list[Path]:
    files = sorted(data_dir.glob("*.csv"), key=year_from_path)
    if not files:
        raise FileNotFoundError(f"No H4 CSV files found under {data_dir}")
    return files


def combine_h4_files(files: list[Path], output_path: Path) -> pd.DataFrame:
    frames = []
    for path in files:
        df = pd.read_csv(path)
        df["source_year"] = year_from_path(path)
        frames.append(df)
    combined = pd.concat(frames, ignore_index=True)
    combined["time"] = pd.to_datetime(combined["time"], utc=True)
    combined.sort_values("time", inplace=True)
    combined.drop_duplicates(subset=["time"], inplace=True)
    combined.to_csv(output_path, index=False)
    return combined


def run_engine(input_file: Path, params: CandidateParams, args: argparse.Namespace) -> dict[str, Any]:
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


def enrich_trades(report: dict[str, Any], params: CandidateParams, args: argparse.Namespace) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    units = args.lot_size * args.contract_size
    for idx, trade in enumerate(report.get("trade_details", []), start=1):
        pnl = float(trade["net_pnl"])
        entry_atr = float(trade["entry_atr"])
        initial_risk = max(params.sl_atr_mult * entry_atr * units, 1e-9)
        entry_time = parse_time(str(trade["entry_time"]))
        exit_time = parse_time(str(trade["exit_time"]))
        holding_bars = int(trade["holding_bars"])
        rows.append(
            {
                "trade_id": idx,
                "side": str(trade["side"]),
                "signal_time": trade["signal_time"],
                "entry_time": trade["entry_time"],
                "exit_time": trade["exit_time"],
                "exit_year": exit_time.year,
                "exit_quarter": f"{exit_time.year}Q{((exit_time.month - 1) // 3) + 1}",
                "entry_price": float(trade["entry_price"]),
                "exit_price": float(trade["exit_price"]),
                "exit_reason": str(trade["exit_reason"]),
                "net_pnl": pnl,
                "trade_return_pct_initial_balance": pnl / args.initial_balance * 100.0,
                "r_multiple": pnl / initial_risk,
                "holding_bars": holding_bars,
                "holding_days": (exit_time - entry_time).total_seconds() / 86400.0,
                "entry_atr": entry_atr,
                "entry_atr_ratio": float(trade["entry_atr_ratio"]),
                "entry_h1_adx": float(trade["entry_h1_adx"]),
                "gross_pnl": float(trade["gross_pnl"]),
                "swap_total": float(trade["swap_total"]),
                "total_commission": float(trade["entry_commission"]) + float(trade["exit_commission"]),
                "equity_after": float(trade["equity_after"]),
            }
        )
    return rows


def trade_metrics(trades: list[dict[str, Any]]) -> dict[str, float | int]:
    pnls = [float(t["net_pnl"]) for t in trades]
    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [pnl for pnl in pnls if pnl < 0]
    avg_win = mean(wins)
    avg_loss = mean(losses)
    return {
        "trades": len(pnls),
        "win_rate_pct": len(wins) / len(pnls) * 100.0 if pnls else 0.0,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "payoff_ratio": avg_win / abs(avg_loss) if avg_loss < 0 else 0.0,
        "profit_factor": profit_factor(pnls),
        "expectancy": mean(pnls),
        "sharpe_per_trade": mean(pnls) / stdev(pnls) if stdev(pnls) > 0 else 0.0,
        "avg_r_multiple": mean([float(t["r_multiple"]) for t in trades]),
        "avg_holding_bars": mean([int(t["holding_bars"]) for t in trades]),
        "avg_holding_days": mean([float(t["holding_days"]) for t in trades]),
        "net_pnl": sum(pnls),
    }


def bucket_holding(bars: int) -> str:
    if bars <= 3:
        return "01_1-3_bars"
    if bars <= 6:
        return "02_4-6_bars"
    if bars <= 12:
        return "03_7-12_bars"
    if bars <= 24:
        return "04_13-24_bars"
    return "05_25_plus_bars"


def bucket_adx(value: float) -> str:
    if value < 20:
        return "01_adx_18-20"
    if value < 25:
        return "02_adx_20-25"
    if value < 30:
        return "03_adx_25-30"
    return "04_adx_30_plus"


def bucket_atr_ratio(value: float) -> str:
    if value < 1.1:
        return "01_atrr_1.0-1.1"
    if value < 1.25:
        return "02_atrr_1.1-1.25"
    if value < 1.5:
        return "03_atrr_1.25-1.5"
    return "04_atrr_1.5_plus"


def add_buckets(trades: list[dict[str, Any]]) -> None:
    for trade in trades:
        trade["holding_bucket"] = bucket_holding(int(trade["holding_bars"]))
        trade["adx_bucket"] = bucket_adx(float(trade["entry_h1_adx"]))
        trade["atr_ratio_bucket"] = bucket_atr_ratio(float(trade["entry_atr_ratio"]))
        trade["pnl_sign"] = "win" if float(trade["net_pnl"]) > 0 else "loss"


def group_summary(trades: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for trade in trades:
        groups.setdefault(str(trade[key]), []).append(trade)
    rows = []
    for name, items in sorted(groups.items()):
        pnls = [float(t["net_pnl"]) for t in items]
        wins = [pnl for pnl in pnls if pnl > 0]
        losses = [pnl for pnl in pnls if pnl < 0]
        rows.append(
            {
                key: name,
                "trades": len(items),
                "win_rate_pct": round(len(wins) / len(items) * 100.0, 6) if items else 0.0,
                "net_pnl": round(sum(pnls), 6),
                "avg_pnl": round(mean(pnls), 6),
                "avg_r": round(mean([float(t["r_multiple"]) for t in items]), 6),
                "avg_win": round(mean(wins), 6),
                "avg_loss": round(mean(losses), 6),
                "profit_factor": round(profit_factor(pnls), 6),
                "avg_holding_bars": round(mean([int(t["holding_bars"]) for t in items]), 6),
                "avg_holding_days": round(mean([float(t["holding_days"]) for t in items]), 6),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def pct_drawdown(equity: list[float]) -> list[float]:
    out = []
    peak = equity[0] if equity else 0.0
    for value in equity:
        peak = max(peak, value)
        out.append((value - peak) / peak * 100.0 if peak else 0.0)
    return out


def rolling_sharpe(values: list[float], window: int) -> list[float]:
    out = []
    for idx in range(len(values)):
        sample = values[max(0, idx - window + 1) : idx + 1]
        sd = stdev(sample)
        out.append(mean(sample) / sd if len(sample) >= 2 and sd > 0 else 0.0)
    return out


def scale_points(values: list[float], width: int, height: int, pad: int, invert: bool = True) -> list[tuple[float, float]]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if math.isclose(lo, hi):
        hi = lo + 1.0
    points = []
    denom = max(len(values) - 1, 1)
    for idx, value in enumerate(values):
        x = pad + idx / denom * (width - 2 * pad)
        ratio = (value - lo) / (hi - lo)
        y = pad + (1 - ratio if invert else ratio) * (height - 2 * pad)
        points.append((x, y))
    return points


def polyline(points: list[tuple[float, float]], color: str, width: float = 2.0) -> str:
    raw = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f'<polyline points="{raw}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round" />'


def svg_header(title: str, width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff" />',
        f'<text x="24" y="32" font-family="Arial" font-size="18" font-weight="700" fill="#111827">{html.escape(title)}</text>',
    ]


def write_line_svg(path: Path, title: str, labels: list[str], series: list[tuple[str, list[float], str]]) -> None:
    width, height, pad = 1100, 460, 56
    lines = svg_header(title, width, height)
    lines.append(f'<line x1="{pad}" y1="{height-pad}" x2="{width-pad}" y2="{height-pad}" stroke="#d1d5db" />')
    lines.append(f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height-pad}" stroke="#d1d5db" />')
    for name, values, color in series:
        points = scale_points(values, width, height, pad)
        lines.append(polyline(points, color))
        lines.append(f'<text x="{width-pad-180}" y="{60 + 20 * series.index((name, values, color))}" font-family="Arial" font-size="13" fill="{color}">{html.escape(name)}</text>')
    if labels:
        lines.append(f'<text x="{pad}" y="{height-18}" font-family="Arial" font-size="12" fill="#6b7280">{html.escape(labels[0])}</text>')
        lines.append(f'<text x="{width-pad-120}" y="{height-18}" font-family="Arial" font-size="12" fill="#6b7280">{html.escape(labels[-1])}</text>')
    lines.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_overlay_svg(path: Path, equity_df: pd.DataFrame, price_df: pd.DataFrame, trades: list[dict[str, Any]]) -> None:
    width, height, pad = 1200, 560, 62
    price = price_df["close"].astype(float).tolist()
    equity = equity_df["equity"].astype(float).tolist()
    labels = equity_df["time"].dt.strftime("%Y-%m-%d").tolist()
    lines = svg_header("Overlay: normalized close, equity, and trade exits", width, height)
    lines.append(f'<line x1="{pad}" y1="{height-pad}" x2="{width-pad}" y2="{height-pad}" stroke="#d1d5db" />')
    lines.append(f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height-pad}" stroke="#d1d5db" />')
    lines.append(polyline(scale_points(price, width, height, pad), "#6b7280", 1.3))
    lines.append(polyline(scale_points(equity, width, height, pad), "#2563eb", 2.2))

    time_to_idx = {ts.isoformat(): idx for idx, ts in enumerate(equity_df["time"])}
    price_points = scale_points(price, width, height, pad)
    for trade in trades:
        exit_time = parse_time(str(trade["exit_time"])).isoformat()
        idx = time_to_idx.get(exit_time)
        if idx is None or idx >= len(price_points):
            continue
        x, y = price_points[idx]
        color = "#16a34a" if float(trade["net_pnl"]) > 0 else "#dc2626"
        marker = "▲" if str(trade["side"]) == "long" else "▼"
        lines.append(f'<text x="{x-5:.2f}" y="{y+4:.2f}" font-family="Arial" font-size="11" fill="{color}">{marker}</text>')

    lines.append(f'<text x="{width-pad-260}" y="62" font-family="Arial" font-size="13" fill="#2563eb">equity</text>')
    lines.append(f'<text x="{width-pad-260}" y="82" font-family="Arial" font-size="13" fill="#6b7280">close</text>')
    lines.append(f'<text x="{width-pad-260}" y="102" font-family="Arial" font-size="13" fill="#16a34a">win exit</text>')
    lines.append(f'<text x="{width-pad-260}" y="122" font-family="Arial" font-size="13" fill="#dc2626">loss exit</text>')
    if labels:
        lines.append(f'<text x="{pad}" y="{height-20}" font-family="Arial" font-size="12" fill="#6b7280">{html.escape(labels[0])}</text>')
        lines.append(f'<text x="{width-pad-120}" y="{height-20}" font-family="Arial" font-size="12" fill="#6b7280">{html.escape(labels[-1])}</text>')
    lines.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_histogram_svg(path: Path, values: list[float], title: str, bins: int = 24) -> None:
    width, height, pad = 900, 440, 56
    if not values:
        path.write_text("", encoding="utf-8")
        return
    lo, hi = min(values), max(values)
    if math.isclose(lo, hi):
        hi = lo + 1.0
    counts = [0 for _ in range(bins)]
    for value in values:
        idx = min(int((value - lo) / (hi - lo) * bins), bins - 1)
        counts[idx] += 1
    max_count = max(counts) or 1
    bar_w = (width - 2 * pad) / bins
    lines = svg_header(title, width, height)
    lines.append(f'<line x1="{pad}" y1="{height-pad}" x2="{width-pad}" y2="{height-pad}" stroke="#d1d5db" />')
    for idx, count in enumerate(counts):
        x = pad + idx * bar_w
        h = count / max_count * (height - 2 * pad)
        y = height - pad - h
        color = "#16a34a" if (lo + (idx + 0.5) / bins * (hi - lo)) >= 0 else "#dc2626"
        lines.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w-2:.2f}" height="{h:.2f}" fill="{color}" opacity="0.75" />')
    lines.append(f'<text x="{pad}" y="{height-18}" font-family="Arial" font-size="12" fill="#6b7280">{lo:.2f}</text>')
    lines.append(f'<text x="{width-pad-80}" y="{height-18}" font-family="Arial" font-size="12" fill="#6b7280">{hi:.2f}</text>')
    lines.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build_equity_df(report: dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame(report["equity_series"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df["equity"] = pd.to_numeric(df["equity"], errors="coerce")
    df["balance"] = pd.to_numeric(df["balance"], errors="coerce")
    df["drawdown_pct"] = pct_drawdown(df["equity"].tolist())
    return df


def write_diagnostics_summary(
    output_dir: Path,
    report: dict[str, Any],
    metrics: dict[str, float | int],
    breakdowns: dict[str, list[dict[str, Any]]],
) -> None:
    best = sorted(report.get("trade_details", []), key=lambda t: float(t["net_pnl"]), reverse=True)[:5]
    worst = sorted(report.get("trade_details", []), key=lambda t: float(t["net_pnl"]))[:5]
    year_rows = breakdowns["by_exit_year"]
    lines = [
        "# XAUUSD VB/H4 Trade Diagnostics",
        "",
        "Metric note: this diagnostics run uses one continuous 2015-2025 H4 dataset, so equity and drawdown curves are continuous. Annual report averages elsewhere are year-reset averages.",
        "",
        "## Trade Metrics",
        "",
        f"- Trades: `{metrics['trades']}`",
        f"- Win Rate: `{metrics['win_rate_pct']:.2f}%`",
        f"- Avg Win: `{metrics['avg_win']:.2f}`",
        f"- Avg Loss: `{metrics['avg_loss']:.2f}`",
        f"- Payoff Ratio: `{metrics['payoff_ratio']:.2f}`",
        f"- Profit Factor: `{metrics['profit_factor']:.2f}`",
        f"- Expectancy / Trade: `{metrics['expectancy']:.2f}`",
        f"- Sharpe / Trade: `{metrics['sharpe_per_trade']:.2f}`",
        f"- Avg R Multiple: `{metrics['avg_r_multiple']:.2f}`",
        f"- Avg Holding: `{metrics['avg_holding_bars']:.2f}` bars / `{metrics['avg_holding_days']:.2f}` days",
        "",
        "## Plots",
        "",
        "- `plots/equity_curve.svg`",
        "- `plots/drawdown_curve.svg`",
        "- `plots/overlay_curve.svg`",
        "- `plots/trade_return_histogram.svg`",
        "- `plots/rolling_sharpe.svg`",
        "",
        "## Year Breakdown",
        "",
        "| Year | Trades | Win Rate | Net PnL | Avg R | PF | Avg Hold Bars |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in year_rows:
        lines.append(
            "| "
            f"{row['exit_year']} | {row['trades']} | {row['win_rate_pct']:.2f}% | "
            f"{row['net_pnl']:.2f} | {row['avg_r']:.2f} | {row['profit_factor']:.2f} | "
            f"{row['avg_holding_bars']:.2f} |"
        )
    lines.extend(["", "## Largest Wins", "", "| Exit | Side | PnL | R | Holding Bars |", "| --- | --- | ---: | ---: | ---: |"])
    for trade in best:
        lines.append(f"| {trade['exit_time']} | {trade['side']} | {float(trade['net_pnl']):.2f} | {float(trade.get('r_multiple', 0.0)):.2f} | {trade['holding_bars']} |")
    lines.extend(["", "## Largest Losses", "", "| Exit | Side | PnL | R | Holding Bars |", "| --- | --- | ---: | ---: | ---: |"])
    for trade in worst:
        lines.append(f"| {trade['exit_time']} | {trade['side']} | {float(trade['net_pnl']):.2f} | {float(trade.get('r_multiple', 0.0)):.2f} | {trade['holding_bars']} |")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "diagnostics_summary.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trade-level diagnostics and SVG plots for XAUUSD VB/H4 candidate.")
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
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
    output_dir = Path(args.output_dir).expanduser()
    if not data_dir.is_absolute():
        data_dir = (Path.cwd() / data_dir).resolve()
    if not output_dir.is_absolute():
        output_dir = (Path.cwd() / output_dir).resolve()
    params = CandidateParams(
        donchian_breakout_period=args.donchian_breakout_period,
        donchian_exit_period=args.donchian_exit_period,
        sl_atr_mult=args.sl_atr_mult,
        trail_atr_mult=args.trail_atr_mult,
        h1_adx_min=args.h1_adx_min,
        atr_ratio_min=args.atr_ratio_min,
    )

    files = resolve_h4_files(data_dir)
    with tempfile.TemporaryDirectory(prefix="vb_h4_diag_") as tmp:
        combined_path = Path(tmp) / "H4_2015_2025.csv"
        price_df = combine_h4_files(files, combined_path)
        report = run_engine(combined_path, params, args)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "continuous_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    trades = enrich_trades(report, params, args)
    add_buckets(trades)
    report["trade_details"] = trades
    metrics = trade_metrics(trades)
    write_csv(output_dir / "trade_details.csv", trades)

    breakdowns = {
        "by_exit_year": group_summary(trades, "exit_year"),
        "by_exit_quarter": group_summary(trades, "exit_quarter"),
        "by_side": group_summary(trades, "side"),
        "by_exit_reason": group_summary(trades, "exit_reason"),
        "by_holding_bucket": group_summary(trades, "holding_bucket"),
        "by_adx_bucket": group_summary(trades, "adx_bucket"),
        "by_atr_ratio_bucket": group_summary(trades, "atr_ratio_bucket"),
    }
    breakdown_dir = output_dir / "breakdowns"
    for name, rows in breakdowns.items():
        write_csv(breakdown_dir / f"{name}.csv", rows)

    equity_df = build_equity_df(report)
    plots_dir = output_dir / "plots"
    labels = equity_df["time"].dt.strftime("%Y-%m-%d").tolist()
    write_line_svg(plots_dir / "equity_curve.svg", "Continuous equity curve", labels, [("equity", equity_df["equity"].tolist(), "#2563eb")])
    write_line_svg(plots_dir / "drawdown_curve.svg", "Drawdown curve (%)", labels, [("drawdown_pct", equity_df["drawdown_pct"].tolist(), "#dc2626")])
    write_overlay_svg(plots_dir / "overlay_curve.svg", equity_df, price_df.reset_index(drop=True), trades)
    write_histogram_svg(plots_dir / "trade_return_histogram.svg", [float(t["r_multiple"]) for t in trades], "Trade return histogram (R multiple)")
    rolling = rolling_sharpe([float(t["net_pnl"]) for t in trades], window=30)
    write_line_svg(plots_dir / "rolling_sharpe.svg", "Rolling 30-trade Sharpe", [str(t["trade_id"]) for t in trades], [("rolling_sharpe", rolling, "#7c3aed")])

    write_diagnostics_summary(output_dir, report, metrics, breakdowns)
    print(f"Saved diagnostics to {output_dir}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
