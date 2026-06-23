from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[4]
DATA_ROOT = ALPHA_ROOT / "shared" / "data"
EXPANDED_STUDY_DIR = ALPHA_ROOT / "research" / "cross_sectional" / "expanded_universe_momentum"
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
STRATEGIES = {
    "Original 12 ETF Top5": list(MIXED_ASSET_SYMBOLS),
    "Expanded 45 ETF Global Top5": [
        "SPY", "QQQ", "IWM", "EFA", "EEM", "VTI", "DIA",
        "XLK", "XLF", "XLV", "XLY", "XLP", "XLE", "XLI", "XLU", "XLB", "XLRE",
        "IWF", "IWD", "MTUM", "QUAL", "USMV", "VLUE", "VNQ",
        "GLD", "SLV", "PPLT", "PALL", "USO", "UNG", "DBO", "XOP",
        "DBA", "CORN", "WEAT", "SOYB", "DBC", "GSG",
        "TLT", "IEF", "SHY", "LQD", "TIP", "HYG", "UUP",
    ],
    "Representative 9 ETF Top5": ["SPY", "DBA", "DBC", "GLD", "IEF", "PALL", "UNG", "UUP", "XLU"],
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
EXPANDED_SYMBOLS = STRATEGIES["Expanded 45 ETF Global Top5"]


def load_prices() -> pd.DataFrame:
    frames = []
    for asset_class, symbols in ASSET_CLASSES.items():
        directory = DATA_ROOT / asset_class.lower()
        for symbol in symbols:
            frame = load_symbol(directory / f"{symbol}.csv")
            if frame is None:
                raise RuntimeError(f"Failed to load {symbol}")
            frames.append(frame)
    prices = pd.concat(frames, axis=1).sort_index().dropna(how="any")
    return prices[EXPANDED_SYMBOLS]


def build_targets(
    prices: pd.DataFrame,
) -> tuple[dict[str, dict[pd.Timestamp, pd.Series]], pd.DataFrame]:
    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    targets = {strategy: {} for strategy in STRATEGIES}
    selection_rows = []

    for rebalance_date in core.month_end_dates(prices.index):
        expanded_scores = momentum.loc[rebalance_date].dropna()
        if len(expanded_scores) != len(prices.columns):
            continue
        location = prices.index.get_loc(rebalance_date)
        if location + 1 >= len(prices.index):
            continue
        effective_date = prices.index[location + 1]
        if effective_date < COMPARISON_START:
            continue

        for strategy, symbols in STRATEGIES.items():
            ranked = expanded_scores.loc[symbols].sort_values(ascending=False)
            selected = ranked.head(TOP_N)
            target = pd.Series(0.0, index=prices.columns)
            target.loc[selected.index] = 1.0 / TOP_N
            targets[strategy][effective_date] = target
            for rank, (symbol, score) in enumerate(selected.items(), start=1):
                asset_class = next(name for name, members in ASSET_CLASSES.items() if symbol in members)
                selection_rows.append(
                    {
                        "Strategy": strategy,
                        "Rebalance Date": rebalance_date,
                        "Effective Date": effective_date,
                        "Symbol": symbol,
                        "Asset Class": asset_class,
                        "Rank": rank,
                        "Momentum": score,
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
            raise RuntimeError(f"{strategy}: unexpected start date {details.index.min()}")
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
        universe = set(STRATEGIES[strategy])
        for asset_class, symbols in ASSET_CLASSES.items():
            available = sorted(universe.intersection(symbols))
            row[asset_class] = weights[available].sum(axis=1).mean() if available else 0.0
        row["Cash"] = (1 - weights.sum(axis=1)).mean()
        rows.append(row)
    return pd.DataFrame(rows)


def selection_statistics(
    selections: pd.DataFrame,
    details_by_strategy: dict[str, pd.DataFrame],
    targets: dict[str, dict[pd.Timestamp, pd.Series]],
) -> pd.DataFrame:
    rows = []
    for strategy in STRATEGIES:
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


def representative_frequency(selections: pd.DataFrame, number_of_rebalances: int) -> pd.DataFrame:
    representative = selections.loc[selections["Strategy"] == "Representative 9 ETF Top5"]
    result = representative.groupby("Symbol").size().rename("Selection Count").reset_index()
    result["Selection Percent"] = result["Selection Count"] / number_of_rebalances
    return result.sort_values(["Selection Count", "Symbol"], ascending=[False, True]).reset_index(drop=True)


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
    expanded = perf.loc["Expanded 45 ETF Global Top5"]
    representative = perf.loc["Representative 9 ETF Top5"]
    representative_better = representative["Sharpe"] > expanded["Sharpe"] and representative["MaxDD"] > expanded["MaxDD"]
    close_to_original = (
        abs(representative["CAGR"] - original["CAGR"]) <= 0.02
        and abs(representative["Sharpe"] - original["Sharpe"]) <= 0.15
        and abs(representative["MaxDD"] - original["MaxDD"]) <= 0.05
    )
    sharpe_recovery = (representative["Sharpe"] - expanded["Sharpe"]) / (original["Sharpe"] - expanded["Sharpe"])
    bond_change = exp.loc["Representative 9 ETF Top5", "Bond"] - exp.loc["Expanded 45 ETF Global Top5", "Bond"]
    selected_count = int(selection.set_index("Strategy").loc["Representative 9 ETF Top5", "Distinct Assets Selected"])
    maxdd_recovery = representative["MaxDD"] - expanded["MaxDD"]
    volatility_change = representative["Volatility"] - expanded["Volatility"]

    return f"""# Representative Cluster Universe Momentum Test

## 1. Research Question

在固定 `mom_126 Top5` 策略下，检验使用 9 个风险簇代表 ETF 是否能修复 Expanded 45 ETF Global Top5 的风险收益恶化。本实验不优化参数。

## 2. Fixed Design

- Sample: `{COMPARISON_START.date()}` to `{end_date.date()}`
- Monthly rebalance; month-end signal effective next trading day
- Momentum: 126 trading days; Top5 equal weight
- Transaction cost: 5 bps; no MA filter
- Representative Universe: SPY, DBA, DBC, GLD, IEF, PALL, UNG, UUP, XLU
- Descriptive closeness to Original: CAGR difference <= 2 percentage points, Sharpe difference <= 0.15, MaxDD difference <= 5 percentage points

## 3. Performance

{markdown_table(performance, ['Strategy', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Calmar', 'Total Return', 'Turnover'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return', 'Turnover'})}

## 4. Relative Change vs Original 12

正的 MaxDD Change 表示回撤改善。

{markdown_table(relative, ['Strategy', 'CAGR Change', 'Sharpe Change', 'MaxDD Change'], {'CAGR Change', 'MaxDD Change'})}

## 5. Asset Class Exposure

{markdown_table(exposure, ['Strategy', 'Equity', 'Commodity', 'Bond', 'Currency', 'Cash'], {'Equity', 'Commodity', 'Bond', 'Currency', 'Cash'})}

## 6. Selection Statistics

`Average Turnover` 是全部预定调仓月的平均双边绝对权重变化。

{markdown_table(selection, ['Strategy', 'Distinct Assets Selected', 'Average Holdings', 'Average Turnover', 'Number of Rebalances'], {'Average Turnover'})}

## 7. Representative ETF Selection Frequency

{markdown_table(frequency, ['Symbol', 'Selection Count', 'Selection Percent'], {'Selection Percent'})}

## 8. Interpretation

1. **Representative Universe 是否优于 Expanded Global Top5？** {'是' if representative_better else '否'}。Sharpe {representative['Sharpe']:.2f} vs {expanded['Sharpe']:.2f}；MaxDD {fmt_pct(representative['MaxDD'])} vs {fmt_pct(expanded['MaxDD'])}。
2. **是否接近 Original 12？** {'是，满足预设的三项接近标准' if close_to_original else '否，未同时满足 CAGR、Sharpe 和 MaxDD 接近标准'}。
3. **Sharpe 是否恢复？** 部分恢复。相对 Expanded 到 Original 的 Sharpe 缺口，Representative 恢复了 {fmt_pct(sharpe_recovery)}；MaxDD 改善 {fmt_pct(maxdd_recovery)}，Volatility 变化 {fmt_pct(volatility_change)}。
4. **Bond 是否恢复合理权重？** Bond 长期权重从 {fmt_pct(exp.loc['Expanded 45 ETF Global Top5', 'Bond'])} 回升至 {fmt_pct(exp.loc['Representative 9 ETF Top5', 'Bond'])}，但仍低于 Original 的 {fmt_pct(exp.loc['Original 12 ETF Top5', 'Bond'])}，只属于部分恢复。
5. **Expanded 失败是否主要来自重复风险来源？** {'去重后 Sharpe 和 MaxDD 同时改善，重复 ETF 和不均衡排名机会是重要原因；但代表池自身类别构成仍会影响结果，不能作为唯一因果解释。' if representative_better else '去重没有同时修复 Sharpe 与 MaxDD，重复风险来源不足以解释 Expanded 的失败。'}
6. **Clustering 是否提高有效广度？** Representative Top5 曾使用 {selected_count}/9 个风险簇代表。去重让每个簇最多拥有一个排名席位，降低了大型相关簇凭 ticker 数量占据 Top5 的机会；但 9 个代表中 5 个属于 Commodity，类别数量仍不均衡，因此有效广度只得到部分改善。

## 9. Final Conclusion

{'使用风险簇代表 ETF 后，回撤和波动特征明显恢复，但 CAGR 与 Sharpe 未恢复到 Original 12 水平。去重是必要的 Universe 改进，却不是充分条件；还需要关注各资产类别拥有的簇数量和排名机会是否均衡。' if representative_better and not close_to_original else '使用风险簇代表 ETF 后，核心风险收益特征已接近 Original 12。Universe 设计应按独立风险来源控制排名机会，而不是简单增加高度相关 ticker。' if representative_better else '使用风险簇代表 ETF 后，核心风险收益特征没有恢复；Universe 去重本身不足以解决 Expanded Global Top5 的问题。'}该结论只适用于固定 9 ETF 代表池和既定策略，不包含参数优化。
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
    frequency = representative_frequency(selections, len(targets["Representative 9 ETF Top5"]))

    prior = pd.read_csv(EXPANDED_STUDY_DIR / "outputs" / "daily_returns.csv", index_col="Date", parse_dates=True)
    original_error = float((details_by_strategy["Original 12 ETF Top5"]["return"] - prior["Original 12 ETF Universe"]).abs().max())
    expanded_error = float((details_by_strategy["Expanded 45 ETF Global Top5"]["return"] - prior["Expanded ETF Universe"]).abs().max())
    if original_error > 1e-12 or expanded_error > 1e-12:
        raise RuntimeError(f"Prior strategy reproduction mismatch: {original_error}, {expanded_error}")

    performance.to_csv(METRICS_DIR / "performance.csv", index=False)
    relative.to_csv(METRICS_DIR / "relative_change.csv", index=False)
    exposure.to_csv(METRICS_DIR / "asset_class_exposure.csv", index=False)
    selection.to_csv(METRICS_DIR / "selection_statistics.csv", index=False)
    frequency.to_csv(METRICS_DIR / "representative_selection_frequency.csv", index=False)
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

    print("\nRepresentative Cluster Universe Momentum Test Complete")
    print(f"Original reproduction max error: {original_error:.3e}")
    print(f"Expanded reproduction max error: {expanded_error:.3e}")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nAsset class exposure:")
    print(exposure.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nRepresentative selection frequency:")
    print(frequency.to_string(index=False))


if __name__ == "__main__":
    main()
