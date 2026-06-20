from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = ALPHA_ROOT / "shared" / "data"
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(ALPHA_ROOT))

from shared.configs.universes import MIXED_ASSET_SYMBOLS  # noqa: E402
from shared.loaders.prices import load_symbol  # noqa: E402
from shared.utils import cross_sectional as core  # noqa: E402


MOMENTUM_WINDOW = 126
TOP_N = 5
UNIVERSES = {
    "Original 12 ETF Universe": list(MIXED_ASSET_SYMBOLS),
    "Expanded ETF Universe": [
        "SPY", "QQQ", "IWM", "EFA", "EEM", "VTI", "DIA",
        "XLK", "XLF", "XLV", "XLY", "XLP", "XLE", "XLI", "XLU", "XLB", "XLRE",
        "IWF", "IWD", "MTUM", "QUAL", "USMV", "VLUE", "VNQ",
        "GLD", "SLV", "PPLT", "PALL", "USO", "UNG", "DBO", "XOP",
        "DBA", "CORN", "WEAT", "SOYB", "DBC", "GSG",
        "TLT", "IEF", "SHY", "LQD", "TIP", "HYG", "UUP",
    ],
}
ASSET_CLASSES = {
    "Equity": [
        "SPY", "QQQ", "IWM", "EFA", "EEM", "VTI", "DIA",
        "XLK", "XLF", "XLV", "XLY", "XLP", "XLE", "XLI", "XLU", "XLB", "XLRE",
        "IWF", "IWD", "MTUM", "QUAL", "USMV", "VLUE", "VNQ",
    ],
    "Commodity": [
        "GLD", "SLV", "PPLT", "PALL", "USO", "UNG", "DBO", "XOP",
        "DBA", "CORN", "WEAT", "SOYB", "DBC", "GSG",
    ],
    "Bond": ["TLT", "IEF", "SHY", "LQD", "TIP", "HYG"],
    "Currency": ["UUP"],
}


def load_expanded_prices() -> pd.DataFrame:
    frames = []
    missing = []
    for asset_class, symbols in ASSET_CLASSES.items():
        directory = DATA_ROOT / asset_class.lower()
        for symbol in symbols:
            path = directory / f"{symbol}.csv"
            if not path.exists():
                missing.append(symbol)
                continue
            frame = load_symbol(path)
            if frame is None:
                raise RuntimeError(f"Failed to load {symbol}")
            frames.append(frame)
    if missing:
        raise RuntimeError(f"Missing Expanded Universe data: {missing}")
    prices = pd.concat(frames, axis=1).sort_index().dropna(how="any")
    expected = UNIVERSES["Expanded ETF Universe"]
    if set(prices.columns) != set(expected):
        raise RuntimeError("Expanded Universe symbols do not match loaded prices")
    return prices[expected]


def build_targets(
    prices: pd.DataFrame,
) -> tuple[dict[str, dict[pd.Timestamp, pd.Series]], pd.DataFrame]:
    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    targets = {universe: {} for universe in UNIVERSES}
    selection_rows = []

    for rebalance_date in core.month_end_dates(prices.index):
        expanded_scores = momentum.loc[rebalance_date].dropna()
        if len(expanded_scores) != len(prices.columns):
            continue
        location = prices.index.get_loc(rebalance_date)
        if location + 1 >= len(prices.index):
            continue
        effective_date = prices.index[location + 1]

        for universe, symbols in UNIVERSES.items():
            scores = expanded_scores.loc[symbols].sort_values(ascending=False)
            selected = scores.head(TOP_N)
            target = pd.Series(0.0, index=prices.columns)
            target.loc[selected.index] = 1.0 / TOP_N
            targets[universe][effective_date] = target
            for rank, (symbol, score) in enumerate(selected.items(), start=1):
                selection_rows.append(
                    {
                        "Universe": universe,
                        "Rebalance Date": rebalance_date,
                        "Effective Date": effective_date,
                        "Symbol": symbol,
                        "Rank": rank,
                        "Momentum": score,
                        "Target Weight": 1.0 / TOP_N,
                    }
                )

    return targets, pd.DataFrame(selection_rows)


def simulate(
    returns: pd.DataFrame,
    targets: dict[str, dict[pd.Timestamp, pd.Series]],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    performance_rows = []
    daily_returns = {}
    details_by_universe = {}
    weights_by_universe = {}

    for universe, universe_targets in targets.items():
        details, weights = core.simulate_monthly_holdings(returns, universe_targets)
        equity = (1 + details["return"]).cumprod()
        metrics = core.calculate_metrics(
            label=universe,
            momentum_window="mom_126",
            strategy="Top5",
            returns=details["return"],
            equity=equity,
            turnover=details["turnover"],
            number_of_rebalances=len(universe_targets),
        )
        performance_rows.append(
            {
                "Universe": universe,
                "CAGR": metrics["CAGR"],
                "Sharpe": metrics["Sharpe"],
                "MaxDD": metrics["MaxDD"],
                "Volatility": metrics["Volatility"],
                "Calmar": metrics["Calmar"],
                "Total Return": metrics["Total Return"],
                "Turnover": metrics["Turnover"],
            }
        )
        daily_returns[universe] = details["return"]
        details_by_universe[universe] = details
        weights_by_universe[universe] = weights

    comparison_index = next(iter(details_by_universe.values())).index
    if not all(details.index.equals(comparison_index) for details in details_by_universe.values()):
        raise RuntimeError("Universe simulations do not share the same comparison sample")
    return (
        pd.DataFrame(performance_rows),
        pd.DataFrame(daily_returns, index=comparison_index),
        details_by_universe,
        weights_by_universe,
    )


def relative_change(performance: pd.DataFrame) -> pd.DataFrame:
    indexed = performance.set_index("Universe")
    original = indexed.loc["Original 12 ETF Universe"]
    expanded = indexed.loc["Expanded ETF Universe"]
    metrics = ["CAGR", "Sharpe", "MaxDD", "Volatility", "Calmar", "Turnover"]
    return pd.DataFrame(
        {"Metric": metrics, "Expanded - Original": [expanded[metric] - original[metric] for metric in metrics]}
    )


def selection_statistics(
    selections: pd.DataFrame,
    details_by_universe: dict[str, pd.DataFrame],
    targets: dict[str, dict[pd.Timestamp, pd.Series]],
) -> pd.DataFrame:
    rows = []
    for universe, symbols in UNIVERSES.items():
        universe_selections = selections.loc[selections["Universe"] == universe]
        selected_assets = universe_selections["Symbol"].nunique()
        details = details_by_universe[universe]
        trading_years = len(details) / core.TRADING_DAYS
        rows.append(
            {
                "Universe": universe,
                "Average Eligible Assets": len(symbols),
                "Average Distinct Assets Held": universe_selections.groupby("Effective Date")["Symbol"].nunique().mean(),
                "Average Annual Turnover": details["turnover"].sum() / trading_years,
                "Number of Assets Ever Selected": selected_assets,
                "Percent of Universe Ever Selected": selected_assets / len(symbols),
                "Number of Rebalances": len(targets[universe]),
            }
        )
    return pd.DataFrame(rows)


def asset_class_exposure(weights_by_universe: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for asset_class, class_symbols in ASSET_CLASSES.items():
        row = {"Asset Class": asset_class}
        for universe, symbols in UNIVERSES.items():
            available = sorted(set(class_symbols).intersection(symbols))
            row[f"{universe} Weight"] = (
                weights_by_universe[universe][available].sum(axis=1).mean() if available else 0.0
            )
        rows.append(row)
    return pd.DataFrame(rows)


def top_holdings_frequency(selections: pd.DataFrame, number_of_rebalances: int) -> pd.DataFrame:
    expanded = selections.loc[selections["Universe"] == "Expanded ETF Universe"]
    result = expanded.groupby("Symbol").size().rename("Selection Count").reset_index()
    result["Selection Percent"] = result["Selection Count"] / number_of_rebalances
    result["Original 12 ETF"] = result["Symbol"].isin(MIXED_ASSET_SYMBOLS)
    return result.sort_values(["Selection Count", "Symbol"], ascending=[False, True]).head(15).reset_index(drop=True)


def fmt_pct(value: float) -> str:
    return f"{value:.2%}"


def fmt_num(value: float) -> str:
    return f"{value:.2f}"


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


def relative_markdown(relative: pd.DataFrame) -> str:
    percentage_metrics = {"CAGR", "MaxDD", "Volatility", "Turnover"}
    lines = ["| Metric | Expanded - Original |", "| --- | --- |"]
    for _, row in relative.iterrows():
        value = fmt_pct(row["Expanded - Original"]) if row["Metric"] in percentage_metrics else fmt_num(row["Expanded - Original"])
        lines.append(f"| {row['Metric']} | {value} |")
    return "\n".join(lines)


def selection_markdown(selection: pd.DataFrame) -> str:
    indexed = selection.set_index("Universe")
    metrics = [
        "Average Eligible Assets", "Average Distinct Assets Held", "Average Annual Turnover",
        "Number of Assets Ever Selected", "Percent of Universe Ever Selected", "Number of Rebalances",
    ]
    lines = ["| Metric | Original | Expanded |", "| --- | --- | --- |"]
    for metric in metrics:
        original = indexed.loc["Original 12 ETF Universe", metric]
        expanded = indexed.loc["Expanded ETF Universe", metric]
        if metric in {"Average Annual Turnover", "Percent of Universe Ever Selected"}:
            original_text, expanded_text = fmt_pct(original), fmt_pct(expanded)
        else:
            original_text, expanded_text = fmt_num(original), fmt_num(expanded)
        lines.append(f"| {metric} | {original_text} | {expanded_text} |")
    return "\n".join(lines)


def generate_summary(
    performance: pd.DataFrame,
    relative: pd.DataFrame,
    selection: pd.DataFrame,
    exposure: pd.DataFrame,
    top_holdings: pd.DataFrame,
    selections: pd.DataFrame,
    common_start: pd.Timestamp,
    common_end: pd.Timestamp,
    common_days: int,
    strategy_start: pd.Timestamp,
    strategy_days: int,
) -> str:
    indexed = performance.set_index("Universe")
    original = indexed.loc["Original 12 ETF Universe"]
    expanded = indexed.loc["Expanded ETF Universe"]
    selection_indexed = selection.set_index("Universe")
    expanded_selections = selections.loc[selections["Universe"] == "Expanded ETF Universe"]
    original_slot_share = expanded_selections["Symbol"].isin(MIXED_ASSET_SYMBOLS).mean()
    top_new = top_holdings.loc[~top_holdings["Original 12 ETF"], "Symbol"].tolist()
    sharpe_similar = abs(expanded["Sharpe"] - original["Sharpe"]) <= 0.15
    maxdd_similar = abs(expanded["MaxDD"] - original["MaxDD"]) <= 0.05
    return_direction = "改善" if expanded["CAGR"] > original["CAGR"] + 0.005 else "恶化" if expanded["CAGR"] < original["CAGR"] - 0.005 else "基本持平"
    breadth_increased = (
        selection_indexed.loc["Expanded ETF Universe", "Number of Assets Ever Selected"]
        > selection_indexed.loc["Original 12 ETF Universe", "Number of Assets Ever Selected"]
    )
    supports_general = sharpe_similar and maxdd_similar and breadth_increased
    exposure_indexed = exposure.set_index("Asset Class")
    original_bond_weight = exposure_indexed.loc["Bond", "Original 12 ETF Universe Weight"]
    expanded_bond_weight = exposure_indexed.loc["Bond", "Expanded ETF Universe Weight"]
    original_annual_turnover = selection_indexed.loc["Original 12 ETF Universe", "Average Annual Turnover"]
    expanded_annual_turnover = selection_indexed.loc["Expanded ETF Universe", "Average Annual Turnover"]
    incremental_annual_cost = (expanded_annual_turnover - original_annual_turnover) * core.TRADING_COST

    return f"""# Expanded Universe Momentum Test

## 1. Research Question

在固定 `mom_126 Top5` 策略下，检验 Universe 从原始 12 ETF 扩展至 45 ETF 后，Cross-Sectional Momentum 的核心风险收益特征是否仍然存在。本实验不优化任何参数。

## 2. Fixed Design and Sample

- Monthly rebalance; month-end signal effective next trading day
- Momentum window: 126 trading days
- Top5 equal weight; transaction cost 5 bps; no MA filter
- Common data sample: `{common_start.date()}` to `{common_end.date()}` ({common_days} trading days)
- First 126 common-sample trading days are momentum warm-up
- Strategy comparison sample: `{strategy_start.date()}` to `{common_end.date()}` ({strategy_days} trading days)
- Both Universes use identical rebalance dates and performance sample
- Descriptive similarity guide: Sharpe difference <= 0.15 and MaxDD difference <= 5 percentage points

## 3. Performance Comparison

{markdown_table(performance, ['Universe', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Calmar', 'Total Return', 'Turnover'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return', 'Turnover'})}

## 4. Relative Change

{relative_markdown(relative)}

## 5. Selection Statistics

{selection_markdown(selection)}

`Average Distinct Assets Held` 是每个调仓期实际 Top5 持仓数；资产广度主要由 `Number of Assets Ever Selected` 和 `Percent of Universe Ever Selected` 判断。

## 6. Asset Class Exposure

以下为持有期间日初实际权重的长期均值。

{markdown_table(exposure, ['Asset Class', 'Original 12 ETF Universe Weight', 'Expanded ETF Universe Weight'], {'Original 12 ETF Universe Weight', 'Expanded ETF Universe Weight'})}

## 7. Expanded Universe Top Holdings Frequency

{markdown_table(top_holdings, ['Symbol', 'Selection Count', 'Selection Percent', 'Original 12 ETF'], {'Selection Percent'})}

## 8. Interpretation

1. **Expanded Universe 是否保持类似 Sharpe？** {'是' if sharpe_similar else '否'}。Expanded 为 {expanded['Sharpe']:.2f}，Original 为 {original['Sharpe']:.2f}。
2. **是否保持类似 MaxDD？** {'是' if maxdd_similar else '否'}。Expanded 为 {fmt_pct(expanded['MaxDD'])}，Original 为 {fmt_pct(original['MaxDD'])}。
3. **收益变化？** CAGR {return_direction}：Expanded {fmt_pct(expanded['CAGR'])} vs Original {fmt_pct(original['CAGR'])}。
4. **是否出现新的长期赢家？** {'是，Top15 中新增标的包括 ' + ', '.join(top_new) if top_new else 'Top15 仍全部来自原始 12 ETF'}。
5. **Top5 是否仍由原始 12 ETF 主导？** 原始 12 ETF 占 Expanded 全部入选槽位的 {fmt_pct(original_slot_share)}；{'仍占多数' if original_slot_share > 0.5 else '已不占多数'}。
6. **是否提高资产广度？** {'是' if breadth_increased else '否'}。曾入选资产数从 {int(selection_indexed.loc['Original 12 ETF Universe', 'Number of Assets Ever Selected'])} 增至 {int(selection_indexed.loc['Expanded ETF Universe', 'Number of Assets Ever Selected'])}。
7. **更支持哪种解释？** {'风险收益特征在更广 Universe 中保持且选择广度增加，更支持 Momentum 是较普遍的横截面趋势效应，而非只依赖原始 12 ETF 构造。' if supports_general else '扩展后核心风险收益特征未同时保持，当前证据仍显示策略对 Universe 构造敏感。'}

名义广度增加并不等同于独立风险来源增加。Expanded Universe 包含多组高度重叠的宽基、行业、风格和单一商品 ETF；同时 Bond 实际权重从 {fmt_pct(original_bond_weight)} 降至 {fmt_pct(expanded_bond_weight)}。年化换手增加对应的直接成本差约为 {fmt_pct(incremental_annual_cost)}，不足以单独解释 CAGR 的全部下降，主要变化来自持仓构成、波动率和回撤。

## 9. Final Conclusion

{'扩展到 45 ETF 后，Cross-Sectional Momentum 的核心风险收益特征仍然成立。' if supports_general else '扩展到 45 ETF 后，Cross-Sectional Momentum 的核心风险收益特征没有完整保持。'}这一结论仅比较固定策略在两个 Universe 中的表现，不包含参数搜索。
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    prices = load_expanded_prices()
    common_start, common_end = prices.index.min(), prices.index.max()
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    targets, selections = build_targets(prices)
    performance, daily_returns, details_by_universe, weights_by_universe = simulate(returns, targets)
    strategy_start = daily_returns.index.min()

    relative = relative_change(performance)
    selection = selection_statistics(selections, details_by_universe, targets)
    exposure = asset_class_exposure(weights_by_universe)
    top_holdings = top_holdings_frequency(selections, len(targets["Expanded ETF Universe"]))
    sample = pd.DataFrame(
        [
            {"Metric": "Common Start Date", "Value": common_start.date().isoformat()},
            {"Metric": "Common End Date", "Value": common_end.date().isoformat()},
            {"Metric": "Common Trading Days", "Value": len(prices)},
            {"Metric": "Strategy Comparison Start Date", "Value": strategy_start.date().isoformat()},
            {"Metric": "Strategy Comparison Trading Days", "Value": len(daily_returns)},
        ]
    )

    performance.to_csv(METRICS_DIR / "performance_comparison.csv", index=False)
    relative.to_csv(METRICS_DIR / "relative_change.csv", index=False)
    selection.to_csv(METRICS_DIR / "selection_statistics.csv", index=False)
    exposure.to_csv(METRICS_DIR / "asset_class_exposure.csv", index=False)
    top_holdings.to_csv(METRICS_DIR / "top_holdings_frequency.csv", index=False)
    sample.to_csv(METRICS_DIR / "sample_summary.csv", index=False)
    selections.to_csv(OUTPUTS_DIR / "selections.csv", index=False)
    daily_returns.to_csv(OUTPUTS_DIR / "daily_returns.csv")
    combined_weights = pd.concat(weights_by_universe, axis=1)
    combined_weights.columns = [f"{universe}::{symbol}" for universe, symbol in combined_weights.columns]
    combined_weights.to_csv(OUTPUTS_DIR / "daily_weights.csv")
    combined_details = pd.concat(details_by_universe, axis=1)
    combined_details.columns = [f"{universe}::{metric}" for universe, metric in combined_details.columns]
    combined_details.to_csv(OUTPUTS_DIR / "daily_details.csv")

    SUMMARY_PATH.write_text(
        generate_summary(
            performance, relative, selection, exposure, top_holdings, selections,
            common_start, common_end, len(prices), strategy_start, len(daily_returns),
        ),
        encoding="utf-8",
    )

    print("\nExpanded Universe Momentum Test Complete")
    print(f"Common data sample: {common_start.date()} to {common_end.date()} ({len(prices)} days)")
    print(f"Strategy sample: {strategy_start.date()} to {common_end.date()} ({len(daily_returns)} days)")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nSelection statistics:")
    print(selection.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nTop holdings:")
    print(top_holdings.to_string(index=False))


if __name__ == "__main__":
    main()
