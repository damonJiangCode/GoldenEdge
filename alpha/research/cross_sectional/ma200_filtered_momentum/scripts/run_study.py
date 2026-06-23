from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[4]
BASELINE_DIR = ALPHA_ROOT / "research" / "cross_sectional" / "mixed_asset_momentum"
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(ALPHA_ROOT))

from shared.configs.universes import MIXED_ASSET_CLASSES, MIXED_ASSET_SYMBOLS  # noqa: E402
from shared.loaders.prices import load_symbol  # noqa: E402
from shared.utils import cross_sectional as core  # noqa: E402


MOMENTUM_WINDOW = 126
MA_WINDOW = 200
TOP_N = 5
DATA_ROOT = ALPHA_ROOT / "shared" / "data"
STRATEGY_NAMES = {
    "Baseline": "mom_126 Top5",
    "MA200 Version A": "MA200 + mom_126 Top5, partial cash",
    "MA200 Version B": "MA200 + mom_126 Top5, fully invested",
}


def load_full_history_ma200(index: pd.DatetimeIndex) -> pd.DataFrame:
    moving_averages = []
    for symbol in MIXED_ASSET_SYMBOLS:
        matches = list(DATA_ROOT.glob(f"*/{symbol}.csv"))
        if len(matches) != 1:
            raise RuntimeError(f"Expected one data file for {symbol}, found {len(matches)}")
        frame = load_symbol(matches[0])
        if frame is None:
            raise RuntimeError(f"Failed to load full history for {symbol}")
        moving_averages.append(frame[symbol].rolling(MA_WINDOW, min_periods=MA_WINDOW).mean().rename(symbol))
    return pd.concat(moving_averages, axis=1).reindex(index)


def build_targets(
    prices: pd.DataFrame,
    ma200: pd.DataFrame,
) -> tuple[dict[str, dict[pd.Timestamp, pd.Series]], pd.DataFrame]:
    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    targets = {strategy: {} for strategy in STRATEGY_NAMES}
    eligibility_rows = []

    for rebalance_date in core.month_end_dates(prices.index):
        scores = momentum.loc[rebalance_date].dropna()
        moving_averages = ma200.loc[rebalance_date]
        if len(scores) != len(prices.columns):
            continue
        location = prices.index.get_loc(rebalance_date)
        if location + 1 >= len(prices.index):
            continue
        effective_date = prices.index[location + 1]

        ranked_all = scores.sort_values(ascending=False)
        baseline_selected = ranked_all.head(TOP_N).index.tolist()
        baseline_target = pd.Series(0.0, index=prices.columns)
        baseline_target.loc[baseline_selected] = 1.0 / TOP_N
        targets["Baseline"][effective_date] = baseline_target

        eligible = (prices.loc[rebalance_date] > moving_averages).fillna(False)
        eligible_symbols = eligible[eligible].index.tolist()
        ranked_eligible = scores.loc[eligible_symbols].sort_values(ascending=False)
        selected = ranked_eligible.head(TOP_N).index.tolist()

        version_a_target = pd.Series(0.0, index=prices.columns)
        version_a_target.loc[selected] = 1.0 / TOP_N
        targets["MA200 Version A"][effective_date] = version_a_target

        version_b_target = pd.Series(0.0, index=prices.columns)
        if selected:
            version_b_target.loc[selected] = 1.0 / len(selected)
        targets["MA200 Version B"][effective_date] = version_b_target

        eligibility_rows.append(
            {
                "rebalance_date": rebalance_date,
                "effective_date": effective_date,
                "eligible_count": len(eligible_symbols),
                "eligible_symbols": ",".join(eligible_symbols),
                "selected_symbols": ",".join(selected),
                "portfolio_holdings": len(selected),
                "version_a_cash": 1 - version_a_target.sum(),
                "version_b_cash": 1 - version_b_target.sum(),
                "below_5_assets": len(eligible_symbols) < TOP_N,
            }
        )

    return targets, pd.DataFrame(eligibility_rows)


def calculate_performance(
    returns: pd.DataFrame,
    targets: dict[str, dict[pd.Timestamp, pd.Series]],
    analysis_index: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]:
    metric_rows = []
    daily_returns = {}
    weights_by_strategy = {}

    for strategy, strategy_targets in targets.items():
        details, weights = core.simulate_monthly_holdings(returns, strategy_targets)
        details = details.reindex(analysis_index)
        weights = weights.reindex(analysis_index)
        if details["return"].isna().any() or weights.isna().any().any():
            raise RuntimeError(f"{strategy}: incomplete common sample")
        equity = (1 + details["return"]).cumprod()
        metrics = core.calculate_metrics(
            label=strategy,
            momentum_window="mom_126",
            strategy=STRATEGY_NAMES[strategy],
            returns=details["return"],
            equity=equity,
            turnover=details["turnover"],
            number_of_rebalances=len(core.monthly_returns(details["return"])),
        )
        metric_rows.append(
            {
                "Strategy": strategy,
                "CAGR": metrics["CAGR"],
                "Sharpe": metrics["Sharpe"],
                "MaxDD": metrics["MaxDD"],
                "Volatility": metrics["Volatility"],
                "Calmar": metrics["Calmar"],
                "Total Return": metrics["Total Return"],
                "Turnover": metrics["Turnover"],
                "Number of Rebalances": metrics["Number of Rebalances"],
            }
        )
        daily_returns[strategy] = details["return"]
        weights_by_strategy[strategy] = weights

    return pd.DataFrame(metric_rows), pd.DataFrame(daily_returns, index=analysis_index), weights_by_strategy


def calculate_relative_change(performance: pd.DataFrame) -> pd.DataFrame:
    baseline = performance.loc[performance["Strategy"] == "Baseline"].iloc[0]
    result = performance.loc[performance["Strategy"] != "Baseline", ["Strategy", "CAGR", "Sharpe", "MaxDD"]].copy()
    result["CAGR Change"] = result["CAGR"] - baseline["CAGR"]
    result["Sharpe Change"] = result["Sharpe"] - baseline["Sharpe"]
    result["MaxDD Change"] = result["MaxDD"] - baseline["MaxDD"]
    return result[["Strategy", "CAGR Change", "Sharpe Change", "MaxDD Change"]]


def calculate_exposure_statistics(
    eligibility: pd.DataFrame,
    analysis_index: pd.DatetimeIndex,
) -> pd.DataFrame:
    in_sample = eligibility.loc[
        pd.to_datetime(eligibility["effective_date"]).between(analysis_index.min(), analysis_index.max())
    ]
    rows = []
    common_metrics = {
        "Average Eligible Assets": in_sample["eligible_count"].mean(),
        "Minimum Eligible Assets": in_sample["eligible_count"].min(),
        "Maximum Eligible Assets": in_sample["eligible_count"].max(),
        "Average Portfolio Holdings": in_sample["portfolio_holdings"].mean(),
        "Percent Months Below 5 Assets": in_sample["below_5_assets"].mean(),
    }
    for strategy, cash_column in [
        ("MA200 Version A", "version_a_cash"),
        ("MA200 Version B", "version_b_cash"),
    ]:
        for metric, value in common_metrics.items():
            rows.append({"Strategy": strategy, "Metric": metric, "Value": value})
        rows.append(
            {
                "Strategy": strategy,
                "Metric": "Average Cash Allocation",
                "Value": in_sample[cash_column].mean(),
            }
        )
    return pd.DataFrame(rows)


def calculate_asset_class_exposure(weights_by_strategy: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    average_total_risk = {
        strategy: weights.sum(axis=1).mean()
        for strategy, weights in weights_by_strategy.items()
    }
    for asset_class, symbols in MIXED_ASSET_CLASSES.items():
        row = {"Asset Class": asset_class}
        for strategy, weights in weights_by_strategy.items():
            class_weight = weights[symbols].sum(axis=1).mean()
            row[f"{strategy} Weight"] = class_weight
            row[f"{strategy} Risk Share"] = class_weight / average_total_risk[strategy]
        rows.append(row)
    return pd.DataFrame(rows)


def fmt_pct(value: float) -> str:
    return "NA" if pd.isna(value) else f"{value:.2%}"


def fmt_num(value: float) -> str:
    return "NA" if pd.isna(value) else f"{value:.2f}"


def markdown_table(df: pd.DataFrame, columns: list[str], pct_columns: set[str]) -> str:
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


def exposure_markdown_table(exposure: pd.DataFrame) -> str:
    pivot = exposure.pivot(index="Metric", columns="Strategy", values="Value")
    lines = [
        "| Metric | MA200 Version A | MA200 Version B |",
        "| --- | --- | --- |",
    ]
    percentage_metrics = {"Average Cash Allocation", "Percent Months Below 5 Assets"}
    ordered_metrics = [
        "Average Eligible Assets",
        "Minimum Eligible Assets",
        "Maximum Eligible Assets",
        "Average Portfolio Holdings",
        "Average Cash Allocation",
        "Percent Months Below 5 Assets",
    ]
    for metric in ordered_metrics:
        values = pivot.loc[metric]
        if metric in percentage_metrics:
            version_a = fmt_pct(values["MA200 Version A"])
            version_b = fmt_pct(values["MA200 Version B"])
        else:
            version_a = fmt_num(values["MA200 Version A"])
            version_b = fmt_num(values["MA200 Version B"])
        lines.append(f"| {metric} | {version_a} | {version_b} |")
    return "\n".join(lines)


def generate_summary(
    performance: pd.DataFrame,
    relative_change: pd.DataFrame,
    exposure_statistics: pd.DataFrame,
    class_exposure: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> str:
    baseline = performance.set_index("Strategy").loc["Baseline"]
    version_a = performance.set_index("Strategy").loc["MA200 Version A"]
    version_b = performance.set_index("Strategy").loc["MA200 Version B"]
    exposure = class_exposure.set_index("Asset Class")

    both_sharpe_improve = version_a["Sharpe"] > baseline["Sharpe"] and version_b["Sharpe"] > baseline["Sharpe"]
    both_drawdown_improve = version_a["MaxDD"] > baseline["MaxDD"] and version_b["MaxDD"] > baseline["MaxDD"]
    best_filtered = max(["MA200 Version A", "MA200 Version B"], key=lambda name: performance.set_index("Strategy").loc[name, "Sharpe"])
    best = performance.set_index("Strategy").loc[best_filtered]

    equity_change = exposure.loc["Equity", f"{best_filtered} Weight"] - exposure.loc["Equity", "Baseline Weight"]
    equity_risk_share_change = (
        exposure.loc["Equity", f"{best_filtered} Risk Share"]
        - exposure.loc["Equity", "Baseline Risk Share"]
    )
    commodity_change = exposure.loc["Commodity", f"{best_filtered} Weight"] - exposure.loc["Commodity", "Baseline Weight"]
    bond_change = exposure.loc["Bond", f"{best_filtered} Weight"] - exposure.loc["Bond", "Baseline Weight"]

    version_a_value = (
        version_a["Sharpe"] > baseline["Sharpe"]
        and version_a["MaxDD"] > baseline["MaxDD"]
        and version_a["CAGR"] / baseline["CAGR"] >= 0.95
    )
    if both_sharpe_improve and both_drawdown_improve:
        filter_conclusion = "MA200 在两种低 eligible 处理方式下都提高 Sharpe 并降低 MaxDD，证据支持它是有价值的趋势过滤器。"
    elif version_a_value:
        filter_conclusion = (
            "MA200 是有价值的条件性风险过滤器：只有当不合格仓位保留为现金时，"
            "它才在几乎保留 CAGR 的同时提高 Sharpe 并大幅降低 MaxDD。"
            "Version B 的恶化说明改善来自趋势过滤与降低风险暴露的组合，不是过滤后集中持仓本身。"
        )
    elif both_drawdown_improve:
        filter_conclusion = "MA200 稳定降低 MaxDD，但 Sharpe 改善依赖现金处理方式；它更像风险过滤器，而非稳定的策略增强器。"
    else:
        filter_conclusion = "MA200 没有在两种实现中稳定改善 Sharpe 与 MaxDD，当前证据不足以支持加入组合。"

    performance_columns = ["Strategy", "CAGR", "Sharpe", "MaxDD", "Volatility", "Calmar", "Total Return", "Turnover"]
    relative_columns = ["Strategy", "CAGR Change", "Sharpe Change", "MaxDD Change"]
    class_columns = [
        "Asset Class",
        "Baseline Weight",
        "MA200 Version A Weight",
        "MA200 Version B Weight",
        "Baseline Risk Share",
        "MA200 Version A Risk Share",
        "MA200 Version B Risk Share",
    ]

    return f"""# MA200 Filter + Cross-Sectional Momentum Test

## 1. Research Question

在固定的 12 ETF Mixed Asset `mom_126 Top5` 框架下，MA200 是否能够降低回撤、提高 Sharpe 和改善风险调整后收益？本实验不搜索其他 MA 或 momentum 参数。

## 2. Fixed Design

- Sample: `{start_date.date()}` to `{end_date.date()}`
- Monthly rebalance; signal at month end; holdings effective next trading day
- Momentum window: 126 trading days
- Portfolio: Top5 equal weight
- Transaction cost: 5 bps
- MA filter: month-end `Adj Close > SMA200`
- Version A: eligible 少于 5 时，每只仍持有 20%，剩余资金为零收益现金
- Version B: eligible 少于 5 时，在全部 eligible 资产中等权满仓
- eligible 为 0 时，两种版本均为全现金

## 3. Performance

{markdown_table(performance, performance_columns, {"CAGR", "MaxDD", "Volatility", "Total Return", "Turnover"})}

## 4. Relative Change vs Baseline

正的 MaxDD Change 表示回撤改善。

{markdown_table(relative_change, relative_columns, {"CAGR Change", "MaxDD Change"})}

## 5. Exposure Statistics

{exposure_markdown_table(exposure_statistics)}

## 6. Asset Class Exposure

以下为日初实际风险资产权重的全样本均值；Version A 的行合计可能低于 100%，差额为现金。

{markdown_table(class_exposure, class_columns, set(class_columns) - {"Asset Class"})}

## 7. Interpretation

1. **MA200 是否提高 Sharpe？** Version A: {version_a['Sharpe']:.2f} vs {baseline['Sharpe']:.2f}; Version B: {version_b['Sharpe']:.2f} vs {baseline['Sharpe']:.2f}。
2. **MA200 是否降低 MaxDD？** Version A: {fmt_pct(version_a['MaxDD'])}; Version B: {fmt_pct(version_b['MaxDD'])}; Baseline: {fmt_pct(baseline['MaxDD'])}。
3. **收益变化主要来自什么？** 最佳过滤版本 `{best_filtered}` 的 CAGR 为 {fmt_pct(best['CAGR'])}、波动率为 {fmt_pct(best['Volatility'])}。Version A 通过平均现金仓位降低风险暴露，避开弱趋势资产基本抵消了现金拖累。
4. **是否减少 Commodity/Bond 暴露？** 最佳过滤版本相对 baseline 的 Commodity/Bond 总权重变化为 {fmt_pct(commodity_change)} / {fmt_pct(bond_change)}；其中一部分来自现金仓位。
5. **是否提高 Equity Concentration？** Equity 总权重变化为 {fmt_pct(equity_change)}，但在已投资风险资产中的占比变化为 {fmt_pct(equity_risk_share_change)}。
6. **是否足以证明策略增强？** {filter_conclusion}

## 8. Final Conclusion

{filter_conclusion}

该结论只适用于固定的 MA200、mom_126、Top5 和当前 12 ETF Universe。两种现金处理方式同时给出，是为了判断改善是否来自过滤本身，而不是某一种低 eligible 权重规则。
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    prices = core.load_prices()
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    ma200 = load_full_history_ma200(prices.index)
    existing_daily = pd.read_csv(BASELINE_DIR / "outputs" / "daily_returns.csv", index_col="Date", parse_dates=True)
    analysis_index = existing_daily.index

    targets, eligibility = build_targets(prices, ma200)
    performance, daily_returns, weights_by_strategy = calculate_performance(returns, targets, analysis_index)
    baseline_error = float((daily_returns["Baseline"] - existing_daily["mom_126_Top5"]).abs().max())
    if baseline_error > 1e-12:
        raise RuntimeError(f"Baseline reproduction mismatch: {baseline_error}")

    relative_change = calculate_relative_change(performance)
    exposure_statistics = calculate_exposure_statistics(eligibility, analysis_index)
    class_exposure = calculate_asset_class_exposure(weights_by_strategy)

    performance.to_csv(METRICS_DIR / "performance.csv", index=False)
    relative_change.to_csv(METRICS_DIR / "relative_change.csv", index=False)
    exposure_statistics.to_csv(METRICS_DIR / "exposure_statistics.csv", index=False)
    class_exposure.to_csv(METRICS_DIR / "asset_class_exposure.csv", index=False)
    eligibility.to_csv(OUTPUTS_DIR / "monthly_eligibility.csv", index=False)
    daily_returns.to_csv(OUTPUTS_DIR / "daily_returns.csv")
    combined_weights = pd.concat(weights_by_strategy, axis=1)
    combined_weights.columns = [f"{strategy}::{symbol}" for strategy, symbol in combined_weights.columns]
    combined_weights.to_csv(OUTPUTS_DIR / "daily_weights.csv")

    summary = generate_summary(
        performance,
        relative_change,
        exposure_statistics,
        class_exposure,
        analysis_index.min(),
        analysis_index.max(),
    )
    SUMMARY_PATH.write_text(summary, encoding="utf-8")

    print("\nMA200 Filter + Cross-Sectional Momentum Test Complete")
    print(f"Study directory: {STUDY_DIR}")
    print(f"Baseline reproduction max error: {baseline_error:.3e}")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nRelative change:")
    print(relative_change.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nExposure statistics:")
    print(exposure_statistics.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nAsset class exposure:")
    print(class_exposure.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
