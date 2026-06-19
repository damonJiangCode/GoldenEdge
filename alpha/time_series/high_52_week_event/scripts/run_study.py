from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
import math
import warnings

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = PROJECT_ROOT / "shared" / "data"
STUDY_DIR = Path(__file__).resolve().parents[1]
METRICS_DIR = STUDY_DIR / "metrics"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(PROJECT_ROOT))

from shared.configs.universes import MIXED_ASSET_SYMBOLS  # noqa: E402

ROLLING_WINDOW = 252
FORWARD_WINDOWS = [20, 60, 120]
BOOTSTRAP_RUNS = 1000
RANDOM_SEED = 42
REQUIRED_COLUMNS = ["Date", "Adj Close"]
ASSET_CLASSES = ["equity", "commodity", "bond"]


def discover_data_files() -> list[tuple[str, Path]]:
    files = []
    for asset_class in ASSET_CLASSES:
        asset_dir = DATA_ROOT / asset_class
        if not asset_dir.exists():
            warnings.warn(f"Missing asset class directory: {asset_dir}")
            continue
        for path in sorted(asset_dir.glob("*.csv")):
            if path.stem in MIXED_ASSET_SYMBOLS:
                files.append((asset_class, path))
    return files


def load_price_data(path: Path, asset_class: str) -> Optional[pd.DataFrame]:
    symbol = path.stem
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        warnings.warn(f"{symbol}: failed to read {path}: {exc}")
        return None

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        warnings.warn(f"{symbol}: missing columns {missing}, skipped")
        return None

    df = df[REQUIRED_COLUMNS].copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["price"] = pd.to_numeric(df["Adj Close"], errors="coerce")
    df = df.dropna(subset=["Date", "price"]).sort_values("Date")
    df = df.drop_duplicates(subset=["Date"], keep="last").reset_index(drop=True)

    if len(df) <= ROLLING_WINDOW + max(FORWARD_WINDOWS):
        warnings.warn(f"{symbol}: only {len(df)} rows, skipped")
        return None

    df["symbol"] = symbol
    df["asset_class"] = asset_class
    return df


def add_event_study_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["rolling_high_252"] = df["price"].shift(1).rolling(ROLLING_WINDOW).max()
    df["new_high"] = (df["price"] > df["rolling_high_252"]).fillna(False).astype(bool)
    previous_new_high = df["new_high"].shift(1, fill_value=False).astype(bool)
    df["event"] = df["new_high"] & (~previous_new_high)

    for window in FORWARD_WINDOWS:
        df[f"FR{window}"] = df["price"].shift(-window) / df["price"] - 1

    return df


def metric_row(group: str, horizon: str, returns: pd.Series, extra: Optional[dict] = None) -> dict:
    returns = returns.dropna()
    row = {
        "group": group,
        "horizon": horizon,
        "sample_count": int(len(returns)),
        "mean": returns.mean() if len(returns) else np.nan,
        "median": returns.median() if len(returns) else np.nan,
        "std": returns.std(ddof=1) if len(returns) > 1 else np.nan,
        "win_rate": (returns > 0).mean() if len(returns) else np.nan,
    }
    if extra:
        row.update(extra)
    return row


def pooled_cohens_d(x: pd.Series, y: pd.Series) -> float:
    x = x.dropna()
    y = y.dropna()
    if len(x) < 2 or len(y) < 2:
        return np.nan

    var_x = x.var(ddof=1)
    var_y = y.var(ddof=1)
    pooled_var = ((len(x) - 1) * var_x + (len(y) - 1) * var_y) / (len(x) + len(y) - 2)
    if pooled_var <= 0 or pd.isna(pooled_var):
        return np.nan
    return (x.mean() - y.mean()) / math.sqrt(pooled_var)


def normal_two_sided_p_value(z: float) -> float:
    if pd.isna(z):
        return np.nan
    return math.erfc(abs(z) / math.sqrt(2))


def bootstrap_random_means(
    values: pd.Series,
    sample_size: int,
    rng: np.random.Generator,
    runs: int = BOOTSTRAP_RUNS,
) -> np.ndarray:
    values = values.dropna().to_numpy(dtype=float)
    if sample_size <= 0 or len(values) == 0:
        return np.array([], dtype=float)
    draws = rng.choice(values, size=(runs, sample_size), replace=True)
    return draws.mean(axis=1)


def summarize_bootstrap(group: str, horizon: str, means: np.ndarray, extra: Optional[dict] = None) -> dict:
    row = {
        "group": group,
        "horizon": horizon,
        "bootstrap_runs": int(len(means)),
        "mean": float(np.mean(means)) if len(means) else np.nan,
        "std": float(np.std(means, ddof=1)) if len(means) > 1 else np.nan,
        "percentile_5": float(np.percentile(means, 5)) if len(means) else np.nan,
        "percentile_95": float(np.percentile(means, 95)) if len(means) else np.nan,
    }
    if extra:
        row.update(extra)
    return row


def horizon_rank(horizon: str) -> int:
    return FORWARD_WINDOWS.index(int(horizon.replace("FR", "")))


def sort_by_group_and_horizon(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["_horizon_rank"] = df["horizon"].map(horizon_rank)
    df = df.sort_values(["group_type", "group", "_horizon_rank"]).drop(columns="_horizon_rank")
    return df.reset_index(drop=True)


def interpret_difference(diff: float, p_value: float) -> str:
    if pd.isna(diff):
        return "insufficient_data"
    if abs(diff) < 1e-12:
        return "B_event_approximately_random"
    if pd.notna(p_value) and p_value > 0.05:
        return "B_event_approximately_random"
    if diff > 0:
        return "A_supports_trend_alpha"
    return "C_event_weaker_than_random"


def compare_event_to_random(
    group: str,
    horizon: str,
    event_returns: pd.Series,
    non_event_returns: pd.Series,
    random_means: np.ndarray,
) -> dict:
    event_returns = event_returns.dropna()
    non_event_returns = non_event_returns.dropna()
    event_mean = event_returns.mean() if len(event_returns) else np.nan
    random_mean = float(np.mean(random_means)) if len(random_means) else np.nan
    random_std = float(np.std(random_means, ddof=1)) if len(random_means) > 1 else np.nan
    difference = event_mean - random_mean

    if pd.notna(random_std) and random_std > 0:
        t_statistic = difference / random_std
        empirical_p = (np.abs(random_means - random_mean) >= abs(difference)).mean()
        p_value = max(float(empirical_p), 1.0 / len(random_means))
    else:
        t_statistic = np.nan
        p_value = np.nan

    normal_p_value = normal_two_sided_p_value(t_statistic)
    cohens_d = pooled_cohens_d(event_returns, non_event_returns)

    return {
        "group": group,
        "horizon": horizon,
        "event_sample_count": int(len(event_returns)),
        "non_event_sample_count": int(len(non_event_returns)),
        "event_mean": event_mean,
        "random_mean": random_mean,
        "difference": difference,
        "t_statistic": t_statistic,
        "p_value": p_value,
        "normal_approx_p_value": normal_p_value,
        "cohens_d": cohens_d,
        "event_win_rate": (event_returns > 0).mean() if len(event_returns) else np.nan,
        "interpretation": interpret_difference(difference, p_value),
    }


def build_group_stats(
    labeled_returns: pd.DataFrame,
    group_col: str,
    rng: np.random.Generator,
) -> tuple[list[dict], list[dict], list[dict]]:
    event_rows = []
    bootstrap_rows = []
    comparison_rows = []

    for group_value, part in labeled_returns.groupby(group_col, dropna=False):
        group = str(group_value)
        for window in FORWARD_WINDOWS:
            horizon = f"FR{window}"
            valid = part.dropna(subset=[horizon])
            event_returns = valid.loc[valid["event"], horizon]
            non_event_returns = valid.loc[~valid["event"], horizon]
            random_means = bootstrap_random_means(non_event_returns, len(event_returns), rng)

            event_rows.append(metric_row(group, horizon, event_returns))
            bootstrap_rows.append(summarize_bootstrap(group, horizon, random_means))
            comparison_rows.append(
                compare_event_to_random(group, horizon, event_returns, non_event_returns, random_means)
            )

    return event_rows, bootstrap_rows, comparison_rows


def summarize_asset_classes(comparison: pd.DataFrame, event_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    event_lookup = event_summary.set_index(["group", "horizon"])
    for _, row in comparison[comparison["group"].isin(ASSET_CLASSES)].iterrows():
        event_stats = event_lookup.loc[(row["group"], row["horizon"])]
        rows.append(
            {
                "asset_class": row["group"],
                "horizon": row["horizon"],
                "event_sample_count": row["event_sample_count"],
                "event_mean": row["event_mean"],
                "event_median": event_stats["median"],
                "event_std": event_stats["std"],
                "event_win_rate": row["event_win_rate"],
                "random_mean": row["random_mean"],
                "difference": row["difference"],
                "t_statistic": row["t_statistic"],
                "p_value": row["p_value"],
                "cohens_d": row["cohens_d"],
                "interpretation": row["interpretation"],
            }
        )
    return pd.DataFrame(rows)


def fmt_pct(value: float) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.2%}"


def fmt_num(value: float) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.2f}"


def markdown_table(df: pd.DataFrame, columns: list[str], pct_columns: Optional[set[str]] = None) -> str:
    pct_columns = pct_columns or set()
    lines = ["| " + " | ".join(columns) + " |"]
    lines.append("|" + "|".join(["---"] * len(columns)) + "|")
    for _, row in df[columns].iterrows():
        cells = []
        for col in columns:
            value = row[col]
            if col in pct_columns:
                cells.append(fmt_pct(value))
            elif isinstance(value, (float, np.floating)):
                cells.append(fmt_num(value))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_summary(
    combined: pd.DataFrame,
    event_summary: pd.DataFrame,
    bootstrap_summary: pd.DataFrame,
    asset_class_summary: pd.DataFrame,
    comparison: pd.DataFrame,
    warnings_list: list[str],
) -> None:
    overall = comparison[comparison["group"] == "ALL"].copy()
    overall_events = event_summary[event_summary["group"] == "ALL"].copy()
    overall_bootstrap = bootstrap_summary[bootstrap_summary["group"] == "ALL"].copy()
    total_events = int(combined["event"].sum())
    symbol_counts = combined.groupby(["asset_class", "symbol"])["event"].sum().reset_index(name="event_count")

    lines = []
    lines.append("# 52-Week High Event Study Summary\n")
    lines.append("## 1. 研究问题\n")
    lines.append("当资产首次突破过去 52 周最高收盘价时，未来收益是否显著高于随机时期？")
    lines.append("这里验证的是事件本身是否具有预测未来收益的能力，不是验证某个交易策略。\n")

    lines.append("## 2. 事件定义\n")
    lines.append("- Price: `Adj Close`")
    lines.append("- `rolling_high_252 = AdjClose.shift(1).rolling(252).max()`")
    lines.append("- `new_high = AdjClose > rolling_high_252`")
    lines.append("- `event = new_high & (~new_high.shift(1).fillna(False))`")
    lines.append("- 连续创新高只记录第一次突破，减少样本重叠。")
    lines.append("- Forward returns: `FR20`, `FR60`, `FR120`; 未来数据不足的样本直接丢弃。\n")

    lines.append("## 3. 对照组与统计口径\n")
    lines.append(f"- 从全部非事件日中 bootstrap 抽样 `{BOOTSTRAP_RUNS}` 次。")
    lines.append("- 每次抽取数量等于对应事件样本数量。")
    lines.append("- `p_value` 为事件均值相对 bootstrap 随机均值分布的双侧经验 p-value。")
    lines.append("- `normal_approx_p_value` 保留在 CSV 中，作为 t-statistic 的正态近似参考。")
    lines.append("- `cohens_d` 用事件日收益和全部可用非事件日收益的 pooled std 计算。\n")

    lines.append("## 4. 总体结果\n")
    overall_cols = [
        "horizon",
        "event_sample_count",
        "event_mean",
        "random_mean",
        "difference",
        "t_statistic",
        "p_value",
        "cohens_d",
        "event_win_rate",
        "interpretation",
    ]
    lines.append(markdown_table(overall, overall_cols, {"event_mean", "random_mean", "difference", "event_win_rate"}))
    lines.append("")

    lines.append("## 5. Event Group 单独统计\n")
    event_cols = ["horizon", "sample_count", "mean", "median", "std", "win_rate"]
    lines.append(markdown_table(overall_events, event_cols, {"mean", "median", "std", "win_rate"}))
    lines.append("")

    lines.append("## 6. Bootstrap Random Group\n")
    boot_cols = ["horizon", "bootstrap_runs", "mean", "std", "percentile_5", "percentile_95"]
    lines.append(markdown_table(overall_bootstrap, boot_cols, {"mean", "std", "percentile_5", "percentile_95"}))
    lines.append("")

    lines.append("## 7. 分资产类别结果\n")
    asset_cols = [
        "asset_class",
        "horizon",
        "event_sample_count",
        "event_mean",
        "random_mean",
        "difference",
        "p_value",
        "cohens_d",
        "event_win_rate",
        "interpretation",
    ]
    lines.append(markdown_table(asset_class_summary, asset_cols, {"event_mean", "random_mean", "difference", "event_win_rate"}))
    lines.append("")

    lines.append("## 8. 结果解释框架\n")
    lines.append("- 情况 A: `Event Return > Random Return` 且差异显著，支持 Trend Alpha。")
    lines.append("- 情况 B: `Event Return ≈ Random Return`，不支持 Trend Alpha。")
    lines.append("- 情况 C: `Event Return < Random Return`，说明突破 52 周新高之后未来收益弱于普通时期。")
    lines.append("- 注意: 收益较低不等于负收益，也不等于适合做空。")
    lines.append("- 因此需要单独看 Event Group 中 `FR20 > 0`, `FR60 > 0`, `FR120 > 0` 的比例，也就是上表的 `event_win_rate`。\n")

    lines.append("## 9. 总体判断\n")
    for _, row in overall.iterrows():
        horizon = row["horizon"]
        if row["interpretation"] == "A_supports_trend_alpha":
            verdict = "支持 Trend Alpha"
        elif row["interpretation"] == "C_event_weaker_than_random":
            verdict = "事件后收益弱于随机时期，但这不是做空结论"
        else:
            verdict = "不支持 Trend Alpha"
        lines.append(
            f"- {horizon}: Event mean {fmt_pct(row['event_mean'])}, "
            f"Random mean {fmt_pct(row['random_mean'])}, "
            f"Difference {fmt_pct(row['difference'])}, "
            f"p-value {fmt_num(row['p_value'])}; 结论: {verdict}."
        )
    lines.append("")

    lines.append("## 10. 事件数量\n")
    lines.append(f"- Total first-breakout events before forward-return horizon filtering: `{total_events}`")
    lines.append(markdown_table(symbol_counts, ["asset_class", "symbol", "event_count"]))

    if warnings_list:
        lines.append("\n## 11. Warnings\n")
        for warning in warnings_list:
            lines.append(f"- {warning}")

    SUMMARY_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(RANDOM_SEED)
    warnings_list = []
    frames = []

    for asset_class, path in discover_data_files():
        symbol = path.stem
        df = load_price_data(path, asset_class)
        if df is None:
            warnings_list.append(f"{symbol}: skipped; see terminal warnings")
            continue
        frames.append(add_event_study_columns(df))

    if not frames:
        raise RuntimeError("No valid symbols processed.")

    combined = pd.concat(frames, ignore_index=True)
    combined["all"] = "ALL"

    event_rows = []
    bootstrap_rows = []
    comparison_rows = []
    for group_col in ["all", "asset_class", "symbol"]:
        e_rows, b_rows, c_rows = build_group_stats(combined, group_col, rng)
        group_label = {"all": "overall", "asset_class": "asset_class", "symbol": "symbol"}[group_col]
        for rows in [e_rows, b_rows, c_rows]:
            for row in rows:
                row["group_type"] = group_label
        event_rows.extend(e_rows)
        bootstrap_rows.extend(b_rows)
        comparison_rows.extend(c_rows)

    event_summary = pd.DataFrame(event_rows)
    bootstrap_summary = pd.DataFrame(bootstrap_rows)
    comparison = pd.DataFrame(comparison_rows)
    asset_class_summary = summarize_asset_classes(comparison, event_summary)

    event_summary = sort_by_group_and_horizon(event_summary)
    bootstrap_summary = sort_by_group_and_horizon(bootstrap_summary)
    comparison = sort_by_group_and_horizon(comparison)
    asset_class_summary["_horizon_rank"] = asset_class_summary["horizon"].map(horizon_rank)
    asset_class_summary = asset_class_summary.sort_values(["asset_class", "_horizon_rank"])
    asset_class_summary = asset_class_summary.drop(columns="_horizon_rank").reset_index(drop=True)

    event_summary.to_csv(METRICS_DIR / "event_summary.csv", index=False)
    bootstrap_summary.to_csv(METRICS_DIR / "bootstrap_summary.csv", index=False)
    asset_class_summary.to_csv(METRICS_DIR / "asset_class_summary.csv", index=False)
    comparison.to_csv(METRICS_DIR / "comparison_tests.csv", index=False)

    write_summary(combined, event_summary, bootstrap_summary, asset_class_summary, comparison, warnings_list)

    print("\n52-week high event study overall comparison:")
    print(
        comparison[comparison["group"] == "ALL"][
            [
                "horizon",
                "event_sample_count",
                "event_mean",
                "random_mean",
                "difference",
                "t_statistic",
                "p_value",
                "cohens_d",
                "event_win_rate",
                "interpretation",
            ]
        ].to_string(index=False)
    )
    print(f"\nStudy directory: {STUDY_DIR}")


if __name__ == "__main__":
    main()
