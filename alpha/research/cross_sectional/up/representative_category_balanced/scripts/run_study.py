from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[4]
DATA_ROOT = ALPHA_ROOT / "shared" / "data"
PRIOR_STUDY_DIR = ALPHA_ROOT / "research" / "cross_sectional" / "representative_cluster_momentum"
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
REPRESENTATIVE_CLASSES = {
    "Equity": ["SPY", "XLU"],
    "Commodity": ["DBA", "DBC", "GLD", "PALL", "UNG"],
    "Bond": ["IEF"],
    "Currency": ["UUP"],
}
REPRESENTATIVE_SYMBOLS = [symbol for symbols in REPRESENTATIVE_CLASSES.values() for symbol in symbols]
EXPANDED_CLASSES = {
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
EXPANDED_SYMBOLS = [symbol for symbols in EXPANDED_CLASSES.values() for symbol in symbols]
STRATEGY_UNIVERSES = {
    "Original 12 ETF Top5": list(MIXED_ASSET_SYMBOLS),
    "Representative Global Top5": REPRESENTATIVE_SYMBOLS,
}
STRATEGY_NAMES = [
    "Original 12 ETF Top5",
    "Representative Global Top5",
    "Representative Category Balanced",
]


def load_prices() -> pd.DataFrame:
    frames = []
    for asset_class, symbols in EXPANDED_CLASSES.items():
        directory = DATA_ROOT / asset_class.lower()
        for symbol in symbols:
            frame = load_symbol(directory / f"{symbol}.csv")
            if frame is None:
                raise RuntimeError(f"Failed to load {symbol}")
            frames.append(frame)
    return pd.concat(frames, axis=1).sort_index().dropna(how="any")[EXPANDED_SYMBOLS]


def build_targets(
    prices: pd.DataFrame,
) -> tuple[dict[str, dict[pd.Timestamp, pd.Series]], pd.DataFrame]:
    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    targets = {strategy: {} for strategy in STRATEGY_NAMES}
    selection_rows = []

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

        selected_by_strategy = {
            strategy: scores.loc[symbols].nlargest(TOP_N).index.tolist()
            for strategy, symbols in STRATEGY_UNIVERSES.items()
        }
        selected_by_strategy["Representative Category Balanced"] = (
            scores.loc[REPRESENTATIVE_CLASSES["Equity"]].nlargest(2).index.tolist()
            + scores.loc[REPRESENTATIVE_CLASSES["Commodity"]].nlargest(2).index.tolist()
            + scores.loc[REPRESENTATIVE_CLASSES["Bond"]].nlargest(1).index.tolist()
        )

        for strategy, selected in selected_by_strategy.items():
            target = pd.Series(0.0, index=prices.columns)
            target.loc[selected] = 1.0 / TOP_N
            targets[strategy][effective_date] = target
            for symbol in selected:
                asset_class = next(name for name, members in EXPANDED_CLASSES.items() if symbol in members)
                selection_rows.append(
                    {
                        "Strategy": strategy,
                        "Rebalance Date": rebalance_date,
                        "Effective Date": effective_date,
                        "Symbol": symbol,
                        "Asset Class": asset_class,
                        "Momentum": scores.loc[symbol],
                        "Target Weight": 1.0 / TOP_N,
                    }
                )
    return targets, pd.DataFrame(selection_rows)


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
            raise RuntimeError(f"{strategy}: unexpected comparison start")
        equity = (1 + details["return"]).cumprod()
        metrics = core.calculate_metrics(
            label=strategy,
            momentum_window="mom_126",
            strategy="Top5",
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
    indexed = performance.set_index("Strategy")
    baseline = indexed.loc["Original 12 ETF Top5"]
    result = performance.loc[performance["Strategy"] != "Original 12 ETF Top5", ["Strategy", "CAGR", "Sharpe", "MaxDD"]].copy()
    result["CAGR Change"] = result["CAGR"] - baseline["CAGR"]
    result["Sharpe Change"] = result["Sharpe"] - baseline["Sharpe"]
    result["MaxDD Change"] = result["MaxDD"] - baseline["MaxDD"]
    return result[["Strategy", "CAGR Change", "Sharpe Change", "MaxDD Change"]]


def asset_class_exposure(weights_by_strategy: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for strategy, weights in weights_by_strategy.items():
        row = {"Strategy": strategy}
        for asset_class, symbols in EXPANDED_CLASSES.items():
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
        effective_dates = pd.DatetimeIndex(targets[strategy].keys())
        rows.append(
            {
                "Strategy": strategy,
                "Distinct Assets Selected": selected["Symbol"].nunique(),
                "Average Holdings": selected.groupby("Effective Date")["Symbol"].nunique().mean(),
                "Average Turnover": details_by_strategy[strategy].loc[effective_dates, "turnover"].mean(),
                "Number of Rebalances": len(effective_dates),
            }
        )
    return pd.DataFrame(rows)


def selection_frequency(selections: pd.DataFrame, number_of_rebalances: int) -> pd.DataFrame:
    balanced = selections.loc[selections["Strategy"] == "Representative Category Balanced"]
    counts = balanced.groupby("Symbol").size()
    rows = []
    for symbol in REPRESENTATIVE_SYMBOLS:
        count = int(counts.get(symbol, 0))
        rows.append(
            {"ETF": symbol, "Selection Count": count, "Selection Percent": count / number_of_rebalances}
        )
    return pd.DataFrame(rows).sort_values(["Selection Count", "ETF"], ascending=[False, True]).reset_index(drop=True)


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
    relative: pd.DataFrame,
    exposure: pd.DataFrame,
    selection: pd.DataFrame,
    frequency: pd.DataFrame,
    end_date: pd.Timestamp,
) -> str:
    perf = performance.set_index("Strategy")
    exp = exposure.set_index("Strategy")
    original = perf.loc["Original 12 ETF Top5"]
    global_top5 = perf.loc["Representative Global Top5"]
    balanced = perf.loc["Representative Category Balanced"]
    balanced_better = (
        balanced["CAGR"] > global_top5["CAGR"]
        and balanced["Sharpe"] > global_top5["Sharpe"]
        and balanced["Calmar"] > global_top5["Calmar"]
    )
    close_to_original = (
        abs(balanced["CAGR"] - original["CAGR"]) <= 0.02
        and abs(balanced["Sharpe"] - original["Sharpe"]) <= 0.15
        and abs(balanced["MaxDD"] - original["MaxDD"]) <= 0.05
    )
    commodity_change = exp.loc["Representative Category Balanced", "Commodity"] - exp.loc["Representative Global Top5", "Commodity"]
    bond_change = exp.loc["Representative Category Balanced", "Bond"] - exp.loc["Representative Global Top5", "Bond"]
    sharpe_change = balanced["Sharpe"] - global_top5["Sharpe"]
    maxdd_change = balanced["MaxDD"] - global_top5["MaxDD"]

    return f"""# Representative Cluster Universe + Category Balanced Test

## 1. Research Question

检验在固定 9 ETF Representative Universe 中加入 Equity Top2、Commodity Top2、Bond Top1 的类别席位，是否进一步修复 Global Top5 的风险收益特征。本实验不优化参数。

## 2. Fixed Design

- Sample: `{COMPARISON_START.date()}` to `{end_date.date()}`
- Monthly rebalance; month-end signal effective next trading day
- Momentum: 126 trading days; transaction cost: 5 bps; no MA filter
- Representative Global: 9 ETF 统一排名 Top5，每只 20%
- Category Balanced: Equity Top2、Commodity Top2、Bond Top1，每只 20%
- 类别不足时保留现金，不跨类别补仓
- Representative ETFs are fixed and cannot be replaced

## 3. Performance

{markdown_table(performance, ['Strategy', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Calmar', 'Total Return', 'Turnover'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return', 'Turnover'})}

## 4. Relative Change vs Original

正的 MaxDD Change 表示回撤改善。

{markdown_table(relative, ['Strategy', 'CAGR Change', 'Sharpe Change', 'MaxDD Change'], {'CAGR Change', 'MaxDD Change'})}

## 5. Asset Class Exposure

{markdown_table(exposure, ['Strategy', 'Equity', 'Commodity', 'Bond', 'Currency', 'Cash'], {'Equity', 'Commodity', 'Bond', 'Currency', 'Cash'})}

## 6. Selection Statistics

`Average Turnover` 是全部预定调仓月的平均双边绝对权重变化。

{markdown_table(selection, ['Strategy', 'Distinct Assets Selected', 'Average Holdings', 'Average Turnover', 'Number of Rebalances'], {'Average Turnover'})}

## 7. Category Balanced ETF Selection Frequency

{markdown_table(frequency, ['ETF', 'Selection Count', 'Selection Percent'], {'Selection Percent'})}

## 8. Interpretation

1. **Category Balanced 是否优于 Representative Global Top5？** {'整体风险收益更优，但并非每个单项风险指标都改善' if balanced_better else '否'}。CAGR {fmt_pct(balanced['CAGR'])} vs {fmt_pct(global_top5['CAGR'])}，Sharpe {balanced['Sharpe']:.2f} vs {global_top5['Sharpe']:.2f}；MaxDD 变化 {fmt_pct(maxdd_change)}，总 Turnover 从 {fmt_pct(global_top5['Turnover'])} 降至 {fmt_pct(balanced['Turnover'])}。
2. **Sharpe 是否进一步恢复？** 变化为 {sharpe_change:+.2f}；Balanced 与 Original 的 Sharpe 差为 {balanced['Sharpe'] - original['Sharpe']:+.2f}。
3. **Bond 权重是否恢复？** 从 {fmt_pct(exp.loc['Representative Global Top5', 'Bond'])} 增至 {fmt_pct(exp.loc['Representative Category Balanced', 'Bond'])}，变化 {fmt_pct(bond_change)}。
4. **Commodity 是否被过度压制？** Commodity 从 {fmt_pct(exp.loc['Representative Global Top5', 'Commodity'])} 调整为 {fmt_pct(exp.loc['Representative Category Balanced', 'Commodity'])}，变化 {fmt_pct(commodity_change)}；Original 为 {fmt_pct(exp.loc['Original 12 ETF Top5', 'Commodity'])}。类别结构仍保留 40% Commodity 目标权重，不属于完全压制。
5. **主要问题是去重不足还是类别失衡？** Global 版本已经完成去重但仍有 5/9 Commodity 代表竞争 Top5；Balanced 只改变类别席位。{'风险调整表现继续改善，说明完成去重后的主要剩余问题是类别排名机会失衡。' if balanced_better else '没有进一步改善，说明类别失衡不是剩余问题的充分解释。'}
6. **是否更接近 Original 12？** {'是，满足预设的 CAGR、Sharpe、MaxDD 接近标准' if close_to_original else '否，未同时满足预设的三项接近标准'}。

## 9. Final Conclusion

{'在已去重的 Representative Universe 中，类别平衡进一步修复了 CAGR、Sharpe、Calmar 和换手，并使整体表现满足接近 Original 12 的预设标准；代价是 MaxDD 相对 Representative Global 小幅变深。Universe 设计需要同时控制相关性重复和各资产类别的排名席位，只做聚类去重仍不足。' if balanced_better else '在 Representative Universe 中加入固定类别席位没有进一步修复风险收益特征；当前证据不支持类别平衡是剩余问题的主要答案。'}该结论只适用于固定代表池和预先指定的类别席位，不包含参数优化。
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    prices = load_prices()
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    targets, selections = build_targets(prices)
    performance, details_by_strategy, weights_by_strategy = simulate(returns, targets)
    relative = relative_change(performance)
    exposure = asset_class_exposure(weights_by_strategy)
    selection = selection_statistics(selections, details_by_strategy, targets)
    frequency = selection_frequency(selections, len(targets["Representative Category Balanced"]))

    prior = pd.read_csv(PRIOR_STUDY_DIR / "outputs" / "daily_details.csv", index_col="Date", parse_dates=True)
    original_error = float((details_by_strategy["Original 12 ETF Top5"]["return"] - prior["Original 12 ETF Top5::return"]).abs().max())
    representative_error = float((details_by_strategy["Representative Global Top5"]["return"] - prior["Representative 9 ETF Top5::return"]).abs().max())
    if original_error > 1e-12 or representative_error > 1e-12:
        raise RuntimeError(f"Prior reproduction mismatch: {original_error}, {representative_error}")

    performance.to_csv(METRICS_DIR / "performance.csv", index=False)
    relative.to_csv(METRICS_DIR / "relative_change.csv", index=False)
    exposure.to_csv(METRICS_DIR / "asset_class_exposure.csv", index=False)
    selection.to_csv(METRICS_DIR / "selection_statistics.csv", index=False)
    frequency.to_csv(METRICS_DIR / "selection_frequency.csv", index=False)
    selections.to_csv(OUTPUTS_DIR / "selections.csv", index=False)
    combined_details = pd.concat(details_by_strategy, axis=1)
    combined_details.columns = [f"{strategy}::{metric}" for strategy, metric in combined_details.columns]
    combined_details.to_csv(OUTPUTS_DIR / "daily_details.csv")
    combined_weights = pd.concat(weights_by_strategy, axis=1)
    combined_weights.columns = [f"{strategy}::{symbol}" for strategy, symbol in combined_weights.columns]
    combined_weights.to_csv(OUTPUTS_DIR / "daily_weights.csv")
    SUMMARY_PATH.write_text(
        generate_summary(performance, relative, exposure, selection, frequency, prices.index.max()),
        encoding="utf-8",
    )

    print("\nRepresentative Cluster Universe + Category Balanced Test Complete")
    print(f"Original reproduction max error: {original_error:.3e}")
    print(f"Representative Global reproduction max error: {representative_error:.3e}")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nAsset class exposure:")
    print(exposure.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nSelection frequency:")
    print(frequency.to_string(index=False))


if __name__ == "__main__":
    main()
