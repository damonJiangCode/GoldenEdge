from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parent
TREND_DIR = STUDY_DIR.parent
ALPHA_ROOT = TREND_DIR.parent
DATA_ROOT = ALPHA_ROOT / "data"
COMMODITY_DATA_DIR = DATA_ROOT / "commodity"
EQUITY_DATA_DIR = DATA_ROOT / "equity"
METADATA_PATH = DATA_ROOT / "symbols_metadata.csv"
RESULTS_DIR = STUDY_DIR / "results"

sys.path.insert(0, str(TREND_DIR / "cross_sectional_momentum"))
import run_cross_sectional_momentum as core  # noqa: E402


MOMENTUM_WINDOWS = [126, 168]
TOP_N_VALUES = [1, 3]
MATCHED_TOP_N = 3
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
        warnings.warn(f"{symbol}: no valid data, skipped")
        return None
    return frame[[symbol]]


def load_universe(directory: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    paths = sorted(directory.glob("*.csv"))
    if not paths:
        raise RuntimeError(f"No CSV files found in {directory}")

    frames = []
    coverage_rows = []
    for path in paths:
        frame = load_symbol(path)
        if frame is None:
            continue
        frames.append(frame)
        coverage_rows.append(
            {
                "symbol": path.stem,
                "actual_start": frame.index.min(),
                "actual_end": frame.index.max(),
                "rows": len(frame),
            }
        )
    if len(frames) != len(paths):
        raise RuntimeError(f"Expected {len(paths)} valid files in {directory}, loaded {len(frames)}.")

    prices = pd.concat(frames, axis=1).sort_index().dropna(how="any")
    if len(prices) <= max(MOMENTUM_WINDOWS) + 40:
        raise RuntimeError(f"Not enough common history in {directory}.")
    return prices, pd.DataFrame(coverage_rows).sort_values("symbol")


def load_categories(symbols: list[str]) -> dict[str, str]:
    if not METADATA_PATH.exists():
        return {symbol: "Unknown" for symbol in symbols}
    metadata = pd.read_csv(METADATA_PATH)
    required = {"symbol", "asset_class", "category"}
    if not required.issubset(metadata.columns):
        warnings.warn("Metadata lacks symbol/asset_class/category columns")
        return {symbol: "Unknown" for symbol in symbols}
    commodity = metadata.loc[metadata["asset_class"] == "commodity"].set_index("symbol")
    return {symbol: commodity["category"].get(symbol, "Unknown") for symbol in symbols}


def build_study(prices: pd.DataFrame, top_n_values: list[int], universe: str) -> dict:
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    rebalance_dates = core.month_end_dates(prices.index)
    strategy_returns = {}
    strategy_details = {}
    rankings = []
    holdings = []

    for window in MOMENTUM_WINDOWS:
        momentum = prices / prices.shift(window) - 1
        valid_dates = pd.DatetimeIndex(
            [date for date in rebalance_dates if momentum.loc[date].notna().all()]
        )
        for top_n in top_n_values:
            label = f"mom_{window}_Top{top_n}"
            daily, details, ranking, selected = core.build_strategy(
                prices, returns, momentum, valid_dates, window, top_n
            )
            strategy_returns[label] = daily
            strategy_details[label] = details
            if not ranking.empty:
                ranking["universe"] = universe
                rankings.append(ranking)
            if not selected.empty:
                selected["universe"] = universe
                holdings.append(selected)

    equal_weight, equal_weight_turnover, _ = core.build_equal_weight_benchmark(
        prices, returns, rebalance_dates
    )
    return {
        "prices": prices,
        "returns": returns,
        "strategy_returns": strategy_returns,
        "strategy_details": strategy_details,
        "ranking": pd.concat(rankings, ignore_index=True) if rankings else pd.DataFrame(),
        "holdings": pd.concat(holdings, ignore_index=True) if holdings else pd.DataFrame(),
        "equal_weight": equal_weight,
        "equal_weight_turnover": equal_weight_turnover,
    }


def common_strategy_index(study: dict) -> pd.DatetimeIndex:
    start = max(series.index.min() for series in study["strategy_returns"].values())
    end = min(series.index.max() for series in study["strategy_returns"].values())
    index = study["prices"].loc[start:end].index
    for series in study["strategy_returns"].values():
        index = index.intersection(series.index)
    return index.sort_values()


def calculate_strategy_metrics(study: dict, index: pd.DatetimeIndex, universe: str) -> pd.DataFrame:
    rows = []
    for label, daily_returns in study["strategy_returns"].items():
        window_text, top_text = label.split("_Top")
        aligned = daily_returns.reindex(index)
        turnover = study["strategy_details"][label]["turnover"].reindex(index).fillna(0.0)
        row = core.calculate_metrics(
            label,
            window_text,
            f"Top{top_text}",
            aligned,
            (1 + aligned).cumprod(),
            turnover,
            len(core.monthly_returns(aligned)),
        )
        row["universe"] = universe
        rows.append(row)
    return pd.DataFrame(rows)


def benchmark_metrics(
    commodity_equal_weight: pd.Series,
    commodity_turnover: pd.Series,
    spy: pd.Series,
    qqq: pd.Series,
) -> pd.DataFrame:
    rows = []
    specifications = [
        ("Benchmark_CommodityEqualWeight", commodity_equal_weight, commodity_turnover),
        ("Benchmark_SPY", spy, pd.Series(0.0, index=spy.index)),
        ("Benchmark_QQQ", qqq, pd.Series(0.0, index=qqq.index)),
    ]
    for label, returns, turnover in specifications:
        rows.append(
            core.calculate_metrics(
                label,
                "Benchmark",
                label,
                returns,
                (1 + returns).cumprod(),
                turnover,
                len(core.monthly_returns(returns)) if "EqualWeight" in label else 0,
            )
        )
    return pd.DataFrame(rows)


def benchmark_tests(
    study: dict,
    index: pd.DatetimeIndex,
    benchmarks: dict[str, pd.Series],
    universe: str,
) -> pd.DataFrame:
    rows = []
    for label, daily in study["strategy_returns"].items():
        aligned = daily.reindex(index)
        for benchmark_label, benchmark_returns in benchmarks.items():
            row = core.benchmark_comparison(
                aligned, benchmark_returns.reindex(index), label, benchmark_label
            )
            row["universe"] = universe
            rows.append(row)
    return pd.DataFrame(rows)


def summarize_selection(
    ranking: pd.DataFrame,
    index: pd.DatetimeIndex,
    categories: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    aligned = ranking.loc[
        pd.to_datetime(ranking["effective_date"]).between(index.min(), index.max())
    ].copy()
    summary = core.summarize_selection(aligned)
    summary.insert(3, "category", summary["symbol"].map(categories).fillna("Unknown"))
    return summary, aligned


def matched_comparison(
    commodity_metrics: pd.DataFrame,
    equity_metrics: pd.DataFrame,
) -> pd.DataFrame:
    metrics = ["CAGR", "Sharpe", "MaxDD", "Volatility", "Calmar", "Total Return", "Turnover"]
    commodity = commodity_metrics.set_index("label")
    equity = equity_metrics.set_index("label")
    rows = []
    for label in commodity.index.intersection(equity.index):
        row = {
            "strategy_label": label,
            "momentum_window": commodity.loc[label, "momentum_window"],
            "strategy": commodity.loc[label, "strategy"],
        }
        for metric in metrics:
            row[f"commodity_{metric}"] = commodity.loc[label, metric]
            row[f"equity_{metric}"] = equity.loc[label, metric]
            row[f"difference_{metric}"] = commodity.loc[label, metric] - equity.loc[label, metric]
        rows.append(row)
    return pd.DataFrame(rows)


def matched_stability(
    commodity_metrics: pd.DataFrame,
    equity_metrics: pd.DataFrame,
    commodity_tests: pd.DataFrame,
    equity_tests: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    specifications = [
        ("Commodity", commodity_metrics, commodity_tests, "Benchmark_CommodityEqualWeight"),
        ("Equity", equity_metrics, equity_tests, "Benchmark_EqualWeightEquity"),
    ]
    for universe, metrics, tests, benchmark_label in specifications:
        excess = tests.loc[tests["benchmark"] == benchmark_label]
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
                "avg_monthly_excess_vs_equal_weight": excess["avg_monthly_excess"].mean(),
                "positive_excess_count": int((excess["avg_monthly_excess"] > 0).sum()),
                "significant_positive_excess_count": int(
                    ((excess["avg_monthly_excess"] > 0) & (excess["p_value"] < 0.05)).sum()
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
    coverage: pd.DataFrame,
    metrics: pd.DataFrame,
    benchmarks: pd.DataFrame,
    tests: pd.DataFrame,
    selection: pd.DataFrame,
    comparison: pd.DataFrame,
    stability: pd.DataFrame,
    matched_start: pd.Timestamp,
    strategy_start: pd.Timestamp,
    strategy_end: pd.Timestamp,
    warnings_list: list[str],
) -> str:
    top_summary = (
        metrics.groupby("strategy")
        .agg(avg_CAGR=("CAGR", "mean"), avg_Sharpe=("Sharpe", "mean"), avg_MaxDD=("MaxDD", "mean"))
        .reset_index().sort_values("avg_Sharpe", ascending=False)
    )
    window_summary = (
        metrics.groupby("momentum_window")
        .agg(avg_CAGR=("CAGR", "mean"), avg_Sharpe=("Sharpe", "mean"), avg_MaxDD=("MaxDD", "mean"))
        .reset_index().sort_values("avg_Sharpe", ascending=False)
    )
    commodity_ew_tests = tests[
        (tests["universe"] == "CommodityFull")
        & (tests["benchmark"] == "Benchmark_CommodityEqualWeight")
    ]
    positive_ew = commodity_ew_tests[commodity_ew_tests["avg_monthly_excess"] > 0]
    significant_ew = positive_ew[positive_ew["p_value"] < 0.05]
    commodity_ew_metric = benchmarks.loc[
        benchmarks["strategy"] == "Benchmark_CommodityEqualWeight"
    ].iloc[0]
    cagr_outperform_count = int((metrics["CAGR"] > commodity_ew_metric["CAGR"]).sum())

    commodity_stability = stability.loc[stability["universe"] == "Commodity"].iloc[0]
    equity_stability = stability.loc[stability["universe"] == "Equity"].iloc[0]
    stronger_than_equity = (
        commodity_stability["avg_Sharpe"] > equity_stability["avg_Sharpe"]
        and commodity_stability["avg_monthly_excess_vs_equal_weight"]
        > equity_stability["avg_monthly_excess_vs_equal_weight"]
    )
    more_stable_than_equity = (
        commodity_stability["std_Sharpe"] < equity_stability["std_Sharpe"]
        and commodity_stability["min_Sharpe"] > equity_stability["min_Sharpe"]
    )

    spy = benchmarks.loc[benchmarks["strategy"] == "Benchmark_SPY"].iloc[0]
    qqq = benchmarks.loc[benchmarks["strategy"] == "Benchmark_QQQ"].iloc[0]
    avg_strategy_sharpe = metrics["Sharpe"].mean()
    market_context = (
        f"Commodity 策略平均 Sharpe 为 {avg_strategy_sharpe:.2f}，SPY/QQQ 分别为 "
        f"{spy['Sharpe']:.2f}/{qqq['Sharpe']:.2f}。"
    )

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
        "strategy_label", "commodity_CAGR", "equity_CAGR", "difference_CAGR", "commodity_Sharpe",
        "equity_Sharpe", "difference_Sharpe", "commodity_MaxDD", "equity_MaxDD", "difference_MaxDD",
    ]
    stability_columns = [
        "universe", "avg_CAGR", "std_CAGR", "min_CAGR", "avg_Sharpe", "std_Sharpe", "min_Sharpe",
        "avg_MaxDD", "worst_MaxDD", "avg_monthly_excess_vs_equal_weight", "positive_excess_count",
        "significant_positive_excess_count",
    ]

    if len(positive_ew) == len(commodity_ew_tests):
        alpha_direction = "四个固定规格的平均月度超额都为正，方向一致"
    else:
        alpha_direction = (
            f"{len(positive_ew)}/4 个固定规格的平均月度超额为正，方向不完全一致"
        )
    alpha_significance = (
        f"其中 {len(significant_ew)}/4 在 5% 水平显著"
        if len(significant_ew)
        else "但没有规格在 5% 水平显著"
    )

    return f"""# Commodity-Only Cross-Sectional Momentum Summary

## 1. 研究问题

Commodity ETF 内部是否存在稳定的 Cross-Sectional Momentum Alpha，并且是否比 Equity ETF Universe 更强、更稳定？

本研究只验证预先固定的 `mom_126/mom_168` 与 `Top1/Top3`，不继续搜索参数。

## 2. Universe And Sample

- Commodity ETFs: {len(coverage)}
- Earliest Start Date: `{coverage['actual_start'].min().date()}`
- Common Start Date: `{coverage['actual_start'].max().date()}`
- Common End Date: `{coverage['actual_end'].min().date()}`
- Strategy sample after 168-day lookback: `{strategy_start.date()}` to `{strategy_end.date()}`
- Monthly rebalance; month-end ranking; next trading day execution
- Equal Weight; transaction cost 5 bps

## 3. Commodity Strategy Results

{markdown_table(metrics, metric_columns, {"CAGR", "MaxDD", "Volatility", "Total Return", "Turnover"})}

## 4. Benchmarks

{markdown_table(benchmarks, ["strategy", "CAGR", "Sharpe", "MaxDD", "Volatility", "Calmar", "Total Return", "Turnover"], {"CAGR", "MaxDD", "Volatility", "Total Return", "Turnover"})}

## 5. Benchmark Comparison

{markdown_table(tests[tests['universe'] == 'CommodityFull'], test_columns, {"avg_monthly_excess", "annualized_excess", "win_rate_vs_benchmark"})}

- Commodity Equal Weight: {alpha_direction}，{alpha_significance}。
- 按最终复合收益计算，只有 {cagr_outperform_count}/4 个规格的 CAGR 高于 Commodity Equal Weight。算术月度超额为正不保证复合财富更高。
- {market_context}

## 6. Top1 vs Top3

{markdown_table(top_summary, ["strategy", "avg_CAGR", "avg_Sharpe", "avg_MaxDD"], {"avg_CAGR", "avg_MaxDD"})}

按两个固定 window 的平均 Sharpe，`{top_summary.iloc[0]['strategy']}` 更好。Top1 集中度更高，应同时检查其回撤和换手。

## 7. 126 vs 168

{markdown_table(window_summary, ["momentum_window", "avg_CAGR", "avg_Sharpe", "avg_MaxDD"], {"avg_CAGR", "avg_MaxDD"})}

按 Top1/Top3 的平均 Sharpe，`{window_summary.iloc[0]['momentum_window']}` 更好。重点是两个 window 的 Alpha 方向是否一致，不是挑选单点最优。

## 8. Commodity vs Equity: Matched Top3 Comparison

为了公平比较，只比较双方共有的 `Top3 × mom_126/mom_168`，并使用完全相同的 `{matched_start.date()}` 至 `{strategy_end.date()}` 样本。

{markdown_table(comparison, comparison_columns, {"commodity_CAGR", "equity_CAGR", "difference_CAGR", "commodity_MaxDD", "equity_MaxDD", "difference_MaxDD"})}

### Stability

{markdown_table(stability, stability_columns, {"avg_CAGR", "std_CAGR", "min_CAGR", "avg_MaxDD", "worst_MaxDD", "avg_monthly_excess_vs_equal_weight"})}

- Commodity 强度是否高于 Equity: {'是' if stronger_than_equity else '否'}。
- Commodity 稳定性是否高于 Equity: {'是' if more_stable_than_equity else '否'}。
- 强度要求平均 Sharpe 与相对各自 Equal Weight 的平均月度超额同时更高。
- 稳定性要求两个 window 的 Sharpe 离散度更低，且最差 Sharpe 更高。

## 9. Asset Selection Analysis

{markdown_table(selection_top, ["momentum_window", "strategy", "symbol", "category", "Average Rank", "Selection Count", "Selection Percentage"], {"Selection Percentage"})}

完整结果见 `asset_selection_summary.csv`。

## 10. 最终结论

Commodity ETF 内部 Momentum Alpha 的方向性证据为：{alpha_direction}，{alpha_significance}。

从可投资的复合结果看，证据更弱：只有 {cagr_outperform_count}/4 个规格的 CAGR 高于 Commodity Equal Weight，Top1 的高波动和严重回撤造成明显复利损耗。因此不支持“Commodity 内部存在稳定、可直接组合化的 Momentum Alpha”。

在同期、同 window、同 Top3 规则下，Commodity 相对 Equity 的强度判断为 `{'stronger' if stronger_than_equity else 'not stronger'}`，稳定性判断为 `{'more stable' if more_stable_than_equity else 'not more stable'}`。{market_context}

Commodity Top3 相对自身 Equal Weight 的月度超额比 Equity Top3 更明显，但这一选择效应被更高波动、更深回撤和更低 Sharpe 抵消，不足以得出 Commodity Universe 更适合构建策略的结论。

是否更适合构建策略，不只取决于绝对收益；还必须同时满足相对 Commodity Equal Weight 的超额方向一致、风险调整收益足够高，以及结果不被个别 Commodity ETF 反复主导。

## 11. 注意事项

- `XOP` 是能源股 ETF，而非商品期货 ETF；它按当前数据 Universe 要求保留。
- 多个农产品和能源 ETF 存在期货展期损益，Momentum 结果包含期限结构效应。
- 月度 t-test 未解决市场状态依赖和多重比较问题。
- 本实验没有搜索其他 window、Top N 或调仓频率。

## 12. Data Warnings

{warnings_section}
"""


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    captured_warnings: list[str] = []

    def capture_warning(message, category, filename, lineno, file=None, line=None):
        captured_warnings.append(str(message))

    old_showwarning = warnings.showwarning
    warnings.showwarning = capture_warning
    try:
        commodity_prices, coverage = load_universe(COMMODITY_DATA_DIR)
        categories = load_categories(commodity_prices.columns.tolist())
        commodity_study = build_study(commodity_prices, TOP_N_VALUES, "CommodityFull")
        strategy_index = common_strategy_index(commodity_study)

        spy_frame = load_symbol(EQUITY_DATA_DIR / "SPY.csv")
        qqq_frame = load_symbol(EQUITY_DATA_DIR / "QQQ.csv")
        if spy_frame is None or qqq_frame is None:
            raise RuntimeError("SPY or QQQ benchmark data unavailable.")
        spy = spy_frame["SPY"].pct_change(fill_method=None).fillna(0.0).reindex(strategy_index)
        qqq = qqq_frame["QQQ"].pct_change(fill_method=None).fillna(0.0).reindex(strategy_index)
        commodity_ew = commodity_study["equal_weight"].reindex(strategy_index)
        commodity_turnover = commodity_study["equal_weight_turnover"].reindex(strategy_index).fillna(0.0)

        metrics = calculate_strategy_metrics(commodity_study, strategy_index, "CommodityFull")
        benchmarks = benchmark_metrics(commodity_ew, commodity_turnover, spy, qqq)
        full_tests = benchmark_tests(
            commodity_study,
            strategy_index,
            {
                "Benchmark_CommodityEqualWeight": commodity_ew,
                "Benchmark_SPY": spy,
                "Benchmark_QQQ": qqq,
            },
            "CommodityFull",
        )
        selection, ranking = summarize_selection(
            commodity_study["ranking"], strategy_index, categories
        )
        holdings = commodity_study["holdings"]
        holdings = holdings.loc[
            pd.to_datetime(holdings["effective_date"]).between(strategy_index.min(), strategy_index.max())
        ].reset_index(drop=True)

        equity_prices, _ = load_universe(EQUITY_DATA_DIR)
        equity_study = build_study(equity_prices, [MATCHED_TOP_N], "EquityMatched")
        commodity_top3_study = build_study(commodity_prices, [MATCHED_TOP_N], "CommodityMatched")
        matched_start = max(
            common_strategy_index(equity_study).min(),
            common_strategy_index(commodity_top3_study).min(),
        )
        matched_end = min(
            common_strategy_index(equity_study).max(),
            common_strategy_index(commodity_top3_study).max(),
        )
        matched_index = equity_prices.loc[matched_start:matched_end].index.intersection(
            commodity_prices.loc[matched_start:matched_end].index
        )
        for study in (equity_study, commodity_top3_study):
            for series in study["strategy_returns"].values():
                matched_index = matched_index.intersection(series.index)
        matched_index = matched_index.sort_values()

        commodity_matched_metrics = calculate_strategy_metrics(
            commodity_top3_study, matched_index, "Commodity"
        )
        equity_matched_metrics = calculate_strategy_metrics(equity_study, matched_index, "Equity")
        commodity_matched_ew = commodity_top3_study["equal_weight"].reindex(matched_index)
        equity_matched_ew = equity_study["equal_weight"].reindex(matched_index)
        commodity_matched_tests = benchmark_tests(
            commodity_top3_study,
            matched_index,
            {"Benchmark_CommodityEqualWeight": commodity_matched_ew},
            "Commodity",
        )
        equity_matched_tests = benchmark_tests(
            equity_study,
            matched_index,
            {"Benchmark_EqualWeightEquity": equity_matched_ew},
            "Equity",
        )
        comparison = matched_comparison(commodity_matched_metrics, equity_matched_metrics)
        stability = matched_stability(
            commodity_matched_metrics,
            equity_matched_metrics,
            commodity_matched_tests,
            equity_matched_tests,
        )
        all_tests = pd.concat(
            [full_tests, commodity_matched_tests, equity_matched_tests], ignore_index=True
        )

        daily_returns = pd.DataFrame(
            {label: series.reindex(strategy_index) for label, series in commodity_study["strategy_returns"].items()}
        )
        daily_returns["Benchmark_CommodityEqualWeight"] = commodity_ew
        daily_returns["Benchmark_SPY"] = spy
        daily_returns["Benchmark_QQQ"] = qqq
        equity_curves = (1 + daily_returns).cumprod()

        coverage.to_csv(RESULTS_DIR / "data_coverage.csv", index=False)
        metrics.to_csv(RESULTS_DIR / "metrics.csv", index=False)
        benchmarks.to_csv(RESULTS_DIR / "benchmark_metrics.csv", index=False)
        all_tests.to_csv(RESULTS_DIR / "benchmark_tests.csv", index=False)
        selection.to_csv(RESULTS_DIR / "asset_selection_summary.csv", index=False)
        ranking.to_csv(RESULTS_DIR / "ranking_history.csv", index=False)
        holdings.to_csv(RESULTS_DIR / "rebalance_holdings.csv", index=False)
        commodity_matched_metrics.to_csv(RESULTS_DIR / "commodity_matched_metrics.csv", index=False)
        equity_matched_metrics.to_csv(RESULTS_DIR / "equity_matched_metrics.csv", index=False)
        comparison.to_csv(RESULTS_DIR / "universe_comparison.csv", index=False)
        stability.to_csv(RESULTS_DIR / "universe_stability_summary.csv", index=False)
        daily_returns.to_csv(RESULTS_DIR / "daily_returns.csv")
        equity_curves.to_csv(RESULTS_DIR / "equity_curves.csv")

        summary = generate_summary(
            coverage,
            metrics,
            benchmarks,
            all_tests,
            selection,
            comparison,
            stability,
            matched_index.min(),
            strategy_index.min(),
            strategy_index.max(),
            captured_warnings,
        )
        (RESULTS_DIR / "summary.md").write_text(summary, encoding="utf-8")
    finally:
        warnings.showwarning = old_showwarning

    print("\nCommodity-Only Cross-Sectional Momentum Test Complete")
    print(f"Results directory: {RESULTS_DIR}")
    print(f"Commodity universe: {len(commodity_prices.columns)} ETFs")
    print(f"Earliest start: {coverage['actual_start'].min().date()}")
    print(f"Common start: {coverage['actual_start'].max().date()}")
    print(f"Common end: {coverage['actual_end'].min().date()}")
    print(f"Strategy sample: {strategy_index.min().date()} to {strategy_index.max().date()}")
    print("\nCommodity metrics:")
    print(
        metrics[
            [
                "momentum_window", "strategy", "CAGR", "Sharpe", "MaxDD", "Volatility", "Calmar",
                "Total Return", "Turnover", "Number of Rebalances",
            ]
        ].to_string(index=False, float_format=lambda value: f"{value:,.4f}")
    )
    print("\nMatched Commodity vs Equity stability:")
    print(stability.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    if captured_warnings:
        print("\nWarnings:")
        for warning in captured_warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
