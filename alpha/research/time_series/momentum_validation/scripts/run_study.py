from __future__ import annotations

import math
import sys
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DATA_ROOT = PROJECT_ROOT / "shared" / "data"
STUDY_DIR = Path(__file__).resolve().parents[1]
METRICS_DIR = STUDY_DIR / "metrics"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(PROJECT_ROOT))

from shared.configs.universes import MIXED_ASSET_SYMBOLS  # noqa: E402

ASSET_CLASSES = ["equity", "commodity", "bond"]
MOMENTUM_WINDOWS = [63, 126, 252]
FORWARD_HORIZONS = [20, 60, 120]
REQUIRED_COLUMNS = ["Date", "Adj Close"]
MIN_QUANTILES = 5


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

    min_rows = max(MOMENTUM_WINDOWS) + max(FORWARD_HORIZONS) + 1
    if len(df) < min_rows:
        warnings.warn(f"{symbol}: only {len(df)} rows, fewer than {min_rows}, skipped")
        return None

    df["symbol"] = symbol
    df["asset_class"] = asset_class
    return df


def add_research_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for window in MOMENTUM_WINDOWS:
        df[f"mom_{window}"] = df["price"] / df["price"].shift(window) - 1

    for horizon in FORWARD_HORIZONS:
        df[f"FR{horizon}"] = df["price"].shift(-horizon) / df["price"] - 1

    return df


def return_metrics(returns: pd.Series) -> dict:
    returns = returns.dropna()
    return {
        "sample_count": int(len(returns)),
        "mean": returns.mean() if len(returns) else np.nan,
        "median": returns.median() if len(returns) else np.nan,
        "std": returns.std(ddof=1) if len(returns) > 1 else np.nan,
        "win_rate": (returns > 0).mean() if len(returns) else np.nan,
    }


def pooled_cohens_d(top: pd.Series, bottom: pd.Series) -> float:
    top = top.dropna()
    bottom = bottom.dropna()
    if len(top) < 2 or len(bottom) < 2:
        return np.nan

    top_var = top.var(ddof=1)
    bottom_var = bottom.var(ddof=1)
    pooled_var = ((len(top) - 1) * top_var + (len(bottom) - 1) * bottom_var) / (
        len(top) + len(bottom) - 2
    )
    if pd.isna(pooled_var) or pooled_var <= 0:
        return np.nan
    return (top.mean() - bottom.mean()) / math.sqrt(pooled_var)


def assign_momentum_quantiles(values: pd.Series, symbol: str, momentum_col: str) -> pd.Series:
    valid = values.dropna()
    if valid.nunique() < MIN_QUANTILES:
        warnings.warn(f"{symbol} {momentum_col}: fewer than 5 unique momentum values, skipped")
        return pd.Series(index=values.index, dtype="object")

    try:
        quantiles = pd.qcut(valid, q=5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"], duplicates="raise")
    except ValueError as exc:
        warnings.warn(f"{symbol} {momentum_col}: unable to create 5 quantiles ({exc}), skipped")
        return pd.Series(index=values.index, dtype="object")

    result = pd.Series(index=values.index, dtype="object")
    result.loc[valid.index] = quantiles.astype(str)
    return result


def analyze_symbol(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    symbol = df["symbol"].iloc[0]
    asset_class = df["asset_class"].iloc[0]
    df = add_research_columns(df)

    quantile_rows = []
    top_bottom_rows = []

    for momentum_window in MOMENTUM_WINDOWS:
        momentum_col = f"mom_{momentum_window}"
        quantile_col = f"{momentum_col}_quantile"
        df[quantile_col] = assign_momentum_quantiles(df[momentum_col], symbol, momentum_col)

        if df[quantile_col].dropna().nunique() < MIN_QUANTILES:
            continue

        for forward_horizon in FORWARD_HORIZONS:
            forward_col = f"FR{forward_horizon}"
            valid = df.dropna(subset=[quantile_col, forward_col]).copy()

            if valid.empty:
                warnings.warn(
                    f"{symbol} {momentum_col}->{forward_col}: no valid samples after forward filtering"
                )
                continue

            for quantile in ["Q1", "Q2", "Q3", "Q4", "Q5"]:
                returns = valid.loc[valid[quantile_col] == quantile, forward_col]
                row = {
                    "symbol": symbol,
                    "asset_class": asset_class,
                    "momentum_window": momentum_col,
                    "forward_horizon": forward_col,
                    "quantile": quantile,
                }
                row.update(return_metrics(returns))
                quantile_rows.append(row)

            top_returns = valid.loc[valid[quantile_col] == "Q5", forward_col].dropna()
            bottom_returns = valid.loc[valid[quantile_col] == "Q1", forward_col].dropna()
            if len(top_returns) < 2 or len(bottom_returns) < 2:
                warnings.warn(
                    f"{symbol} {momentum_col}->{forward_col}: fewer than 2 samples in top or bottom"
                )
                continue

            t_result = stats.ttest_ind(top_returns, bottom_returns, equal_var=False, nan_policy="omit")
            top_bottom_rows.append(
                {
                    "symbol": symbol,
                    "asset_class": asset_class,
                    "momentum_window": momentum_col,
                    "forward_horizon": forward_col,
                    "top_mean": top_returns.mean(),
                    "bottom_mean": bottom_returns.mean(),
                    "difference": top_returns.mean() - bottom_returns.mean(),
                    "top_median": top_returns.median(),
                    "bottom_median": bottom_returns.median(),
                    "top_win_rate": (top_returns > 0).mean(),
                    "bottom_win_rate": (bottom_returns > 0).mean(),
                    "t_statistic": t_result.statistic,
                    "p_value": t_result.pvalue,
                    "cohens_d": pooled_cohens_d(top_returns, bottom_returns),
                }
            )

    return quantile_rows, top_bottom_rows


def summarize_asset_classes(top_bottom_summary: pd.DataFrame) -> pd.DataFrame:
    if top_bottom_summary.empty:
        return pd.DataFrame(
            columns=[
                "asset_class",
                "momentum_window",
                "forward_horizon",
                "avg_difference",
                "percent_symbols_top_outperforms_bottom",
                "avg_top_win_rate",
                "avg_bottom_win_rate",
                "avg_p_value",
                "avg_cohens_d",
            ]
        )

    summary = top_bottom_summary.groupby(["asset_class", "momentum_window", "forward_horizon"]).agg(
        avg_difference=("difference", "mean"),
        percent_symbols_top_outperforms_bottom=("difference", lambda x: (x > 0).mean()),
        avg_top_win_rate=("top_win_rate", "mean"),
        avg_bottom_win_rate=("bottom_win_rate", "mean"),
        avg_p_value=("p_value", "mean"),
        avg_cohens_d=("cohens_d", "mean"),
    )
    return summary.reset_index()


def pct(value: float) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.2%}"


def num(value: float) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.3f}"


def markdown_table(df: pd.DataFrame, columns: list[str], percent_columns: set[str]) -> str:
    if df.empty:
        return "_No data._"

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in df[columns].iterrows():
        formatted = []
        for col in columns:
            value = row[col]
            if col in percent_columns:
                formatted.append(pct(value))
            elif isinstance(value, (float, np.floating)):
                formatted.append(num(value))
            else:
                formatted.append(str(value))
        lines.append("| " + " | ".join(formatted) + " |")
    return "\n".join(lines)


def best_row(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return df
    idx = df.groupby(group_cols)["avg_difference"].idxmax()
    return df.loc[idx].sort_values(group_cols).reset_index(drop=True)


def add_sort_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["_momentum_rank"] = df["momentum_window"].str.replace("mom_", "", regex=False).astype(int)
    df["_forward_rank"] = df["forward_horizon"].str.replace("FR", "", regex=False).astype(int)
    return df


def drop_sort_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=[col for col in ["_momentum_rank", "_forward_rank"] if col in df.columns])


def generate_summary(
    quantile_summary: pd.DataFrame,
    top_bottom_summary: pd.DataFrame,
    asset_class_summary: pd.DataFrame,
    warnings_list: list[str],
) -> str:
    overall = (
        top_bottom_summary.groupby(["momentum_window", "forward_horizon"])
        .agg(
            avg_difference=("difference", "mean"),
            percent_symbols_top_outperforms_bottom=("difference", lambda x: (x > 0).mean()),
            avg_top_win_rate=("top_win_rate", "mean"),
            avg_bottom_win_rate=("bottom_win_rate", "mean"),
            avg_p_value=("p_value", "mean"),
            avg_cohens_d=("cohens_d", "mean"),
        )
        .reset_index()
        if not top_bottom_summary.empty
        else pd.DataFrame()
    )

    overall_best = (
        overall.sort_values(["avg_difference", "avg_cohens_d"], ascending=False).head(1)
        if not overall.empty
        else pd.DataFrame()
    )
    asset_best = best_row(asset_class_summary, ["asset_class"])

    significant = top_bottom_summary[
        (top_bottom_summary["difference"] > 0) & (top_bottom_summary["p_value"] < 0.05)
    ]
    positive_top = top_bottom_summary[top_bottom_summary["top_mean"] > 0]
    top_outperforms = top_bottom_summary[top_bottom_summary["difference"] > 0]

    if overall_best.empty:
        alpha_conclusion = "样本不足，无法判断 Momentum Alpha。"
        best_momentum = "NA"
        best_horizon = "NA"
    else:
        best = overall_best.iloc[0]
        best_momentum = str(best["momentum_window"])
        best_horizon = str(best["forward_horizon"])
        alpha_conclusion = (
            f"总体上 Top 20% 平均相对 Bottom 20% 的最佳组合是 "
            f"{best_momentum} -> {best_horizon}，avg_difference={pct(best['avg_difference'])}。"
        )

    overall_for_table = (
        drop_sort_columns(add_sort_columns(overall).sort_values(["_momentum_rank", "_forward_rank"]))
        if not overall.empty
        else overall
    )
    overall_table = markdown_table(
        overall_for_table,
        [
            "momentum_window",
            "forward_horizon",
            "avg_difference",
            "percent_symbols_top_outperforms_bottom",
            "avg_top_win_rate",
            "avg_bottom_win_rate",
            "avg_p_value",
            "avg_cohens_d",
        ],
        {
            "avg_difference",
            "percent_symbols_top_outperforms_bottom",
            "avg_top_win_rate",
            "avg_bottom_win_rate",
        },
    )
    asset_table = markdown_table(
        asset_best,
        [
            "asset_class",
            "momentum_window",
            "forward_horizon",
            "avg_difference",
            "percent_symbols_top_outperforms_bottom",
            "avg_top_win_rate",
            "avg_bottom_win_rate",
            "avg_p_value",
            "avg_cohens_d",
        ],
        {
            "avg_difference",
            "percent_symbols_top_outperforms_bottom",
            "avg_top_win_rate",
            "avg_bottom_win_rate",
        },
    )

    class_sections = []
    for asset_class in ASSET_CLASSES:
        class_df = asset_class_summary[asset_class_summary["asset_class"] == asset_class]
        if class_df.empty:
            class_sections.append(f"### {asset_class.title()}\n\n- 样本不足或无结果。")
            continue
        class_best = class_df.sort_values(["avg_difference", "avg_cohens_d"], ascending=False).iloc[0]
        class_sig = top_bottom_summary[
            (top_bottom_summary["asset_class"] == asset_class)
            & (top_bottom_summary["difference"] > 0)
            & (top_bottom_summary["p_value"] < 0.05)
        ]
        class_sections.append(
            f"### {asset_class.title()}\n\n"
            f"- 最强组合: `{class_best['momentum_window']} -> {class_best['forward_horizon']}`，"
            f"avg_difference={pct(class_best['avg_difference'])}，"
            f"top outperform 比例={pct(class_best['percent_symbols_top_outperforms_bottom'])}。\n"
            f"- 显著且 Top > Bottom 的 symbol-window-horizon 数量: {len(class_sig)}。"
        )

    warnings_section = (
        "\n".join(f"- {warning}" for warning in warnings_list) if warnings_list else "- 无跳过或数据质量 warning。"
    )

    return f"""# Momentum Alpha Validation Summary

## 1. 研究问题

过去收益率是否能预测未来收益率？
本实验验证的是 Past Return 对 Future Return 的预测能力，不是交易策略回测。

## 2. Alpha 假设

如果 Momentum Alpha 存在，则过去动量最强的一组未来收益应该高于过去动量最弱的一组。
核心比较是每个 symbol 内部的 `Q5 / Top 20%` 与 `Q1 / Bottom 20%`。

## 3. 实验设计

- Price: `Adj Close`
- Momentum windows: `mom_63`, `mom_126`, `mom_252`
- Forward horizons: `FR20`, `FR60`, `FR120`
- 每个 symbol 内部按 momentum 分成 5 组: `Q1` 到 `Q5`
- `Q1` 是过去动量最弱 20%，`Q5` 是过去动量最强 20%
- Forward return 只用于验证，不进入 momentum 信号计算
- 未来数据不足的样本直接丢弃
- Top vs Bottom 检验使用 Welch t-test，并报告 Cohen's d

## 4. 总体结论

- 是否发现 Momentum Alpha: {alpha_conclusion}
- 最有效 momentum window: `{best_momentum}`
- 最有效 forward horizon: `{best_horizon}`
- Top 组未来收益为正的检验组合数量: {len(positive_top)} / {len(top_bottom_summary)}
- Top 组未来收益高于 Bottom 组的检验组合数量: {len(top_outperforms)} / {len(top_bottom_summary)}
- Top > Bottom 且 p-value < 0.05 的检验组合数量: {len(significant)} / {len(top_bottom_summary)}

### Overall Top vs Bottom Summary

{overall_table}

## 5. 分资产类别结论

### Best Combination By Asset Class

{asset_table}

{chr(10).join(class_sections)}

## 6. 注意事项

- `Top 组未来收益为正` 只说明高动量样本后续平均收益为正，不等于存在 alpha。
- `Top 组未来收益高于 Bottom 组` 才是本实验对 Momentum Alpha 的核心方向性证据。
- `p_value < 0.05` 表示均值差异在当前样本中更难用随机波动解释；不显著不等于没有经济意义，但不能作为强统计证据。
- Cohen's d 衡量差异相对波动的大小；均值差异显著但 Cohen's d 很小，仍可能很难构造成稳健策略。
- 是否值得进入策略构建阶段，应同时看方向稳定性、显著性、效果大小、资产类别一致性，以及交易规则后的成本和回撤。

## 7. 下一步建议

- 测试跨资产横截面动量，而不是只做单资产时间序列分位数。
- 测试 monthly rebalance，减少日度样本重叠带来的统计依赖。
- 加入 MA 风险过滤，观察趋势状态是否能改善 Top vs Bottom 差异。
- 做 out-of-sample split，避免只根据全样本选择最佳窗口。
- 对 forward return 使用 Newey-West 或 block bootstrap，处理重叠持有期导致的自相关。

## 8. Data Warnings

{warnings_section}
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    captured_warnings: list[str] = []

    def capture_warning(message, category, filename, lineno, file=None, line=None):
        captured_warnings.append(str(message))

    old_showwarning = warnings.showwarning
    warnings.showwarning = capture_warning
    try:
        quantile_rows = []
        top_bottom_rows = []

        for asset_class, path in discover_data_files():
            df = load_price_data(path, asset_class)
            if df is None:
                continue
            symbol_quantile_rows, symbol_top_bottom_rows = analyze_symbol(df)
            quantile_rows.extend(symbol_quantile_rows)
            top_bottom_rows.extend(symbol_top_bottom_rows)
    finally:
        warnings.showwarning = old_showwarning

    quantile_summary = pd.DataFrame(quantile_rows)
    top_bottom_summary = pd.DataFrame(top_bottom_rows)
    asset_class_summary = summarize_asset_classes(top_bottom_summary)

    quantile_columns = [
        "symbol",
        "asset_class",
        "momentum_window",
        "forward_horizon",
        "quantile",
        "sample_count",
        "mean",
        "median",
        "std",
        "win_rate",
    ]
    top_bottom_columns = [
        "symbol",
        "asset_class",
        "momentum_window",
        "forward_horizon",
        "top_mean",
        "bottom_mean",
        "difference",
        "top_median",
        "bottom_median",
        "top_win_rate",
        "bottom_win_rate",
        "t_statistic",
        "p_value",
        "cohens_d",
    ]
    asset_class_columns = [
        "asset_class",
        "momentum_window",
        "forward_horizon",
        "avg_difference",
        "percent_symbols_top_outperforms_bottom",
        "avg_top_win_rate",
        "avg_bottom_win_rate",
        "avg_p_value",
        "avg_cohens_d",
    ]

    quantile_summary = quantile_summary.reindex(columns=quantile_columns)
    top_bottom_summary = top_bottom_summary.reindex(columns=top_bottom_columns)
    asset_class_summary = asset_class_summary.reindex(columns=asset_class_columns)

    sort_keys = ["symbol", "momentum_window", "forward_horizon"]
    if not quantile_summary.empty:
        quantile_summary = add_sort_columns(quantile_summary).sort_values(
            ["symbol", "_momentum_rank", "_forward_rank", "quantile"]
        )
        quantile_summary = drop_sort_columns(quantile_summary).reset_index(drop=True)
    if not top_bottom_summary.empty:
        top_bottom_summary = add_sort_columns(top_bottom_summary).sort_values(
            ["symbol", "_momentum_rank", "_forward_rank"]
        )
        top_bottom_summary = drop_sort_columns(top_bottom_summary).reset_index(drop=True)
    if not asset_class_summary.empty:
        asset_class_summary = add_sort_columns(asset_class_summary).sort_values(
            ["asset_class", "_momentum_rank", "_forward_rank"]
        )
        asset_class_summary = drop_sort_columns(asset_class_summary).reset_index(drop=True)

    quantile_summary.to_csv(METRICS_DIR / "quantile_summary.csv", index=False)
    top_bottom_summary.to_csv(METRICS_DIR / "top_bottom_summary.csv", index=False)
    asset_class_summary.to_csv(METRICS_DIR / "asset_class_summary.csv", index=False)

    summary = generate_summary(
        quantile_summary=quantile_summary,
        top_bottom_summary=top_bottom_summary,
        asset_class_summary=asset_class_summary,
        warnings_list=captured_warnings,
    )
    SUMMARY_PATH.write_text(summary, encoding="utf-8")

    print("\nMomentum Alpha Test Complete")
    print(f"Study directory: {STUDY_DIR}")
    print(f"Symbols tested: {top_bottom_summary['symbol'].nunique() if not top_bottom_summary.empty else 0}")
    print(f"Top/Bottom tests: {len(top_bottom_summary)}")
    print("\nCore summary table:")
    if top_bottom_summary.empty:
        print("No valid top/bottom results.")
        return

    core = (
        top_bottom_summary.groupby(["momentum_window", "forward_horizon"])
        .agg(
            avg_difference=("difference", "mean"),
            pct_top_outperforms=("difference", lambda x: (x > 0).mean()),
            avg_p_value=("p_value", "mean"),
            avg_cohens_d=("cohens_d", "mean"),
        )
        .reset_index()
        .sort_values(["avg_difference", "avg_cohens_d"], ascending=False)
    )
    print(core.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))

    if captured_warnings:
        print("\nWarnings:")
        for warning in captured_warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
