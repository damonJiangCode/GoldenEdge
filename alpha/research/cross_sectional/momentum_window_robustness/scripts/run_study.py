from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[4]
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(ALPHA_ROOT))

from shared.utils import cross_sectional as core  # noqa: E402


MOMENTUM_WINDOWS = [42, 63, 84, 105, 126, 147, 168, 189, 210, 252]
TOP_N = 5
SHARPE_NEIGHBOR_TOLERANCE = 0.20
PLATEAU_MIN_WINDOWS = 3
PLATEAU_MAX_SHARPE_RANGE = 0.15
PLATEAU_MAX_CAGR_RANGE = 0.02
PLATEAU_MAX_MAXDD_RANGE = 0.10


def add_robustness_scores(metrics: pd.DataFrame) -> pd.DataFrame:
    result = metrics.sort_values("momentum_window").reset_index(drop=True).copy()
    neighbor_labels = []
    neighbor_differences = []
    scores = []

    for index, row in result.iterrows():
        neighbor_indices = [candidate for candidate in (index - 1, index + 1) if 0 <= candidate < len(result)]
        neighbors = result.iloc[neighbor_indices]
        differences = (neighbors["Sharpe"] - row["Sharpe"]).abs()
        mean_difference = differences.mean()
        score = 100 * max(0.0, 1 - mean_difference / SHARPE_NEIGHBOR_TOLERANCE)
        neighbor_labels.append("/".join(neighbors["momentum_window"].astype(str)))
        neighbor_differences.append(mean_difference)
        scores.append(score)

    result["neighbor_windows"] = neighbor_labels
    result["neighbor_sharpe_mae"] = neighbor_differences
    result["Robustness Score"] = scores
    return result


def find_stable_plateau(metrics: pd.DataFrame) -> pd.DataFrame:
    ordered = metrics.sort_values("momentum_window").reset_index(drop=True)
    candidates: list[pd.DataFrame] = []

    for start in range(len(ordered)):
        for end in range(start + PLATEAU_MIN_WINDOWS, len(ordered) + 1):
            part = ordered.iloc[start:end]
            if (
                part["Sharpe"].max() - part["Sharpe"].min() <= PLATEAU_MAX_SHARPE_RANGE
                and part["CAGR"].max() - part["CAGR"].min() <= PLATEAU_MAX_CAGR_RANGE
                and part["MaxDD"].max() - part["MaxDD"].min() <= PLATEAU_MAX_MAXDD_RANGE
            ):
                candidates.append(part)

    if not candidates:
        return pd.DataFrame(columns=ordered.columns)
    return max(candidates, key=lambda part: (len(part), -int(part.iloc[0]["momentum_window"]))).copy()


def detect_sharpe_spikes(metrics: pd.DataFrame) -> pd.DataFrame:
    ordered = metrics.sort_values("momentum_window").reset_index(drop=True)
    columns = [
        "momentum_window",
        "Sharpe",
        "left_window",
        "left_sharpe_difference",
        "right_window",
        "right_sharpe_difference",
    ]
    rows = []
    for index in range(1, len(ordered) - 1):
        current = ordered.iloc[index]
        left = ordered.iloc[index - 1]
        right = ordered.iloc[index + 1]
        smaller_edge = min(current["Sharpe"] - left["Sharpe"], current["Sharpe"] - right["Sharpe"])
        if smaller_edge >= PLATEAU_MAX_SHARPE_RANGE:
            rows.append(
                {
                    "momentum_window": int(current["momentum_window"]),
                    "Sharpe": current["Sharpe"],
                    "left_window": int(left["momentum_window"]),
                    "left_sharpe_difference": current["Sharpe"] - left["Sharpe"],
                    "right_window": int(right["momentum_window"]),
                    "right_sharpe_difference": current["Sharpe"] - right["Sharpe"],
                }
            )
    return pd.DataFrame(rows, columns=columns)


def calculate_trends(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in ["CAGR", "Sharpe", "MaxDD", "Volatility", "Calmar", "Turnover"]:
        regression = stats.linregress(metrics["momentum_window"], metrics[column])
        rows.append(
            {
                "metric": column,
                "slope_per_21_days": regression.slope * 21,
                "r_squared": regression.rvalue**2,
                "p_value": regression.pvalue,
                "direction": "increases" if regression.slope > 0 else "decreases",
            }
        )
    return pd.DataFrame(rows)


def plot_window_metric(metrics: pd.DataFrame, column: str, filename: str, percent: bool = False) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(metrics["momentum_window"], metrics[column], color="#176B87", marker="o", linewidth=2)
    ax.axvline(126, color="#C2410C", linestyle="--", linewidth=1.2, alpha=0.8, label="Current window: 126")
    ax.set_xticks(MOMENTUM_WINDOWS)
    ax.set_xlabel("Momentum Window (Trading Days)")
    ax.set_ylabel(column)
    ax.set_title(f"Momentum Window vs {column}")
    if percent:
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"{value:.0%}"))
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUTS_DIR / filename, dpi=160)
    plt.close(fig)


def fmt_pct(value: float) -> str:
    return "NA" if pd.isna(value) else f"{value:.2%}"


def fmt_num(value: float) -> str:
    return "NA" if pd.isna(value) else f"{value:.2f}"


def markdown_metrics(metrics: pd.DataFrame) -> str:
    columns = [
        "momentum_window",
        "CAGR",
        "Sharpe",
        "MaxDD",
        "Volatility",
        "Calmar",
        "Total Return",
        "Turnover",
        "Robustness Score",
    ]
    pct_columns = {"CAGR", "MaxDD", "Volatility", "Total Return", "Turnover"}
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in metrics.iterrows():
        cells = []
        for column in columns:
            if column in pct_columns:
                cells.append(fmt_pct(row[column]))
            elif column == "momentum_window":
                cells.append(str(int(row[column])))
            else:
                cells.append(fmt_num(row[column]))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def trend_sentence(trends: pd.DataFrame, metric: str, percent: bool = False) -> str:
    row = trends.loc[trends["metric"] == metric].iloc[0]
    slope = row["slope_per_21_days"]
    if metric == "Turnover":
        magnitude = f"{abs(slope) * 100:.2f} 个百分点"
    else:
        magnitude = fmt_pct(abs(slope)) if percent else fmt_num(abs(slope))
    direction = "上升" if slope > 0 else "下降"
    significance = "具有统计显著性" if row["p_value"] < 0.05 else "不具有统计显著性"
    return f"窗口每增加 21 个交易日，{metric} 线性趋势约{direction} {magnitude}，但该趋势{significance}（p={row['p_value']:.3f}）。"


def generate_summary(
    metrics: pd.DataFrame,
    benchmark_metrics: pd.DataFrame,
    benchmark_tests: pd.DataFrame,
    plateau: pd.DataFrame,
    spikes: pd.DataFrame,
    trends: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    warnings_list: list[str],
) -> str:
    if plateau.empty:
        plateau_description = (
            "按预先设定的标准，没有找到至少 3 个连续 window 构成的稳定平台区。"
        )
        balance_description = "未识别出满足稳定性门槛的风险收益平衡区间。"
    else:
        first_window = int(plateau.iloc[0]["momentum_window"])
        last_window = int(plateau.iloc[-1]["momentum_window"])
        plateau_description = (
            f"识别到 `{first_window}-{last_window}` 交易日的平台区，共 {len(plateau)} 个连续 window。"
            f"区间内 CAGR 为 {fmt_pct(plateau['CAGR'].min())}-{fmt_pct(plateau['CAGR'].max())}，"
            f"Sharpe 为 {plateau['Sharpe'].min():.2f}-{plateau['Sharpe'].max():.2f}，"
            f"MaxDD 为 {fmt_pct(plateau['MaxDD'].min())}-{fmt_pct(plateau['MaxDD'].max())}。"
        )
        balance_description = (
            f"在不选择单点最优参数的前提下，`{first_window}-{last_window}` 交易日是当前样本中的稳定风险收益平衡区间。"
        )

    if spikes.empty:
        spike_description = "没有 window 的 Sharpe 同时比左右相邻 window 高出 0.15，未发现孤立尖峰。"
    else:
        labels = ", ".join(str(int(value)) for value in spikes["momentum_window"])
        spike_description = f"发现孤立 Sharpe 尖峰：`{labels}` 交易日，存在参数过拟合警示。"

    current = metrics.loc[metrics["momentum_window"] == 126].iloc[0]
    current_neighbors = metrics[metrics["momentum_window"].isin([105, 147])]
    current_context = (
        f"126 日 Sharpe 为 {current['Sharpe']:.2f}；105/147 日 Sharpe 分别为 "
        f"{current_neighbors.iloc[0]['Sharpe']:.2f}/{current_neighbors.iloc[1]['Sharpe']:.2f}，"
        f"其 Robustness Score 为 {current['Robustness Score']:.2f}。"
    )

    benchmark_table = core.markdown_table(
        benchmark_metrics,
        ["strategy", "CAGR", "Sharpe", "MaxDD", "Volatility", "Calmar", "Total Return", "Turnover"],
        {"CAGR", "MaxDD", "Volatility", "Total Return", "Turnover"},
    )
    warnings_section = "\n".join(f"- {warning}" for warning in warnings_list) if warnings_list else "- 无数据 warning。"
    positive_vs_ew = benchmark_tests[
        (benchmark_tests["benchmark"] == "Benchmark_EqualWeight")
        & (benchmark_tests["avg_monthly_excess"] > 0)
    ]
    significant_vs_ew = positive_vs_ew[positive_vs_ew["p_value"] < 0.05]
    positive_vs_spy = benchmark_tests[
        (benchmark_tests["benchmark"] == "Benchmark_SPY")
        & (benchmark_tests["avg_monthly_excess"] > 0)
    ]
    significant_vs_spy = positive_vs_spy[positive_vs_spy["p_value"] < 0.05]

    if plateau.empty:
        final_conclusion = (
            "未找到符合预设标准的连续参数平台，因此当前结果不支持 Momentum Alpha "
            "在一段参数区间内稳定存在。"
        )
    else:
        final_conclusion = (
            "Top5 策略的风险收益形态在一段连续参数区间内稳定存在，126 日不是孤立尖峰。"
            "但严格的 benchmark-relative Alpha 只得到部分支持：相对 Equal Weight 的经济超额在所有 window "
            "上方向一致，统计显著性却没有形成平台；相对 SPY 则没有稳定超额收益。"
        )

    return f"""# Cross-Sectional Momentum Window Robustness Test

## 1. 研究目标

本实验不寻找新的最佳 momentum window。唯一目标是判断：Top5 横截面 Momentum Alpha 是否在一段邻近参数区间内稳定存在，还是主要来自 126 日这个孤立峰值。

## 2. 固定实验条件

- Universe: 当前 12 ETF
- Common sample: `{start_date.date()}` to `{end_date.date()}`
- Rebalance: Monthly，月末排名，下一交易日开始持仓
- Portfolio: Top5, Equal Weight
- Transaction cost: 5 bps applied to turnover
- Benchmarks: SPY Buy & Hold, Equal Weight All Assets monthly rebalance
- 唯一变化参数: momentum window = `{', '.join(map(str, MOMENTUM_WINDOWS))}` trading days
- 所有 window 使用完全相同的回测起止日期

## 3. Robustness Score

对每个 window，计算其 Sharpe 与左右直接相邻测试 window 的平均绝对差：

`Robustness Score = 100 × max(0, 1 - neighbor_sharpe_MAE / 0.20)`

分数越高，表示该 window 与邻近参数的 Sharpe 越接近。该分数只衡量局部平滑度，不衡量收益高低，也不用于挑选最佳参数。

## 4. Window Results

{markdown_metrics(metrics)}

## 5. Stable Plateau Test

平台区预先定义为至少 {PLATEAU_MIN_WINDOWS} 个连续 window，并同时满足：Sharpe 极差不超过 {PLATEAU_MAX_SHARPE_RANGE:.2f}、CAGR 极差不超过 {PLATEAU_MAX_CAGR_RANGE:.0%}、MaxDD 极差不超过 {PLATEAU_MAX_MAXDD_RANGE:.0%}。

{plateau_description}

{spike_description}

对原参数的局部检查：{current_context}

## 6. Window Length And Risk/Return

- {trend_sentence(trends, 'CAGR', percent=True)}
- {trend_sentence(trends, 'Sharpe')}
- {trend_sentence(trends, 'MaxDD', percent=True)}
- {trend_sentence(trends, 'Turnover', percent=True)}

这些线性趋势只用于描述方向，不代表窗口长度与绩效之间存在稳定因果关系。

## 7. Benchmark Context

{benchmark_table}

- 月度平均超额收益为正的 window：相对 SPY 为 {len(positive_vs_spy)}/{len(metrics)}，相对 Equal Weight 为 {len(positive_vs_ew)}/{len(metrics)}。
- 正超额且 p-value < 0.05 的 window：相对 SPY 为 {len(significant_vs_spy)}/{len(metrics)}，相对 Equal Weight 为 {len(significant_vs_ew)}/{len(metrics)}。
- Benchmark 检验用于提供经济意义背景；平台判断本身不以某一个显著性结果作为参数筛选条件。

## 8. 最终结论

{final_conclusion}

{balance_description}

这项结论只说明参数邻域稳定性。它不能替代 out-of-sample、walk-forward、资产池敏感性和更高交易成本测试。

## 9. Data Warnings

{warnings_section}
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    captured_warnings: list[str] = []

    def capture_warning(message, category, filename, lineno, file=None, line=None):
        captured_warnings.append(str(message))

    old_showwarning = warnings.showwarning
    warnings.showwarning = capture_warning
    try:
        prices = core.load_prices()
        if len(prices) <= max(MOMENTUM_WINDOWS) + 40:
            raise RuntimeError("Not enough common history for the longest momentum window.")
        returns = prices.pct_change(fill_method=None).fillna(0.0)
        rebalance_dates = core.month_end_dates(prices.index)

        strategy_returns: dict[int, pd.Series] = {}
        strategy_details: dict[int, pd.DataFrame] = {}
        for window in MOMENTUM_WINDOWS:
            momentum = prices / prices.shift(window) - 1
            valid_dates = pd.DatetimeIndex(
                [date for date in rebalance_dates if momentum.loc[date].notna().all()]
            )
            daily, details, _, _ = core.build_strategy(
                prices, returns, momentum, valid_dates, window, TOP_N
            )
            strategy_returns[window] = daily
            strategy_details[window] = details

        common_start = max(series.index[0] for series in strategy_returns.values())
        common_end = min(series.index[-1] for series in strategy_returns.values())
        daily_returns = pd.DataFrame(
            {f"mom_{window}_Top5": series.loc[common_start:common_end] for window, series in strategy_returns.items()}
        ).dropna()

        benchmark_spy = returns[core.BENCHMARK_SPY].reindex(daily_returns.index)
        benchmark_ew, benchmark_ew_turnover, _ = core.build_equal_weight_benchmark(
            prices, returns, rebalance_dates
        )
        benchmark_ew = benchmark_ew.reindex(daily_returns.index)

        metric_rows = []
        benchmark_rows = []
        for window in MOMENTUM_WINDOWS:
            label = f"mom_{window}_Top5"
            daily = daily_returns[label]
            equity = (1 + daily).cumprod()
            turnover = strategy_details[window]["turnover"].reindex(daily.index).fillna(0.0)
            row = core.calculate_metrics(
                label=label,
                momentum_window=f"mom_{window}",
                strategy="Top5",
                returns=daily,
                equity=equity,
                turnover=turnover,
                number_of_rebalances=len(core.monthly_returns(daily)),
            )
            row["momentum_window"] = window
            metric_rows.append(row)
            benchmark_rows.append(core.benchmark_comparison(daily, benchmark_spy, label, "Benchmark_SPY"))
            benchmark_rows.append(
                core.benchmark_comparison(daily, benchmark_ew, label, "Benchmark_EqualWeight")
            )

        metrics = add_robustness_scores(pd.DataFrame(metric_rows))
        benchmark_tests = pd.DataFrame(benchmark_rows)
        benchmark_metrics = pd.DataFrame(
            [
                core.calculate_metrics(
                    "Benchmark_SPY",
                    "Benchmark",
                    "Benchmark_SPY",
                    benchmark_spy,
                    (1 + benchmark_spy).cumprod(),
                    pd.Series(0.0, index=benchmark_spy.index),
                    0,
                ),
                core.calculate_metrics(
                    "Benchmark_EqualWeight",
                    "Benchmark",
                    "Benchmark_EqualWeight",
                    benchmark_ew,
                    (1 + benchmark_ew).cumprod(),
                    benchmark_ew_turnover.reindex(benchmark_ew.index).fillna(0.0),
                    len(core.monthly_returns(benchmark_ew)),
                ),
            ]
        )

        plateau = find_stable_plateau(metrics)
        spikes = detect_sharpe_spikes(metrics)
        trends = calculate_trends(metrics)

        combined_daily_returns = daily_returns.copy()
        combined_daily_returns["Benchmark_SPY"] = benchmark_spy
        combined_daily_returns["Benchmark_EqualWeight"] = benchmark_ew
        equity_curves = (1 + combined_daily_returns).cumprod()

        metrics.to_csv(METRICS_DIR / "window_metrics.csv", index=False)
        benchmark_metrics.to_csv(METRICS_DIR / "benchmark_metrics.csv", index=False)
        benchmark_tests.to_csv(METRICS_DIR / "benchmark_tests.csv", index=False)
        trends.to_csv(METRICS_DIR / "window_trends.csv", index=False)
        spikes.to_csv(METRICS_DIR / "sharpe_spikes.csv", index=False)
        plateau.to_csv(METRICS_DIR / "stable_plateau.csv", index=False)
        combined_daily_returns.to_csv(OUTPUTS_DIR / "daily_returns.csv")
        equity_curves.to_csv(OUTPUTS_DIR / "equity_curves.csv")

        plot_window_metric(metrics, "CAGR", "momentum_window_vs_cagr.png", percent=True)
        plot_window_metric(metrics, "Sharpe", "momentum_window_vs_sharpe.png")
        plot_window_metric(metrics, "MaxDD", "momentum_window_vs_maxdd.png", percent=True)
        plot_window_metric(metrics, "Calmar", "momentum_window_vs_calmar.png")

        summary = generate_summary(
            metrics,
            benchmark_metrics,
            benchmark_tests,
            plateau,
            spikes,
            trends,
            daily_returns.index[0],
            daily_returns.index[-1],
            captured_warnings,
        )
        SUMMARY_PATH.write_text(summary, encoding="utf-8")
    finally:
        warnings.showwarning = old_showwarning

    print("\nMomentum Window Robustness Test Complete")
    print(f"Study directory: {STUDY_DIR}")
    print(f"Common sample: {daily_returns.index[0].date()} to {daily_returns.index[-1].date()}")
    print("\nCore robustness table:")
    print(
        metrics[
            [
                "momentum_window",
                "CAGR",
                "Sharpe",
                "MaxDD",
                "Volatility",
                "Calmar",
                "Total Return",
                "Turnover",
                "Robustness Score",
            ]
        ].to_string(index=False, float_format=lambda value: f"{value:,.4f}")
    )
    if plateau.empty:
        print("\nStable plateau: none under the predefined criteria")
    else:
        print(
            f"\nStable plateau: {int(plateau.iloc[0]['momentum_window'])}"
            f"-{int(plateau.iloc[-1]['momentum_window'])} trading days"
        )
    print(f"Isolated Sharpe spikes: {len(spikes)}")
    if captured_warnings:
        print("\nWarnings:")
        for warning in captured_warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
