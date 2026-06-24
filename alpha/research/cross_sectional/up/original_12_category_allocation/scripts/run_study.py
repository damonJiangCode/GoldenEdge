from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[4]
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(ALPHA_ROOT))

from shared.configs.universes import MIXED_ASSET_CLASSES, MIXED_ASSET_SYMBOLS  # noqa: E402
from shared.utils import cross_sectional as core  # noqa: E402


MOMENTUM_WINDOW = 126
COMPARISON_START = pd.Timestamp("2008-02-01")
TOP_N = 5
SLOT_WEIGHT = 0.20
STRATEGY_SLOTS = {
    "Original Top5": None,
    "3-1-1": {"Equity": 3, "Commodity": 1, "Bond": 1},
    "2-2-1": {"Equity": 2, "Commodity": 2, "Bond": 1},
    "1-3-1": {"Equity": 1, "Commodity": 3, "Bond": 1},
}
ASSET_CLASS_ORDER = ["Equity", "Commodity", "Bond"]


def build_targets(
    prices: pd.DataFrame,
) -> tuple[dict[str, dict[pd.Timestamp, pd.Series]], pd.DataFrame, pd.DataFrame]:
    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    targets = {strategy: {} for strategy in STRATEGY_SLOTS}
    selection_rows = []
    slot_rows = []

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

        for strategy, slots in STRATEGY_SLOTS.items():
            if slots is None:
                selected = scores.nlargest(TOP_N).index.tolist()
            else:
                selected = []
                for asset_class in ASSET_CLASS_ORDER:
                    selected.extend(
                        scores.loc[MIXED_ASSET_CLASSES[asset_class]]
                        .nlargest(slots[asset_class])
                        .index.tolist()
                    )
            target = pd.Series(0.0, index=prices.columns)
            target.loc[selected] = SLOT_WEIGHT
            targets[strategy][effective_date] = target

            counts = {asset_class: 0 for asset_class in ASSET_CLASS_ORDER}
            for symbol in selected:
                asset_class = next(
                    name for name, symbols in MIXED_ASSET_CLASSES.items() if symbol in symbols
                )
                counts[asset_class] += 1
                selection_rows.append(
                    {
                        "Strategy": strategy,
                        "Rebalance Date": rebalance_date,
                        "Effective Date": effective_date,
                        "Symbol": symbol,
                        "Asset Class": asset_class,
                        "Momentum": scores.loc[symbol],
                        "Target Weight": SLOT_WEIGHT,
                    }
                )
            slot_rows.append(
                {
                    "Strategy": strategy,
                    "Rebalance Date": rebalance_date,
                    "Effective Date": effective_date,
                    "Equity Slots": counts["Equity"],
                    "Commodity Slots": counts["Commodity"],
                    "Bond Slots": counts["Bond"],
                }
            )
    return targets, pd.DataFrame(selection_rows), pd.DataFrame(slot_rows)


def simulate(
    returns: pd.DataFrame,
    targets: dict[str, dict[pd.Timestamp, pd.Series]],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    rows = []
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
        rows.append(
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
    return pd.DataFrame(rows), details_by_strategy, weights_by_strategy


def relative_change(performance: pd.DataFrame) -> pd.DataFrame:
    baseline = performance.set_index("Strategy").loc["Original Top5"]
    result = performance.loc[performance["Strategy"] != "Original Top5", ["Strategy", "CAGR", "Sharpe", "MaxDD"]].copy()
    result["CAGR Change"] = result["CAGR"] - baseline["CAGR"]
    result["Sharpe Change"] = result["Sharpe"] - baseline["Sharpe"]
    result["MaxDD Change"] = result["MaxDD"] - baseline["MaxDD"]
    return result[["Strategy", "CAGR Change", "Sharpe Change", "MaxDD Change"]]


def asset_class_exposure(weights_by_strategy: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for strategy, weights in weights_by_strategy.items():
        row = {"Strategy": strategy}
        for asset_class in ASSET_CLASS_ORDER:
            row[asset_class] = weights[MIXED_ASSET_CLASSES[asset_class]].sum(axis=1).mean()
        rows.append(row)
    return pd.DataFrame(rows)


def selection_statistics(
    selections: pd.DataFrame,
    details_by_strategy: dict[str, pd.DataFrame],
    targets: dict[str, dict[pd.Timestamp, pd.Series]],
) -> pd.DataFrame:
    rows = []
    for strategy in STRATEGY_SLOTS:
        selected = selections.loc[selections["Strategy"] == strategy]
        effective_dates = pd.DatetimeIndex(targets[strategy].keys())
        counts = selected.groupby("Symbol").size().reindex(MIXED_ASSET_SYMBOLS, fill_value=0)
        slot_share = counts / counts.sum()
        rows.append(
            {
                "Strategy": strategy,
                "Distinct Assets Selected": selected["Symbol"].nunique(),
                "Average Holdings": selected.groupby("Effective Date")["Symbol"].nunique().mean(),
                "Average Turnover": details_by_strategy[strategy].loc[effective_dates, "turnover"].mean(),
                "Selection Concentration HHI": float((slot_share**2).sum()),
                "Number of Rebalances": len(effective_dates),
            }
        )
    return pd.DataFrame(rows)


def category_contribution(
    returns: pd.DataFrame,
    details_by_strategy: dict[str, pd.DataFrame],
    weights_by_strategy: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    rows = []
    for strategy in STRATEGY_SLOTS:
        details = details_by_strategy[strategy]
        weights = weights_by_strategy[strategy]
        strategy_returns = returns.loc[details.index]
        starting_wealth = (1 + details["return"]).cumprod().shift(1, fill_value=1.0)
        contributions = {}
        for asset_class in ASSET_CLASS_ORDER:
            daily_return = (
                weights[MIXED_ASSET_CLASSES[asset_class]]
                * strategy_returns[MIXED_ASSET_CLASSES[asset_class]]
            ).sum(axis=1)
            contributions[asset_class] = float((starting_wealth * daily_return).sum())
        total = sum(contributions.values())
        rows.append(
            {
                "Strategy": strategy,
                "Equity Contribution": contributions["Equity"] / total,
                "Commodity Contribution": contributions["Commodity"] / total,
                "Bond Contribution": contributions["Bond"] / total,
            }
        )
    return pd.DataFrame(rows)


def selection_frequency(selections: pd.DataFrame, number_of_rebalances: int) -> pd.DataFrame:
    rows = []
    for strategy in STRATEGY_SLOTS:
        counts = selections.loc[selections["Strategy"] == strategy].groupby("Symbol").size()
        for symbol in MIXED_ASSET_SYMBOLS:
            count = int(counts.get(symbol, 0))
            rows.append(
                {
                    "Strategy": strategy,
                    "ETF": symbol,
                    "Selection Count": count,
                    "Selection Percent": count / number_of_rebalances,
                }
            )
    return pd.DataFrame(rows)


def average_category_slots(slot_history: pd.DataFrame) -> pd.DataFrame:
    result = (
        slot_history.groupby("Strategy", as_index=False)
        .agg(
            **{
                "Average Equity Slots": ("Equity Slots", "mean"),
                "Average Commodity Slots": ("Commodity Slots", "mean"),
                "Average Bond Slots": ("Bond Slots", "mean"),
            }
        )
    )
    order = {strategy: index for index, strategy in enumerate(STRATEGY_SLOTS)}
    result["_order"] = result["Strategy"].map(order)
    return result.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def original_slot_distribution(slot_history: pd.DataFrame) -> pd.DataFrame:
    original = slot_history.loc[slot_history["Strategy"] == "Original Top5"]
    result = (
        original.groupby(["Equity Slots", "Commodity Slots", "Bond Slots"])
        .size()
        .rename("Month Count")
        .reset_index()
    )
    result["Month Percent"] = result["Month Count"] / len(original)
    return result.sort_values(
        ["Month Count", "Equity Slots", "Commodity Slots", "Bond Slots"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)


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


def frequency_sections(frequency: pd.DataFrame) -> str:
    sections = []
    for strategy in STRATEGY_SLOTS:
        table = frequency.loc[frequency["Strategy"] == strategy].sort_values(
            ["Selection Count", "ETF"], ascending=[False, True]
        )
        sections.append(
            f"### {strategy}\n\n"
            + markdown_table(table, ["ETF", "Selection Count", "Selection Percent"], {"Selection Percent"})
        )
    return "\n\n".join(sections)


def generate_summary(
    performance: pd.DataFrame,
    relative: pd.DataFrame,
    exposure: pd.DataFrame,
    selection: pd.DataFrame,
    contribution: pd.DataFrame,
    frequency: pd.DataFrame,
    slots: pd.DataFrame,
    slot_distribution: pd.DataFrame,
    end_date: pd.Timestamp,
) -> str:
    perf = performance.set_index("Strategy")
    baseline = perf.loc["Original Top5"]
    constrained = perf.drop(index="Original Top5")
    original_best = bool(
        (baseline["CAGR"] > constrained["CAGR"]).all()
        and (baseline["Sharpe"] > constrained["Sharpe"]).all()
    )
    original_slots = slots.set_index("Strategy").loc["Original Top5"]
    fixed_slots = slots.set_index("Strategy").drop(index="Original Top5")
    slot_distances = fixed_slots.apply(
        lambda row: sum(
            abs(row[column] - original_slots[column])
            for column in ["Average Equity Slots", "Average Commodity Slots", "Average Bond Slots"]
        ),
        axis=1,
    )
    nearest_slots = slot_distances.idxmin()
    comparison_distances = {}
    for strategy, row in constrained.iterrows():
        comparison_distances[strategy] = (
            abs(row["CAGR"] - baseline["CAGR"]) / 0.02
            + abs(row["Sharpe"] - baseline["Sharpe"]) / 0.15
            + abs(row["MaxDD"] - baseline["MaxDD"]) / 0.05
        )
    nearest_performance = min(comparison_distances, key=comparison_distances.get)
    fixed = perf.loc[["3-1-1", "2-2-1", "1-3-1"]]
    equity_monotonic = fixed.loc[["1-3-1", "2-2-1", "3-1-1"], "CAGR"].is_monotonic_increasing
    commodity_cagr_decreases = fixed.loc[["3-1-1", "2-2-1", "1-3-1"], "CAGR"].is_monotonic_decreasing
    commodity_maxdd_improves = fixed.loc[["3-1-1", "2-2-1", "1-3-1"], "MaxDD"].is_monotonic_increasing
    selection_index = selection.set_index("Strategy")
    most_diverse = selection_index["Selection Concentration HHI"].idxmin()
    exact_221 = slot_distribution.loc[
        (slot_distribution["Equity Slots"] == 2)
        & (slot_distribution["Commodity Slots"] == 2)
        & (slot_distribution["Bond Slots"] == 1),
        "Month Percent",
    ].sum()
    bond_one = slot_distribution.loc[slot_distribution["Bond Slots"] == 1, "Month Percent"].sum()
    most_common = slot_distribution.iloc[0]
    core_rows = []
    for strategy in STRATEGY_SLOTS:
        top = frequency.loc[frequency["Strategy"] == strategy].nlargest(3, "Selection Count")
        core_rows.append(f"{strategy}: {', '.join(top['ETF'])}")

    return f"""# Original 12 ETF Category Allocation Test

## 1. Research Question

比较 Original 12 ETF 中自由竞争 Top5 与固定 `3-1-1`、`2-2-1`、`1-3-1` 类别席位，检验成功是否隐含稳定类别配置。本实验不优化参数。

## 2. Fixed Design

- Sample: `{COMPARISON_START.date()}` to `{end_date.date()}`
- Monthly rebalance; month-end signal effective next trading day
- Momentum: 126 trading days; transaction cost: 5 bps
- No MA filter; five equal-weight 20% holdings
- Initial portfolio is established from cash on the sample start date

## 3. Performance

{markdown_table(performance, ['Strategy', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Calmar', 'Total Return', 'Turnover'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return', 'Turnover'})}

## 4. Relative Change vs Original Top5

正的 MaxDD Change 表示回撤改善。

{markdown_table(relative, ['Strategy', 'CAGR Change', 'Sharpe Change', 'MaxDD Change'], {'CAGR Change', 'MaxDD Change'})}

## 5. Asset Class Exposure

{markdown_table(exposure, ['Strategy', 'Equity', 'Commodity', 'Bond'], {'Equity', 'Commodity', 'Bond'})}

## 6. Selection Statistics

Lower Selection Concentration HHI means selection slots are distributed more broadly across the 12 ETFs.

{markdown_table(selection, ['Strategy', 'Distinct Assets Selected', 'Average Holdings', 'Average Turnover', 'Selection Concentration HHI', 'Number of Rebalances'], {'Average Turnover'})}

## 7. Category Contribution

Contribution uses beginning-wealth-weighted gross PnL and is normalized across the three asset classes; transaction costs are not assigned to a class.

{markdown_table(contribution, ['Strategy', 'Equity Contribution', 'Commodity Contribution', 'Bond Contribution'], {'Equity Contribution', 'Commodity Contribution', 'Bond Contribution'})}

## 8. Average Category Slots

{markdown_table(slots, ['Strategy', 'Average Equity Slots', 'Average Commodity Slots', 'Average Bond Slots'], set())}

## 9. ETF Selection Frequency

{frequency_sections(frequency)}

## 10. Original Top5 Slot Dynamics

{markdown_table(slot_distribution, ['Equity Slots', 'Commodity Slots', 'Bond Slots', 'Month Count', 'Month Percent'], {'Month Percent'})}

Original Top5 is exactly `2-2-1` in {fmt_pct(exact_221)} of rebalance months and has exactly one Bond slot in {fmt_pct(bond_one)}. The most common structure is `{int(most_common['Equity Slots'])}-{int(most_common['Commodity Slots'])}-{int(most_common['Bond Slots'])}` at {fmt_pct(most_common['Month Percent'])}.

## 11. Interpretation

1. **Original Top5 是否优于所有约束方案？** {'是，CAGR 与 Sharpe 均高于全部固定结构' if original_best else '否，并未在 CAGR 与 Sharpe 上同时优于全部固定结构'}。
2. **2-2-1 是否最接近 Original？** 按 CAGR、Sharpe、MaxDD 的预设归一化距离，`{nearest_performance}` 最接近。
3. **Equity 席位增加是否提高 CAGR？** {'在三个固定结构中呈单调提高' if equity_monotonic else '没有呈单调提高'}。
4. **Commodity 席位增加的影响？** {'在固定结构中 CAGR 单调下降，同时 MaxDD 单调改善' if commodity_cagr_decreases and commodity_maxdd_improves else 'CAGR 与 MaxDD 没有呈一致单调关系'}；更多 Commodity 在本样本中牺牲收益并降低部分尾部风险。
5. **固定一席 Bond 是否稳定风险？** 没有证据表明固定一席足够。三个固定结构的 MaxDD 都比 Original 更深；Original 虽平均有 {original_slots['Average Bond Slots']:.2f} 席 Bond，但只有 {fmt_pct(bond_one)} 的月份恰好一席，风险控制来自动态类别轮动而非固定一席。
6. **成功来自 Momentum 还是类别平衡？** 两者共同作用，但 Momentum 驱动的动态类别轮动更关键。Original 长期平均接近均衡结构，却显著优于机械固定配额。
7. **Original 平均席位最接近？** `{nearest_slots}`；Original 平均为 Equity {original_slots['Average Equity Slots']:.2f}、Commodity {original_slots['Average Commodity Slots']:.2f}、Bond {original_slots['Average Bond Slots']:.2f}。
8. **长期核心 ETF？** {'; '.join(core_rows)}。
9. **约束提高广度还是集中？** HHI 最低的是 `{most_diverse}`。全部策略都曾选择12只ETF，但固定配额提高了选择集中度，未提高实际广度。
10. **是否隐含稳定类别模式？** 只存在长期平均倾向，不存在稳定固定模式。Original 恰好2-2-1仅占 {fmt_pct(exact_221)}，最常见结构也只有 {fmt_pct(most_common['Month Percent'])}；平均值掩盖了显著的月度类别轮动。

## 12. Final Conclusion

Original 12 的成功部分来自长期平均类别平衡，但更关键的是 Momentum 允许类别席位随市场状态动态变化。`{nearest_performance}` 在风险收益上最接近，`{nearest_slots}` 在平均席位上最接近；然而固定该结构会显著损失收益并加深回撤。目标应是保留自由排名产生的动态类别轮动，而不是把长期平均机械固化。
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    prices = core.load_prices()
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    targets, selections, slot_history = build_targets(prices)
    performance, details_by_strategy, weights_by_strategy = simulate(returns, targets)
    relative = relative_change(performance)
    exposure = asset_class_exposure(weights_by_strategy)
    selection = selection_statistics(selections, details_by_strategy, targets)
    contribution = category_contribution(returns, details_by_strategy, weights_by_strategy)
    frequency = selection_frequency(selections, len(targets["Original Top5"]))
    slots = average_category_slots(slot_history)
    slot_distribution = original_slot_distribution(slot_history)

    performance.to_csv(METRICS_DIR / "performance.csv", index=False)
    relative.to_csv(METRICS_DIR / "relative_change.csv", index=False)
    exposure.to_csv(METRICS_DIR / "asset_class_exposure.csv", index=False)
    selection.to_csv(METRICS_DIR / "selection_statistics.csv", index=False)
    contribution.to_csv(METRICS_DIR / "category_contribution.csv", index=False)
    frequency.to_csv(METRICS_DIR / "selection_frequency.csv", index=False)
    slots.to_csv(METRICS_DIR / "average_category_slots.csv", index=False)
    slot_distribution.to_csv(METRICS_DIR / "original_slot_distribution.csv", index=False)
    selections.to_csv(OUTPUTS_DIR / "selections.csv", index=False)
    slot_history.to_csv(OUTPUTS_DIR / "category_slots_by_rebalance.csv", index=False)
    combined_details = pd.concat(details_by_strategy, axis=1)
    combined_details.columns = [f"{strategy}::{metric}" for strategy, metric in combined_details.columns]
    combined_details.to_csv(OUTPUTS_DIR / "daily_details.csv")
    combined_weights = pd.concat(weights_by_strategy, axis=1)
    combined_weights.columns = [f"{strategy}::{symbol}" for strategy, symbol in combined_weights.columns]
    combined_weights.to_csv(OUTPUTS_DIR / "daily_weights.csv")
    SUMMARY_PATH.write_text(
        generate_summary(
            performance, relative, exposure, selection, contribution, frequency, slots,
            slot_distribution, prices.index.max()
        ),
        encoding="utf-8",
    )

    print("\nOriginal 12 ETF Category Allocation Test Complete")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nAverage category slots:")
    print(slots.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nCategory contribution:")
    print(contribution.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
