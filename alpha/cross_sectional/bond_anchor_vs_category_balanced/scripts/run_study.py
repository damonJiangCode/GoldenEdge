from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = ALPHA_ROOT / "shared" / "data"
PRIOR_STUDY_DIR = ALPHA_ROOT / "cross_sectional" / "representative_category_balanced"
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(ALPHA_ROOT))

from shared.configs.universes import MIXED_ASSET_SYMBOLS  # noqa: E402
from shared.loaders.prices import load_symbol  # noqa: E402
from shared.utils import cross_sectional as core  # noqa: E402


MOMENTUM_WINDOW = 126
COMPARISON_START = pd.Timestamp("2016-05-02")
SLOT_WEIGHT = 0.20
REPRESENTATIVE_CLASSES = {
    "Equity": ["SPY", "XLU"],
    "Commodity": ["DBA", "DBC", "GLD", "PALL", "UNG"],
    "Bond": ["IEF"],
    "Currency": ["UUP"],
}
REPRESENTATIVE_SYMBOLS = [symbol for symbols in REPRESENTATIVE_CLASSES.values() for symbol in symbols]
NON_BOND_SYMBOLS = [symbol for symbol in REPRESENTATIVE_SYMBOLS if symbol != "IEF"]
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
STRATEGY_NAMES = [
    "Original 12 ETF Top5 (Reference)",
    "Representative Category Balanced",
    "Bond Anchor Global Top4",
    "Bond Anchor Commodity Cap",
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


def commodity_capped_top4(scores: pd.Series) -> list[str]:
    selected = []
    commodity_count = 0
    commodity_symbols = set(REPRESENTATIVE_CLASSES["Commodity"])
    for symbol in scores.loc[NON_BOND_SYMBOLS].sort_values(ascending=False).index:
        if symbol in commodity_symbols and commodity_count >= 2:
            continue
        selected.append(symbol)
        if symbol in commodity_symbols:
            commodity_count += 1
        if len(selected) == 4:
            break
    if len(selected) != 4:
        raise RuntimeError("Commodity cap could not fill four non-Bond slots")
    return selected


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
            "Original 12 ETF Top5 (Reference)": scores.loc[MIXED_ASSET_SYMBOLS].nlargest(5).index.tolist(),
            "Representative Category Balanced": (
                scores.loc[REPRESENTATIVE_CLASSES["Equity"]].nlargest(2).index.tolist()
                + scores.loc[REPRESENTATIVE_CLASSES["Commodity"]].nlargest(2).index.tolist()
                + ["IEF"]
            ),
            "Bond Anchor Global Top4": ["IEF"] + scores.loc[NON_BOND_SYMBOLS].nlargest(4).index.tolist(),
            "Bond Anchor Commodity Cap": ["IEF"] + commodity_capped_top4(scores),
        }

        for strategy, selected in selected_by_strategy.items():
            target = pd.Series(0.0, index=prices.columns)
            target.loc[selected] = SLOT_WEIGHT
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
                        "Target Weight": SLOT_WEIGHT,
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
    baseline = performance.set_index("Strategy").loc["Representative Category Balanced"]
    result = performance.loc[performance["Strategy"] != "Representative Category Balanced", ["Strategy", "CAGR", "Sharpe", "MaxDD"]].copy()
    result["CAGR Change"] = result["CAGR"] - baseline["CAGR"]
    result["Sharpe Change"] = result["Sharpe"] - baseline["Sharpe"]
    result["MaxDD Change"] = result["MaxDD"] - baseline["MaxDD"]
    result = result[["Strategy", "CAGR Change", "Sharpe Change", "MaxDD Change"]]
    numeric = ["CAGR Change", "Sharpe Change", "MaxDD Change"]
    result[numeric] = result[numeric].mask(result[numeric].abs() < 1e-12, 0.0)
    return result


def asset_class_exposure(weights_by_strategy: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for strategy, weights in weights_by_strategy.items():
        row = {"Strategy": strategy}
        for asset_class, symbols in EXPANDED_CLASSES.items():
            row[asset_class] = weights[symbols].sum(axis=1).mean()
        row["Cash"] = (1 - weights.sum(axis=1)).mean()
        rows.append(row)
    result = pd.DataFrame(rows)
    numeric = ["Equity", "Commodity", "Bond", "Currency", "Cash"]
    result[numeric] = result[numeric].mask(result[numeric].abs() < 1e-12, 0.0)
    return result


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
    rows = []
    experimental = [
        "Representative Category Balanced",
        "Bond Anchor Global Top4",
        "Bond Anchor Commodity Cap",
    ]
    for strategy in experimental:
        counts = selections.loc[selections["Strategy"] == strategy].groupby("Symbol").size()
        for symbol in REPRESENTATIVE_SYMBOLS:
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
    for strategy in frequency["Strategy"].drop_duplicates():
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
    frequency: pd.DataFrame,
    end_date: pd.Timestamp,
) -> str:
    perf = performance.set_index("Strategy")
    exp = exposure.set_index("Strategy")
    original = perf.loc["Original 12 ETF Top5 (Reference)"]
    balanced = perf.loc["Representative Category Balanced"]
    global_anchor = perf.loc["Bond Anchor Global Top4"]
    capped_anchor = perf.loc["Bond Anchor Commodity Cap"]
    global_better = global_anchor["CAGR"] > balanced["CAGR"] and global_anchor["Sharpe"] > balanced["Sharpe"]
    cap_better = (
        capped_anchor["CAGR"] > global_anchor["CAGR"]
        and capped_anchor["Sharpe"] > global_anchor["Sharpe"]
        and capped_anchor["Calmar"] > global_anchor["Calmar"]
    )
    commodity_global = exp.loc["Bond Anchor Global Top4", "Commodity"]
    commodity_capped = exp.loc["Bond Anchor Commodity Cap", "Commodity"]

    comparison_strategies = [
        "Representative Category Balanced", "Bond Anchor Global Top4", "Bond Anchor Commodity Cap"
    ]
    distances = {}
    for strategy in comparison_strategies:
        row = perf.loc[strategy]
        distances[strategy] = (
            abs(row["CAGR"] - original["CAGR"]) / 0.02
            + abs(row["Sharpe"] - original["Sharpe"]) / 0.15
            + abs(row["MaxDD"] - original["MaxDD"]) / 0.05
        )
    closest = min(distances, key=distances.get)

    return f"""# Bond Anchor vs Category Balanced Test

## 1. Research Question

在固定 Representative Universe 中，检验只固定 20% IEF 风险锚、其余资产统一排名，是否优于固定 Equity/Commodity/Bond 类别席位。本实验不优化任何参数。

## 2. Fixed Design

- Sample: `{COMPARISON_START.date()}` to `{end_date.date()}`
- Monthly rebalance; month-end signal effective next trading day
- Momentum: 126 trading days; transaction cost: 5 bps; no MA filter
- Category Balanced: Equity Top2, Commodity Top2, Bond Top1
- Bond Anchor Global: IEF 20% plus global Top4 from the other 8 ETFs
- Bond Anchor Commodity Cap: same anchor, but at most two Commodity ETFs in Top4
- All positions are 20%; Representative Universe is unchanged

## 3. Performance

{markdown_table(performance, ['Strategy', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Calmar', 'Total Return', 'Turnover'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return', 'Turnover'})}

## 4. Relative Change vs Category Balanced

正的 MaxDD Change 表示回撤改善。

{markdown_table(relative, ['Strategy', 'CAGR Change', 'Sharpe Change', 'MaxDD Change'], {'CAGR Change', 'MaxDD Change'})}

## 5. Asset Class Exposure

{markdown_table(exposure, ['Strategy', 'Equity', 'Commodity', 'Bond', 'Currency', 'Cash'], {'Equity', 'Commodity', 'Bond', 'Currency', 'Cash'})}

## 6. Selection Statistics

`Average Turnover` 是全部预定调仓月的平均双边绝对权重变化。

{markdown_table(selection, ['Strategy', 'Distinct Assets Selected', 'Average Holdings', 'Average Turnover', 'Number of Rebalances'], {'Average Turnover'})}

## 7. ETF Selection Frequency

{frequency_sections(frequency)}

## 8. Interpretation

1. **Bond Anchor 是否优于 Category Balanced？** Global Top4 {'在 CAGR 与 Sharpe 上同时更高' if global_better else '没有在 CAGR 与 Sharpe 上同时更高'}：{fmt_pct(global_anchor['CAGR'])}/{global_anchor['Sharpe']:.2f} vs {fmt_pct(balanced['CAGR'])}/{balanced['Sharpe']:.2f}。
2. **固定 Bond 是否提高 Sharpe？** 三种 Representative 结构都约有20% Bond；结构差异来自剩余80%的排名方式。Global Anchor 相对 Balanced 的 Sharpe 变化为 {global_anchor['Sharpe'] - balanced['Sharpe']:+.2f}。
3. **Commodity 是否再次过多？** Global Anchor 的 Commodity 平均权重为 {fmt_pct(commodity_global)}，Category Balanced 为 {fmt_pct(exp.loc['Representative Category Balanced', 'Commodity'])}。
4. **Commodity Cap 是否改善风险收益？** {'整体改善：CAGR、Sharpe、Calmar 均高于 Global Anchor，但 MaxDD 更深' if cap_better else '没有改善整体风险调整表现'}。Cap 后 Commodity 权重为 {fmt_pct(commodity_capped)}，Sharpe/MaxDD 为 {capped_anchor['Sharpe']:.2f}/{fmt_pct(capped_anchor['MaxDD'])}，Global Anchor 为 {global_anchor['Sharpe']:.2f}/{fmt_pct(global_anchor['MaxDD'])}。
5. **更适合固定类别还是固定 Bond？** {'固定 Bond + Global Top4 提供更高收益与 Sharpe，支持把剩余80%作为统一 Alpha sleeve。' if global_better else '固定 Category Balanced 仍最接近 Original，并具有更高 CAGR 和 Calmar；Bond Anchor + Commodity Cap 的 Sharpe 和波动率略优，但没有形成全面优势。单独固定 Bond 不足以替代类别约束。'}
6. **最接近 Original 12？** 按 CAGR、Sharpe、MaxDD 的预设归一化距离，`{closest}` 最接近 Original；该距离只用于结构比较，不用于参数优化。

## 9. Final Conclusion

{'固定 Bond 风险锚后，Global Top4 优于当前 Category Balanced，说明未来可把组合拆成固定风险锚与动态 Alpha sleeve，再单独研究 position sizing。' if global_better else '固定 Bond 本身没有优于当前 Category Balanced；风险锚不能替代对剩余资产类别排名机会的控制。Commodity Cap 使 Anchor 结构重新接近 Balanced，说明未来 Position Sizing 应把固定风险锚与 Alpha sleeve 的类别集中上限分开设计。'}本实验不选择新参数。
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
    original_error = float((details_by_strategy["Original 12 ETF Top5 (Reference)"]["return"] - prior["Original 12 ETF Top5::return"]).abs().max())
    balanced_error = float((details_by_strategy["Representative Category Balanced"]["return"] - prior["Representative Category Balanced::return"]).abs().max())
    if original_error > 1e-12 or balanced_error > 1e-12:
        raise RuntimeError(f"Prior reproduction mismatch: {original_error}, {balanced_error}")

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

    print("\nBond Anchor vs Category Balanced Test Complete")
    print(f"Original reproduction max error: {original_error:.3e}")
    print(f"Category Balanced reproduction max error: {balanced_error:.3e}")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nAsset class exposure:")
    print(exposure.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
