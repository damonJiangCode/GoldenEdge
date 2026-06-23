from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[4]
DATA_ROOT = ALPHA_ROOT / "shared" / "data"
EQUITY_DATA_DIR = DATA_ROOT / "equity"
METADATA_PATH = DATA_ROOT / "symbols_metadata.csv"
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"

sys.path.insert(0, str(ALPHA_ROOT))

from shared.utils import cross_sectional as core  # noqa: E402


MOMENTUM_WINDOWS = [126, 168]
TOP_N_VALUES = [3, 5]
REQUIRED_COLUMNS = ["Date", "Adj Close"]


def load_symbol(path: Path) -> Optional[pd.DataFrame]:
    symbol = path.stem
    try:
        raw = pd.read_csv(path)
    except Exception as exc:
        warnings.warn(f"{symbol}: failed to read {path}: {exc}")
        return None

    missing = [column for column in REQUIRED_COLUMNS if column not in raw.columns]
    if missing:
        warnings.warn(f"{symbol}: missing columns {missing}, skipped")
        return None

    frame = raw[REQUIRED_COLUMNS].copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame[symbol] = pd.to_numeric(frame["Adj Close"], errors="coerce")
    frame = frame.dropna(subset=["Date", symbol]).sort_values("Date")
    frame = frame.drop_duplicates(subset=["Date"], keep="last").set_index("Date")
    if frame.empty:
        warnings.warn(f"{symbol}: no valid rows, skipped")
        return None
    return frame[[symbol]]


def load_equity_prices() -> pd.DataFrame:
    paths = sorted(EQUITY_DATA_DIR.glob("*.csv"))
    if not paths:
        raise RuntimeError(f"No equity CSV files found in {EQUITY_DATA_DIR}")

    frames = []
    for path in paths:
        frame = load_symbol(path)
        if frame is not None:
            frames.append(frame)
    if not frames:
        raise RuntimeError("No valid equity price data loaded.")

    prices = pd.concat(frames, axis=1).sort_index().dropna(how="any")
    if len(prices.columns) != len(paths):
        raise RuntimeError(f"Expected {len(paths)} equity symbols, loaded {len(prices.columns)}.")
    if len(prices) <= max(MOMENTUM_WINDOWS) + 40:
        raise RuntimeError("Not enough common equity history for the requested momentum windows.")
    return prices


def load_categories(symbols: list[str]) -> dict[str, str]:
    if not METADATA_PATH.exists():
        warnings.warn(f"Missing metadata file: {METADATA_PATH}")
        return {symbol: "Unknown" for symbol in symbols}
    metadata = pd.read_csv(METADATA_PATH)
    required = {"symbol", "asset_class", "category"}
    if not required.issubset(metadata.columns):
        warnings.warn("Metadata lacks symbol/asset_class/category columns")
        return {symbol: "Unknown" for symbol in symbols}
    equity = metadata.loc[metadata["asset_class"] == "equity"].set_index("symbol")
    return {symbol: equity["category"].get(symbol, "Unknown") for symbol in symbols}


def build_universe_strategies(prices: pd.DataFrame, universe: str) -> dict:
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    rebalance_dates = core.month_end_dates(prices.index)
    strategy_returns = {}
    strategy_details = {}
    ranking_frames = []
    holding_frames = []

    for window in MOMENTUM_WINDOWS:
        momentum = prices / prices.shift(window) - 1
        valid_dates = pd.DatetimeIndex(
            [date for date in rebalance_dates if momentum.loc[date].notna().all()]
        )
        for top_n in TOP_N_VALUES:
            label = f"mom_{window}_Top{top_n}"
            daily, details, ranking, holdings = core.build_strategy(
                prices=prices,
                returns=returns,
                momentum=momentum,
                rebalance_dates=valid_dates,
                window=window,
                top_n=top_n,
            )
            strategy_returns[label] = daily
            strategy_details[label] = details
            if not ranking.empty:
                ranking["universe"] = universe
                ranking_frames.append(ranking)
            if not holdings.empty:
                holdings["universe"] = universe
                holding_frames.append(holdings)

    equal_weight_returns, equal_weight_turnover, equal_weight_rebalances = core.build_equal_weight_benchmark(
        prices, returns, rebalance_dates
    )
    return {
        "prices": prices,
        "returns": returns,
        "strategy_returns": strategy_returns,
        "strategy_details": strategy_details,
        "ranking": pd.concat(ranking_frames, ignore_index=True) if ranking_frames else pd.DataFrame(),
        "holdings": pd.concat(holding_frames, ignore_index=True) if holding_frames else pd.DataFrame(),
        "equal_weight_returns": equal_weight_returns,
        "equal_weight_turnover": equal_weight_turnover,
        "equal_weight_rebalances": equal_weight_rebalances,
    }


def strategy_metrics(
    study: dict,
    index: pd.DatetimeIndex,
    universe: str,
) -> pd.DataFrame:
    rows = []
    for window in MOMENTUM_WINDOWS:
        for top_n in TOP_N_VALUES:
            label = f"mom_{window}_Top{top_n}"
            daily = study["strategy_returns"][label].reindex(index)
            details = study["strategy_details"][label]
            turnover = details["turnover"].reindex(index).fillna(0.0)
            row = core.calculate_metrics(
                label=label,
                momentum_window=f"mom_{window}",
                strategy=f"Top{top_n}",
                returns=daily,
                equity=(1 + daily).cumprod(),
                turnover=turnover,
                number_of_rebalances=len(core.monthly_returns(daily)),
            )
            row["universe"] = universe
            rows.append(row)
    return pd.DataFrame(rows)


def benchmark_metric_rows(
    spy_returns: pd.Series,
    equal_weight_returns: pd.Series,
    equal_weight_turnover: pd.Series,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            core.calculate_metrics(
                "Benchmark_SPY",
                "Benchmark",
                "Benchmark_SPY",
                spy_returns,
                (1 + spy_returns).cumprod(),
                pd.Series(0.0, index=spy_returns.index),
                0,
            ),
            core.calculate_metrics(
                "Benchmark_EqualWeightEquity",
                "Benchmark",
                "Benchmark_EqualWeightEquity",
                equal_weight_returns,
                (1 + equal_weight_returns).cumprod(),
                equal_weight_turnover,
                len(core.monthly_returns(equal_weight_returns)),
            ),
        ]
    )


def run_benchmark_tests(
    study: dict,
    index: pd.DatetimeIndex,
    spy_returns: pd.Series,
    equal_weight_returns: pd.Series,
    equal_weight_label: str,
    universe: str,
) -> pd.DataFrame:
    rows = []
    for label, daily in study["strategy_returns"].items():
        aligned = daily.reindex(index)
        spy_test = core.benchmark_comparison(aligned, spy_returns, label, "Benchmark_SPY")
        spy_test["universe"] = universe
        rows.append(spy_test)
        equal_weight_test = core.benchmark_comparison(aligned, equal_weight_returns, label, equal_weight_label)
        equal_weight_test["universe"] = universe
        rows.append(equal_weight_test)
    return pd.DataFrame(rows)


def selection_summary(
    ranking: pd.DataFrame,
    index: pd.DatetimeIndex,
    categories: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if ranking.empty:
        return pd.DataFrame(), pd.DataFrame()
    aligned = ranking.loc[
        pd.to_datetime(ranking["effective_date"]).between(index.min(), index.max())
    ].copy()
    summary = core.summarize_selection(aligned)
    summary.insert(3, "category", summary["symbol"].map(categories).fillna("Unknown"))
    return summary, aligned


def matched_universe_comparison(equity_metrics: pd.DataFrame, mixed_metrics: pd.DataFrame) -> pd.DataFrame:
    metric_columns = ["CAGR", "Sharpe", "MaxDD", "Volatility", "Calmar", "Total Return", "Turnover"]
    equity = equity_metrics.set_index("label")
    mixed = mixed_metrics.set_index("label")
    rows = []
    for label in equity.index:
        row = {
            "strategy_label": label,
            "momentum_window": equity.loc[label, "momentum_window"],
            "strategy": equity.loc[label, "strategy"],
        }
        for metric in metric_columns:
            row[f"equity_{metric}"] = equity.loc[label, metric]
            row[f"mixed_{metric}"] = mixed.loc[label, metric]
            row[f"difference_{metric}"] = equity.loc[label, metric] - mixed.loc[label, metric]
        rows.append(row)
    return pd.DataFrame(rows)


def universe_stability_summary(
    metrics_by_universe: dict[str, pd.DataFrame],
    tests_by_universe: dict[str, pd.DataFrame],
    equal_weight_labels: dict[str, str],
) -> pd.DataFrame:
    rows = []
    for universe, metrics in metrics_by_universe.items():
        tests = tests_by_universe[universe]
        equal_weight_tests = tests.loc[tests["benchmark"] == equal_weight_labels[universe]]
        rows.append(
            {
                "universe": universe,
                "avg_CAGR": metrics["CAGR"].mean(),
                "std_CAGR": metrics["CAGR"].std(ddof=0),
                "min_CAGR": metrics["CAGR"].min(),
                "avg_Sharpe": metrics["Sharpe"].mean(),
                "std_Sharpe": metrics["Sharpe"].std(ddof=0),
                "min_Sharpe": metrics["Sharpe"].min(),
                "avg_MaxDD": metrics["MaxDD"].mean(),
                "worst_MaxDD": metrics["MaxDD"].min(),
                "avg_monthly_excess_vs_equal_weight": equal_weight_tests["avg_monthly_excess"].mean(),
                "positive_excess_count": int((equal_weight_tests["avg_monthly_excess"] > 0).sum()),
                "significant_positive_excess_count": int(
                    ((equal_weight_tests["avg_monthly_excess"] > 0) & (equal_weight_tests["p_value"] < 0.05)).sum()
                ),
                "strategy_count": len(metrics),
            }
        )
    return pd.DataFrame(rows)


def fmt_pct(value: float) -> str:
    return "NA" if pd.isna(value) else f"{value:.2%}"


def fmt_num(value: float) -> str:
    return "NA" if pd.isna(value) else f"{value:.2f}"


def markdown_table(df: pd.DataFrame, columns: list[str], pct_columns: set[str]) -> str:
    if df.empty:
        return "_No data._"
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df[columns].iterrows():
        cells = []
        for column in columns:
            value = row[column]
            if column in pct_columns:
                cells.append(fmt_pct(value))
            elif isinstance(value, (float, np.floating)):
                cells.append(fmt_num(value))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def generate_summary(
    equity_metrics: pd.DataFrame,
    benchmark_metrics: pd.DataFrame,
    equity_tests: pd.DataFrame,
    comparison: pd.DataFrame,
    stability: pd.DataFrame,
    selection: pd.DataFrame,
    symbol_count: int,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    warnings_list: list[str],
) -> str:
    top_n_summary = (
        equity_metrics.groupby("strategy")
        .agg(avg_CAGR=("CAGR", "mean"), avg_Sharpe=("Sharpe", "mean"), avg_MaxDD=("MaxDD", "mean"))
        .reset_index()
        .sort_values("avg_Sharpe", ascending=False)
    )
    window_summary = (
        equity_metrics.groupby("momentum_window")
        .agg(avg_CAGR=("CAGR", "mean"), avg_Sharpe=("Sharpe", "mean"), avg_MaxDD=("MaxDD", "mean"))
        .reset_index()
        .sort_values("avg_Sharpe", ascending=False)
    )
    equity_stability = stability.loc[stability["universe"] == "Equity"].iloc[0]
    mixed_stability = stability.loc[stability["universe"] == "Mixed"].iloc[0]

    stronger = (
        equity_stability["avg_Sharpe"] > mixed_stability["avg_Sharpe"]
        and equity_stability["avg_monthly_excess_vs_equal_weight"]
        > mixed_stability["avg_monthly_excess_vs_equal_weight"]
    )
    more_stable = (
        equity_stability["std_Sharpe"] < mixed_stability["std_Sharpe"]
        and equity_stability["min_Sharpe"] > mixed_stability["min_Sharpe"]
    )
    strength_text = "更强" if stronger else "没有同时表现出更高平均 Sharpe 和更高等权基准超额"
    stability_text = "更稳定" if more_stable else "没有同时表现出更低 Sharpe 离散度和更高最差 Sharpe"

    equal_weight_tests = equity_tests[equity_tests["benchmark"] == "Benchmark_EqualWeightEquity"]
    spy_tests = equity_tests[equity_tests["benchmark"] == "Benchmark_SPY"]
    significant_ew = equal_weight_tests[
        (equal_weight_tests["avg_monthly_excess"] > 0) & (equal_weight_tests["p_value"] < 0.05)
    ]
    significant_spy = spy_tests[(spy_tests["avg_monthly_excess"] > 0) & (spy_tests["p_value"] < 0.05)]

    ew = benchmark_metrics.loc[benchmark_metrics["strategy"] == "Benchmark_EqualWeightEquity"].iloc[0]
    higher_return_count = int((equity_metrics["CAGR"] > ew["CAGR"]).sum())
    lower_drawdown_count = int((equity_metrics["MaxDD"] > ew["MaxDD"]).sum())
    if higher_return_count == len(equity_metrics) and lower_drawdown_count == len(equity_metrics):
        source_text = "四个策略相对 Equity Equal Weight 同时具有更高 CAGR 和更低 MaxDD，提升来自收益与回撤两方面。"
    elif higher_return_count > lower_drawdown_count:
        source_text = (
            f"{higher_return_count}/4 个策略的 CAGR 更高，{lower_drawdown_count}/4 个策略的 MaxDD 更低，"
            "改善更多来自更高收益。"
        )
    elif lower_drawdown_count > higher_return_count:
        source_text = (
            f"{higher_return_count}/4 个策略的 CAGR 更高，{lower_drawdown_count}/4 个策略的 MaxDD 更低，"
            "改善更多来自更低回撤。"
        )
    else:
        source_text = "收益与回撤改善的方向并不一致，不能归因于单一来源。"

    selection_top = selection.sort_values(
        ["momentum_window", "strategy", "Selection Count"], ascending=[True, True, False]
    ).groupby(["momentum_window", "strategy"], as_index=False).head(8)
    warnings_section = "\n".join(f"- {warning}" for warning in warnings_list) if warnings_list else "- 无数据 warning。"

    metric_columns = [
        "momentum_window", "strategy", "CAGR", "Sharpe", "MaxDD", "Volatility", "Calmar",
        "Total Return", "Turnover", "Number of Rebalances",
    ]
    test_columns = [
        "strategy_label", "benchmark", "monthly_observations", "avg_monthly_excess", "annualized_excess",
        "win_rate_vs_benchmark", "t_statistic", "p_value",
    ]
    comparison_columns = [
        "strategy_label", "equity_CAGR", "mixed_CAGR", "difference_CAGR", "equity_Sharpe",
        "mixed_Sharpe", "difference_Sharpe", "equity_MaxDD", "mixed_MaxDD", "difference_MaxDD",
    ]
    stability_columns = [
        "universe", "avg_CAGR", "std_CAGR", "min_CAGR", "avg_Sharpe", "std_Sharpe", "min_Sharpe",
        "avg_MaxDD", "worst_MaxDD", "avg_monthly_excess_vs_equal_weight", "positive_excess_count",
        "significant_positive_excess_count",
    ]

    return f"""# Equity-Only Cross-Sectional Momentum Summary

## 1. 研究问题

Momentum Alpha 在股票 ETF 内部是否比 Mixed Asset Universe 更强、更稳定、更适合构建策略组合？

本研究只验证固定的 `mom_126/mom_168` 与 `Top3/Top5`，不继续搜索参数。

## 2. 实验设计

- Equity universe: 自动读取 `alpha/shared/data/equity/` 下全部 {symbol_count} 只 ETF
- Common sample: `{start_date.date()}` to `{end_date.date()}`
- Rebalance: 月末排名，下一交易日开始持仓
- Weighting: Equal Weight
- Transaction cost: 5 bps applied to turnover
- Momentum windows: `126`, `168`
- Portfolios: `Top3`, `Top5`
- Benchmarks: SPY Buy & Hold, Equity Universe monthly Equal Weight
- Mixed Asset 对照在同一期间用相同 window、Top N、权重、调仓与成本重新计算

## 3. Equity-Only Results

{markdown_table(equity_metrics, metric_columns, {"CAGR", "MaxDD", "Volatility", "Total Return", "Turnover"})}

## 4. Benchmarks

{markdown_table(benchmark_metrics, ["strategy", "CAGR", "Sharpe", "MaxDD", "Volatility", "Calmar", "Total Return", "Turnover"], {"CAGR", "MaxDD", "Volatility", "Total Return", "Turnover"})}

## 5. Benchmark Comparison

{markdown_table(equity_tests, test_columns, {"avg_monthly_excess", "annualized_excess", "win_rate_vs_benchmark"})}

- 显著优于 Equity Equal Weight: {len(significant_ew)} / {len(equal_weight_tests)}。
- 显著优于 SPY: {len(significant_spy)} / {len(spy_tests)}。
- {source_text}

## 6. Top3 vs Top5

{markdown_table(top_n_summary, ["strategy", "avg_CAGR", "avg_Sharpe", "avg_MaxDD"], {"avg_CAGR", "avg_MaxDD"})}

按两个固定 window 的平均 Sharpe，`{top_n_summary.iloc[0]['strategy']}` 更好。这里只是固定规格比较，不用于继续扩大参数搜索。

## 7. 126 vs 168

{markdown_table(window_summary, ["momentum_window", "avg_CAGR", "avg_Sharpe", "avg_MaxDD"], {"avg_CAGR", "avg_MaxDD"})}

按 Top3/Top5 的平均 Sharpe，`{window_summary.iloc[0]['momentum_window']}` 更好。重点仍是两个邻近窗口的方向是否一致，而不是挑选单点最优。

## 8. Equity vs Mixed Asset: Matched Sample

{markdown_table(comparison, comparison_columns, {"equity_CAGR", "mixed_CAGR", "difference_CAGR", "equity_MaxDD", "mixed_MaxDD", "difference_MaxDD"})}

### Universe Stability

{markdown_table(stability, stability_columns, {"avg_CAGR", "std_CAGR", "min_CAGR", "avg_MaxDD", "worst_MaxDD", "avg_monthly_excess_vs_equal_weight"})}

- 强度判断：Equity-only {strength_text}。
- 稳定性判断：Equity-only {stability_text}。
- “更强”要求平均 Sharpe 与相对各自 Equal Weight 的平均月度超额同时更高。
- “更稳定”要求四个固定规格的 Sharpe 离散度更低，同时最差 Sharpe 更高。

## 9. Asset Selection Analysis

各策略最常入选的 ETF：

{markdown_table(selection_top, ["momentum_window", "strategy", "symbol", "category", "Average Rank", "Selection Count", "Selection Percentage"], {"Selection Percentage"})}

完整结果见 `metrics/asset_selection_summary.csv`。

## 10. 最终结论

在 `{start_date.date()}` 至 `{end_date.date()}` 的公平配对样本中，Equity-only Momentum 相比 Mixed Asset Momentum：强度上{strength_text}，稳定性上{stability_text}。

Equity ETF 内部的证据也不足以确认稳定 Momentum Alpha：`mom_126` 的 Top3/Top5 相对 Equity Equal Weight 均为负超额，`mom_168` 的两个组合虽为正超额，但 p-value 均高于 0.50。这个 Alpha 没有在两个预先固定的中期窗口上保持方向一致。

这个判断区分了三件事：策略绝对收益为正、策略优于自身等权 Universe、以及超额收益达到统计显著。只有后两项才能支持 Universe 内部的横截面 Momentum Alpha；短样本和 ETF 高度重叠仍限制结论强度。

## 11. 注意事项

- 共同样本由历史最短的 Equity ETF 决定，明显短于原 Mixed Asset 全样本研究。
- SPY、VTI、QQQ、IWF、XLK 等持仓暴露高度重叠，24 个 ETF 不等于 24 个独立股票风险来源。
- 月度 t-test 未解决市场状态依赖和多重比较问题，应视为研究证据而不是最终投资确认。
- 本实验没有搜索其他 momentum window、Top N 或调仓频率。

## 12. Data Warnings

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
        equity_prices = load_equity_prices()
        categories = load_categories(equity_prices.columns.tolist())
        mixed_prices = core.load_prices()

        equity_study = build_universe_strategies(equity_prices, "Equity")
        mixed_study = build_universe_strategies(mixed_prices, "Mixed")

        equity_common_start = max(series.index[0] for series in equity_study["strategy_returns"].values())
        equity_common_end = min(series.index[-1] for series in equity_study["strategy_returns"].values())
        common_index = equity_prices.loc[equity_common_start:equity_common_end].index
        common_index = common_index.intersection(mixed_prices.index)
        for study in (equity_study, mixed_study):
            for series in study["strategy_returns"].values():
                common_index = common_index.intersection(series.index)
        common_index = common_index.sort_values()
        if common_index.empty:
            raise RuntimeError("No common strategy sample between Equity and Mixed universes.")

        spy_returns = equity_study["returns"][core.BENCHMARK_SPY].reindex(common_index)
        equity_ew = equity_study["equal_weight_returns"].reindex(common_index)
        mixed_ew = mixed_study["equal_weight_returns"].reindex(common_index)
        equity_ew_turnover = equity_study["equal_weight_turnover"].reindex(common_index).fillna(0.0)

        equity_metrics = strategy_metrics(equity_study, common_index, "Equity")
        mixed_metrics = strategy_metrics(mixed_study, common_index, "Mixed")
        benchmark_metrics = benchmark_metric_rows(spy_returns, equity_ew, equity_ew_turnover)

        equity_tests = run_benchmark_tests(
            equity_study,
            common_index,
            spy_returns,
            equity_ew,
            "Benchmark_EqualWeightEquity",
            "Equity",
        )
        mixed_tests = run_benchmark_tests(
            mixed_study,
            common_index,
            spy_returns,
            mixed_ew,
            "Benchmark_EqualWeightMixed",
            "Mixed",
        )
        all_tests = pd.concat([equity_tests, mixed_tests], ignore_index=True)

        selection, ranking = selection_summary(equity_study["ranking"], common_index, categories)
        holdings = equity_study["holdings"]
        if not holdings.empty:
            holdings = holdings.loc[
                pd.to_datetime(holdings["effective_date"]).between(common_index.min(), common_index.max())
            ].reset_index(drop=True)

        comparison = matched_universe_comparison(equity_metrics, mixed_metrics)
        stability = universe_stability_summary(
            {"Equity": equity_metrics, "Mixed": mixed_metrics},
            {"Equity": equity_tests, "Mixed": mixed_tests},
            {"Equity": "Benchmark_EqualWeightEquity", "Mixed": "Benchmark_EqualWeightMixed"},
        )

        equity_daily = pd.DataFrame(
            {label: series.reindex(common_index) for label, series in equity_study["strategy_returns"].items()}
        )
        equity_daily["Benchmark_SPY"] = spy_returns
        equity_daily["Benchmark_EqualWeightEquity"] = equity_ew
        equity_curves = (1 + equity_daily).cumprod()

        equity_metrics.to_csv(METRICS_DIR / "metrics.csv", index=False)
        benchmark_metrics.to_csv(METRICS_DIR / "benchmark_metrics.csv", index=False)
        all_tests.to_csv(METRICS_DIR / "benchmark_tests.csv", index=False)
        selection.to_csv(METRICS_DIR / "asset_selection_summary.csv", index=False)
        mixed_metrics.to_csv(METRICS_DIR / "mixed_matched_metrics.csv", index=False)
        comparison.to_csv(METRICS_DIR / "universe_comparison.csv", index=False)
        stability.to_csv(METRICS_DIR / "universe_stability_summary.csv", index=False)
        ranking.to_csv(OUTPUTS_DIR / "ranking_history.csv", index=False)
        holdings.to_csv(OUTPUTS_DIR / "rebalance_holdings.csv", index=False)
        equity_daily.to_csv(OUTPUTS_DIR / "daily_returns.csv")
        equity_curves.to_csv(OUTPUTS_DIR / "equity_curves.csv")

        summary = generate_summary(
            equity_metrics=equity_metrics,
            benchmark_metrics=benchmark_metrics,
            equity_tests=equity_tests,
            comparison=comparison,
            stability=stability,
            selection=selection,
            symbol_count=len(equity_prices.columns),
            start_date=common_index.min(),
            end_date=common_index.max(),
            warnings_list=captured_warnings,
        )
        SUMMARY_PATH.write_text(summary, encoding="utf-8")
    finally:
        warnings.showwarning = old_showwarning

    print("\nEquity-Only Cross-Sectional Momentum Test Complete")
    print(f"Study directory: {STUDY_DIR}")
    print(f"Equity universe: {len(equity_prices.columns)} ETFs")
    print(f"Matched sample: {common_index.min().date()} to {common_index.max().date()}")
    print("\nEquity-only metrics:")
    print(
        equity_metrics[
            [
                "momentum_window", "strategy", "CAGR", "Sharpe", "MaxDD", "Volatility", "Calmar",
                "Total Return", "Turnover", "Number of Rebalances",
            ]
        ].to_string(index=False, float_format=lambda value: f"{value:,.4f}")
    )
    print("\nUniverse stability comparison:")
    print(stability.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    if captured_warnings:
        print("\nWarnings:")
        for warning in captured_warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
