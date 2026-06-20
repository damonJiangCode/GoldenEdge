from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = ALPHA_ROOT / "shared" / "data"
EXPANDED_STUDY_DIR = ALPHA_ROOT / "cross_sectional" / "expanded_universe_momentum"
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(ALPHA_ROOT))

from shared.configs.universes import MIXED_ASSET_SYMBOLS  # noqa: E402
from shared.loaders.prices import load_symbol  # noqa: E402
from shared.utils import cross_sectional as core  # noqa: E402


MOMENTUM_WINDOW = 126
TOP_N = 5
COMPARISON_START = pd.Timestamp("2016-05-02")
STRATEGY_NAMES = [
    "Original 12 ETF Top5",
    "Expanded Global Top5",
    "Category Balanced",
    "Category Winner (Class Mean)",
    "Category Winner (Top3 Mean)",
]
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
EXPANDED_SYMBOLS = [symbol for symbols in ASSET_CLASSES.values() for symbol in symbols]
CATEGORY_BALANCED_SLOTS = {"Equity": 2, "Commodity": 2, "Bond": 1, "Currency": 0}


def load_prices() -> pd.DataFrame:
    frames = []
    for asset_class, symbols in ASSET_CLASSES.items():
        directory = DATA_ROOT / asset_class.lower()
        for symbol in symbols:
            path = directory / f"{symbol}.csv"
            if not path.exists():
                raise RuntimeError(f"Missing data for {symbol}: {path}")
            frame = load_symbol(path)
            if frame is None:
                raise RuntimeError(f"Failed to load {symbol}")
            frames.append(frame)
    prices = pd.concat(frames, axis=1).sort_index().dropna(how="any")
    return prices[EXPANDED_SYMBOLS]


def fixed_slot_target(selected: list[str], slot_count: int, columns: pd.Index) -> pd.Series:
    target = pd.Series(0.0, index=columns)
    if selected:
        target.loc[selected] = 1.0 / slot_count
    return target


def category_scores(momentum: pd.Series, method: str) -> pd.Series:
    scores = {}
    for asset_class, symbols in ASSET_CLASSES.items():
        class_momentum = momentum.loc[symbols]
        if method == "class_mean":
            scores[asset_class] = class_momentum.mean()
        elif method == "top3_mean":
            scores[asset_class] = class_momentum.nlargest(min(3, len(class_momentum))).mean()
        else:
            raise ValueError(f"Unknown category score method: {method}")
    return pd.Series(scores).sort_values(ascending=False)


def build_targets(
    prices: pd.DataFrame,
) -> tuple[dict[str, dict[pd.Timestamp, pd.Series]], pd.DataFrame, pd.DataFrame]:
    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    targets = {strategy: {} for strategy in STRATEGY_NAMES}
    selection_rows = []
    category_rows = []

    for rebalance_date in core.month_end_dates(prices.index):
        scores = momentum.loc[rebalance_date].dropna()
        if len(scores) != len(prices.columns):
            continue
        location = prices.index.get_loc(rebalance_date)
        if location + 1 >= len(prices.index):
            continue
        effective_date = prices.index[location + 1]
        if effective_date < COMPARISON_START:
            continue

        selections: dict[str, list[str]] = {
            "Original 12 ETF Top5": scores.loc[MIXED_ASSET_SYMBOLS].nlargest(5).index.tolist(),
            "Expanded Global Top5": scores.nlargest(5).index.tolist(),
        }
        targets["Original 12 ETF Top5"][effective_date] = fixed_slot_target(
            selections["Original 12 ETF Top5"], 5, prices.columns
        )
        targets["Expanded Global Top5"][effective_date] = fixed_slot_target(
            selections["Expanded Global Top5"], 5, prices.columns
        )

        balanced_selected = []
        for asset_class, slots in CATEGORY_BALANCED_SLOTS.items():
            if slots:
                balanced_selected.extend(scores.loc[ASSET_CLASSES[asset_class]].nlargest(slots).index.tolist())
        selections["Category Balanced"] = balanced_selected
        targets["Category Balanced"][effective_date] = fixed_slot_target(
            balanced_selected, 5, prices.columns
        )

        for strategy, method in [
            ("Category Winner (Class Mean)", "class_mean"),
            ("Category Winner (Top3 Mean)", "top3_mean"),
        ]:
            class_ranking = category_scores(scores, method)
            winning_classes = class_ranking.head(2).index.tolist()
            selected = []
            for asset_class in winning_classes:
                selected.extend(scores.loc[ASSET_CLASSES[asset_class]].nlargest(2).index.tolist())
            selections[strategy] = selected
            targets[strategy][effective_date] = fixed_slot_target(selected, 4, prices.columns)
            for rank, (asset_class, class_score) in enumerate(class_ranking.items(), start=1):
                category_rows.append(
                    {
                        "Strategy": strategy,
                        "Rebalance Date": rebalance_date,
                        "Effective Date": effective_date,
                        "Asset Class": asset_class,
                        "Category Rank": rank,
                        "Category Momentum": class_score,
                        "Selected": asset_class in winning_classes,
                    }
                )

        for strategy, selected in selections.items():
            target = targets[strategy][effective_date]
            for symbol in selected:
                asset_class = next(name for name, symbols in ASSET_CLASSES.items() if symbol in symbols)
                selection_rows.append(
                    {
                        "Strategy": strategy,
                        "Rebalance Date": rebalance_date,
                        "Effective Date": effective_date,
                        "Symbol": symbol,
                        "Asset Class": asset_class,
                        "Momentum": scores.loc[symbol],
                        "Target Weight": target.loc[symbol],
                    }
                )

    return targets, pd.DataFrame(selection_rows), pd.DataFrame(category_rows)


def simulate(
    returns: pd.DataFrame,
    targets: dict[str, dict[pd.Timestamp, pd.Series]],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    performance_rows = []
    details_by_strategy = {}
    weights_by_strategy = {}
    for strategy, strategy_targets in targets.items():
        details, weights = core.simulate_monthly_holdings(returns, strategy_targets)
        if details.index.min() != COMPARISON_START:
            raise RuntimeError(f"{strategy}: unexpected comparison start {details.index.min()}")
        equity = (1 + details["return"]).cumprod()
        metrics = core.calculate_metrics(
            label=strategy,
            momentum_window="mom_126",
            strategy=strategy,
            returns=details["return"],
            equity=equity,
            turnover=details["turnover"],
            number_of_rebalances=len(strategy_targets),
        )
        performance_rows.append(
            {
                "Strategy": strategy,
                "CAGR": metrics["CAGR"],
                "Sharpe": metrics["Sharpe"],
                "MaxDD": metrics["MaxDD"],
                "Volatility": metrics["Volatility"],
                "Calmar": metrics["Calmar"],
                "Total Return": metrics["Total Return"],
                "Turnover": metrics["Turnover"],
            }
        )
        details_by_strategy[strategy] = details
        weights_by_strategy[strategy] = weights
    return pd.DataFrame(performance_rows), details_by_strategy, weights_by_strategy


def asset_class_exposure(weights_by_strategy: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for strategy, weights in weights_by_strategy.items():
        row = {"Strategy": strategy}
        for asset_class, symbols in ASSET_CLASSES.items():
            row[asset_class] = weights[symbols].sum(axis=1).mean()
        row["Cash"] = (1 - weights.sum(axis=1)).mean()
        rows.append(row)
    return pd.DataFrame(rows)


def selection_statistics(
    selections: pd.DataFrame,
    details_by_strategy: dict[str, pd.DataFrame],
    targets: dict[str, dict[pd.Timestamp, pd.Series]],
) -> pd.DataFrame:
    rows = []
    for strategy in STRATEGY_NAMES:
        selected = selections.loc[selections["Strategy"] == strategy]
        rebalance_dates = pd.DatetimeIndex(targets[strategy].keys())
        rebalance_turnover = details_by_strategy[strategy].loc[rebalance_dates, "turnover"]
        rows.append(
            {
                "Strategy": strategy,
                "Distinct Assets Selected": selected["Symbol"].nunique(),
                "Average Holdings": selected.groupby("Effective Date")["Symbol"].nunique().mean(),
                "Average Turnover": rebalance_turnover.mean(),
                "Number of Rebalances": selected["Effective Date"].nunique(),
            }
        )
    return pd.DataFrame(rows)


def category_contribution(
    returns: pd.DataFrame,
    details_by_strategy: dict[str, pd.DataFrame],
    weights_by_strategy: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    rows = []
    contribution_strategies = [
        "Category Balanced",
        "Category Winner (Class Mean)",
        "Category Winner (Top3 Mean)",
    ]
    for strategy in contribution_strategies:
        details = details_by_strategy[strategy]
        weights = weights_by_strategy[strategy]
        strategy_returns = returns.loc[details.index]
        starting_wealth = (1 + details["return"]).cumprod().shift(1, fill_value=1.0)
        contributions = {}
        for asset_class, symbols in ASSET_CLASSES.items():
            daily_class_return = (weights[symbols] * strategy_returns[symbols]).sum(axis=1)
            contributions[asset_class] = float((starting_wealth * daily_class_return).sum())
        total_gross_contribution = sum(contributions.values())
        for asset_class, contribution in contributions.items():
            rows.append(
                {
                    "Strategy": strategy,
                    "Asset Class": asset_class,
                    "Total Gross PnL Contribution": contribution,
                    "Contribution Percent": contribution / total_gross_contribution,
                }
            )
    return pd.DataFrame(rows)


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


def generate_summary(
    performance: pd.DataFrame,
    exposure: pd.DataFrame,
    selection: pd.DataFrame,
    contribution: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> str:
    perf = performance.set_index("Strategy")
    exp = exposure.set_index("Strategy")
    original = perf.loc["Original 12 ETF Top5"]
    global_top5 = perf.loc["Expanded Global Top5"]
    balanced = perf.loc["Category Balanced"]
    winner_mean = perf.loc["Category Winner (Class Mean)"]
    winner_top3 = perf.loc["Category Winner (Top3 Mean)"]
    balanced_better = balanced["Sharpe"] > global_top5["Sharpe"] and balanced["MaxDD"] > global_top5["MaxDD"]
    mean_better = winner_mean["Sharpe"] > global_top5["Sharpe"] and winner_mean["MaxDD"] > global_top5["MaxDD"]
    top3_better = winner_top3["Sharpe"] > global_top5["Sharpe"] and winner_top3["MaxDD"] > global_top5["MaxDD"]
    bond_recovery = exp.loc["Category Balanced", "Bond"] - exp.loc["Expanded Global Top5", "Bond"]
    maxdd_improvement = balanced["MaxDD"] - global_top5["MaxDD"]

    comparison_strategies = ["Expanded Global Top5", "Category Balanced", "Category Winner (Class Mean)", "Category Winner (Top3 Mean)"]
    distances = {}
    for strategy in comparison_strategies:
        row = perf.loc[strategy]
        distances[strategy] = (
            abs(row["CAGR"] - original["CAGR"]) / 0.02
            + abs(row["Sharpe"] - original["Sharpe"]) / 0.15
            + abs(row["MaxDD"] - original["MaxDD"]) / 0.05
        )
    closest = min(distances, key=distances.get)
    category_versions_better = balanced_better or mean_better or top3_better
    combined_evidence = balanced_better and (mean_better or top3_better)

    return f"""# Asset Rotation vs Category Rotation Test

## 1. Research Question

在固定 Expanded 45 ETF、`mom_126` 和月度调仓框架下，比较统一资产排名与先控制或轮动资产类别的结构。本实验不优化任何参数。

## 2. Fixed Design

- Sample: `{start.date()}` to `{end.date()}`
- Monthly rebalance; month-end signal effective next trading day
- Momentum: 126 trading days; transaction cost: 5 bps; no MA filter
- Global Top5: 45 ETF 统一排名，Top5 每只 20%
- Category Balanced: Equity Top2、Commodity Top2、Bond Top1，每只 20%
- Category Winner Class Mean / Top3 Mean: 按两种预先指定的类别动量选 Top2 类别，各类别 Top2 ETF，共四个 25% 槽位
- Currency 不强制配置；类别内不足两个 ETF 时缺失槽位保留现金

## 3. Performance

{markdown_table(performance, ['Strategy', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Calmar', 'Total Return', 'Turnover'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return', 'Turnover'})}

## 4. Asset Class Exposure

{markdown_table(exposure, ['Strategy', 'Equity', 'Commodity', 'Bond', 'Currency', 'Cash'], {'Equity', 'Commodity', 'Bond', 'Currency', 'Cash'})}

## 5. Selection Statistics

`Average Turnover` 是发生调仓时的平均双边绝对权重变化。

{markdown_table(selection, ['Strategy', 'Distinct Assets Selected', 'Average Holdings', 'Average Turnover', 'Number of Rebalances'], {'Average Turnover'})}

## 6. Category Contribution

Contribution 使用期初组合财富加权的资产类别毛 PnL，百分比在四类资产之间归一化，不包含交易成本归属。

{markdown_table(contribution, ['Strategy', 'Asset Class', 'Total Gross PnL Contribution', 'Contribution Percent'], {'Contribution Percent'})}

## 7. Interpretation

1. **Category Balanced 是否优于 Expanded Global Top5？** {'是' if balanced_better else '否'}。Sharpe {balanced['Sharpe']:.2f} vs {global_top5['Sharpe']:.2f}；MaxDD {fmt_pct(balanced['MaxDD'])} vs {fmt_pct(global_top5['MaxDD'])}。
2. **Category Winner 是否优于 Expanded Global Top5？** Class Mean {'是' if mean_better else '否'}，Top3 Mean {'是' if top3_better else '否'}；对应 Sharpe 为 {winner_mean['Sharpe']:.2f}/{winner_top3['Sharpe']:.2f}。
3. **Bond 权重恢复后 MaxDD 是否改善？** Category Balanced 的 Bond 权重增加 {fmt_pct(bond_recovery)}，MaxDD 改善 {fmt_pct(maxdd_improvement)}。
4. **Expanded 劣化是否主要来自 Bond 被挤出？** {'恢复固定 Bond 配置后风险收益显著改善，Bond 被挤出是重要原因；但类别内重复和高波动资产竞争仍会影响结果，不能归因于单一因素。' if balanced_better else '恢复 Bond 配置没有同时修复 Sharpe 与 MaxDD，Bond 被挤出不是充分解释。'}
5. **Alpha 更像来自什么？** {'Category Balanced 与至少一个 Category Winner 版本都改善 Global Top5，证据更支持资产选择与类别结构共同作用。' if combined_evidence else '只有部分类别结构改善 Global Top5，证据不足以认定纯类别轮动；资产排名与类别约束仍需共同解释。' if category_versions_better else '类别结构没有修复 Global Top5，证据更偏向原始资产级 Universe 构造。'}
6. **最接近 Original 12 的结构？** 按 CAGR、Sharpe、MaxDD 相对 Original 的预设归一化距离，`{closest}` 最接近；该距离只用于结构比较，不用于参数优化。

## 8. Final Conclusion

{'当前核心 Alpha 更接近资产级 Momentum 与资产类别结构的结合。Expanded Universe 的失效更可能来自统一排名让大量相关、高波动 ETF 竞争有限 Top5 槽位，并挤出防守性类别，而不是 Momentum 信号本身完全消失。' if combined_evidence else '当前证据不支持把核心 Alpha 简化为纯类别轮动。Expanded Universe 的失效仍表现为资产池构造、类别暴露与资产级排名共同作用的结果。'}
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    prices = load_prices()
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    targets, selections, category_rankings = build_targets(prices)
    performance, details_by_strategy, weights_by_strategy = simulate(returns, targets)
    exposure = asset_class_exposure(weights_by_strategy)
    selection = selection_statistics(selections, details_by_strategy, targets)
    contribution = category_contribution(returns, details_by_strategy, weights_by_strategy)

    prior_returns = pd.read_csv(EXPANDED_STUDY_DIR / "outputs" / "daily_returns.csv", index_col="Date", parse_dates=True)
    original_error = float((details_by_strategy["Original 12 ETF Top5"]["return"] - prior_returns["Original 12 ETF Universe"]).abs().max())
    expanded_error = float((details_by_strategy["Expanded Global Top5"]["return"] - prior_returns["Expanded ETF Universe"]).abs().max())
    if original_error > 1e-12 or expanded_error > 1e-12:
        raise RuntimeError(f"Prior strategy reproduction mismatch: original={original_error}, expanded={expanded_error}")

    performance.to_csv(METRICS_DIR / "performance.csv", index=False)
    exposure.to_csv(METRICS_DIR / "asset_class_exposure.csv", index=False)
    selection.to_csv(METRICS_DIR / "selection_statistics.csv", index=False)
    contribution.to_csv(METRICS_DIR / "category_contribution.csv", index=False)
    selections.to_csv(OUTPUTS_DIR / "selections.csv", index=False)
    category_rankings.to_csv(OUTPUTS_DIR / "category_rankings.csv", index=False)
    combined_details = pd.concat(details_by_strategy, axis=1)
    combined_details.columns = [f"{strategy}::{metric}" for strategy, metric in combined_details.columns]
    combined_details.to_csv(OUTPUTS_DIR / "daily_details.csv")
    combined_weights = pd.concat(weights_by_strategy, axis=1)
    combined_weights.columns = [f"{strategy}::{symbol}" for strategy, symbol in combined_weights.columns]
    combined_weights.to_csv(OUTPUTS_DIR / "daily_weights.csv")
    SUMMARY_PATH.write_text(
        generate_summary(performance, exposure, selection, contribution, COMPARISON_START, prices.index.max()),
        encoding="utf-8",
    )

    print("\nAsset Rotation vs Category Rotation Test Complete")
    print(f"Original reproduction max error: {original_error:.3e}")
    print(f"Expanded reproduction max error: {expanded_error:.3e}")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nAsset class exposure:")
    print(exposure.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nCategory contribution:")
    print(contribution.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
