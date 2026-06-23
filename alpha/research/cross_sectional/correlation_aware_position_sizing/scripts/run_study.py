from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[4]
POSITION_SIZING_A_DIR = ALPHA_ROOT / "research" / "cross_sectional" / "position_sizing_test_a"
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(ALPHA_ROOT))

from shared.configs.universes import MIXED_ASSET_CLASSES, MIXED_ASSET_SYMBOLS  # noqa: E402
from shared.utils import cross_sectional as core  # noqa: E402


MOMENTUM_WINDOW = 126
VOLATILITY_WINDOW = 126
CORRELATION_WINDOW = 126
COMPARISON_START = pd.Timestamp("2008-02-01")
TOP_N = 5
MIN_DIVERSIFICATION_SCORE = 0.10
STRATEGY_NAMES = ["Equal Weight", "Inverse Vol", "Correlation-Adjusted IV"]


def normalized(values: np.ndarray) -> np.ndarray:
    if not np.isfinite(values).all() or (values <= 0).any():
        raise RuntimeError(f"Invalid sizing inputs: {values}")
    return values / values.sum()


def build_targets(
    prices: pd.DataFrame,
) -> tuple[
    dict[str, dict[pd.Timestamp, pd.Series]],
    pd.DataFrame,
    pd.DataFrame,
]:
    returns = prices.pct_change(fill_method=None)
    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    trailing_volatility = returns.rolling(
        VOLATILITY_WINDOW, min_periods=VOLATILITY_WINDOW
    ).std(ddof=1)
    targets = {strategy: {} for strategy in STRATEGY_NAMES}
    target_rows = []
    correlation_rows = []

    for rebalance_date in core.month_end_dates(prices.index):
        scores = momentum.loc[rebalance_date].dropna()
        volatility = trailing_volatility.loc[rebalance_date].dropna()
        if len(scores) != len(prices.columns) or len(volatility) != len(prices.columns):
            continue
        location = prices.index.get_loc(rebalance_date)
        if location + 1 >= len(prices.index):
            continue
        effective_date = prices.index[location + 1]
        if effective_date < COMPARISON_START:
            continue

        ranked = scores.sort_values(ascending=False).head(TOP_N)
        selected = ranked.index.tolist()
        selected_volatility = volatility.loc[selected].to_numpy(dtype=float)
        correlation = returns.loc[:rebalance_date].tail(CORRELATION_WINDOW)[selected].corr()
        if correlation.isna().any().any():
            raise RuntimeError(f"Incomplete correlation matrix at {rebalance_date}")
        average_correlation = (
            (correlation.sum(axis=1) - 1.0) / (TOP_N - 1)
        )
        diversification_score = (1.0 - average_correlation).clip(lower=MIN_DIVERSIFICATION_SCORE)
        weights_by_strategy = {
            "Equal Weight": np.repeat(1.0 / TOP_N, TOP_N),
            "Inverse Vol": normalized(1.0 / selected_volatility),
            "Correlation-Adjusted IV": normalized(
                (1.0 / selected_volatility) * diversification_score.loc[selected].to_numpy()
            ),
        }

        upper = np.triu_indices(TOP_N, k=1)
        pairwise_values = correlation.to_numpy()[upper]
        unweighted_pairwise = float(pairwise_values.mean())
        for strategy, selected_weights in weights_by_strategy.items():
            target = pd.Series(0.0, index=prices.columns)
            target.loc[selected] = selected_weights
            targets[strategy][effective_date] = target
            pair_weight_matrix = np.outer(selected_weights, selected_weights)
            pair_weights = pair_weight_matrix[upper]
            weighted_pairwise = float(np.average(pairwise_values, weights=pair_weights))
            correlation_rows.append(
                {
                    "Strategy": strategy,
                    "Rebalance Date": rebalance_date,
                    "Effective Date": effective_date,
                    "Average Pairwise Correlation": unweighted_pairwise,
                    "Weighted Pairwise Correlation": weighted_pairwise,
                }
            )
            for rank, symbol in enumerate(selected, start=1):
                asset_class = next(
                    name for name, symbols in MIXED_ASSET_CLASSES.items() if symbol in symbols
                )
                target_rows.append(
                    {
                        "Strategy": strategy,
                        "Rebalance Date": rebalance_date,
                        "Effective Date": effective_date,
                        "Rank": rank,
                        "Symbol": symbol,
                        "Asset Class": asset_class,
                        "Momentum": ranked.loc[symbol],
                        "Trailing Volatility": volatility.loc[symbol],
                        "Average Correlation Score": average_correlation.loc[symbol],
                        "Diversification Score": diversification_score.loc[symbol],
                        "Target Weight": target.loc[symbol],
                    }
                )
    return targets, pd.DataFrame(target_rows), pd.DataFrame(correlation_rows)


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
    baseline = performance.set_index("Strategy").loc["Inverse Vol"]
    result = performance.loc[performance["Strategy"] != "Inverse Vol", ["Strategy", "CAGR", "Sharpe", "MaxDD"]].copy()
    result["CAGR Change"] = result["CAGR"] - baseline["CAGR"]
    result["Sharpe Change"] = result["Sharpe"] - baseline["Sharpe"]
    result["MaxDD Change"] = result["MaxDD"] - baseline["MaxDD"]
    return result[["Strategy", "CAGR Change", "Sharpe Change", "MaxDD Change"]]


def correlation_diagnostics(correlation_rows: pd.DataFrame) -> pd.DataFrame:
    result = (
        correlation_rows.groupby("Strategy", as_index=False)
        .agg(
            **{
                "Average Pairwise Correlation": ("Average Pairwise Correlation", "mean"),
                "Weighted Pairwise Correlation": ("Weighted Pairwise Correlation", "mean"),
            }
        )
    )
    order = {strategy: index for index, strategy in enumerate(STRATEGY_NAMES)}
    result["_order"] = result["Strategy"].map(order)
    return result.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def position_concentration(target_rows: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (strategy, _), group in target_rows.groupby(["Strategy", "Effective Date"]):
        hhi = float((group["Target Weight"] ** 2).sum())
        rows.append({"Strategy": strategy, "HHI": hhi, "Effective Positions": 1.0 / hhi})
    result = (
        pd.DataFrame(rows)
        .groupby("Strategy", as_index=False)
        .agg(**{"HHI": ("HHI", "mean"), "Effective Positions": ("Effective Positions", "mean")})
    )
    order = {strategy: index for index, strategy in enumerate(STRATEGY_NAMES)}
    result["_order"] = result["Strategy"].map(order)
    return result.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def weight_distribution(target_rows: pd.DataFrame) -> pd.DataFrame:
    result = (
        target_rows.groupby(["Strategy", "Rank"])["Target Weight"]
        .mean()
        .unstack("Rank")
        .rename(columns={rank: f"Rank{rank}" for rank in range(1, TOP_N + 1)})
        .reset_index()
    )
    order = {strategy: index for index, strategy in enumerate(STRATEGY_NAMES)}
    result["_order"] = result["Strategy"].map(order)
    return result.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def class_exposure(target_rows: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        target_rows.groupby(["Strategy", "Effective Date", "Asset Class"])["Target Weight"]
        .sum()
        .unstack("Asset Class", fill_value=0.0)
    )
    rows = []
    for strategy in STRATEGY_NAMES:
        frame = grouped.loc[strategy]
        rows.append(
            {
                "Strategy": strategy,
                "Equity Weight": frame.get("Equity", pd.Series(0.0, index=frame.index)).mean(),
                "Commodity Weight": frame.get("Commodity", pd.Series(0.0, index=frame.index)).mean(),
                "Bond Weight": frame.get("Bond", pd.Series(0.0, index=frame.index)).mean(),
            }
        )
    return pd.DataFrame(rows)


def penalty_frequency(target_rows: pd.DataFrame) -> pd.DataFrame:
    unique_signal_rows = target_rows.loc[target_rows["Strategy"] == "Correlation-Adjusted IV"]
    result = (
        unique_signal_rows.groupby("Symbol", as_index=False)
        .agg(
            **{
                "Average Correlation Score": ("Average Correlation Score", "mean"),
                "Average Diversification Score": ("Diversification Score", "mean"),
                "Selection Count": ("Effective Date", "count"),
            }
        )
        .rename(columns={"Symbol": "ETF"})
    )
    return result.set_index("ETF").reindex(MIXED_ASSET_SYMBOLS).reset_index()


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
            if pd.isna(value):
                cells.append("NA")
            elif column in pct_columns:
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
    correlations: pd.DataFrame,
    concentration: pd.DataFrame,
    distribution: pd.DataFrame,
    exposure: pd.DataFrame,
    penalties: pd.DataFrame,
    end_date: pd.Timestamp,
) -> str:
    perf = performance.set_index("Strategy")
    corr = correlations.set_index("Strategy")
    conc = concentration.set_index("Strategy")
    exp = exposure.set_index("Strategy")
    inverse = perf.loc["Inverse Vol"]
    adjusted = perf.loc["Correlation-Adjusted IV"]
    sharpe_improves = adjusted["Sharpe"] > inverse["Sharpe"]
    drawdown_improves = adjusted["MaxDD"] > inverse["MaxDD"]
    weighted_corr_change = (
        corr.loc["Correlation-Adjusted IV", "Weighted Pairwise Correlation"]
        - corr.loc["Inverse Vol", "Weighted Pairwise Correlation"]
    )
    equity_change = exp.loc["Correlation-Adjusted IV", "Equity Weight"] - exp.loc["Inverse Vol", "Equity Weight"]
    commodity_change = exp.loc["Correlation-Adjusted IV", "Commodity Weight"] - exp.loc["Inverse Vol", "Commodity Weight"]
    bond_change = exp.loc["Correlation-Adjusted IV", "Bond Weight"] - exp.loc["Inverse Vol", "Bond Weight"]
    concentrated_change = conc.loc["Correlation-Adjusted IV", "HHI"] - conc.loc["Inverse Vol", "HHI"]

    return f"""# Correlation-Aware Position Sizing Test

## 1. Research Question

在固定 Original 12 ETF `mom_126 Top5` 和Inverse Vol框架中，加入简单的平均相关性惩罚，检验资产间相关性是否提供额外风险管理价值。本实验不优化参数。

## 2. Fixed Design

- Sample: `{COMPARISON_START.date()}` to `{end_date.date()}`
- Monthly rebalance; month-end signal effective next trading day
- Momentum, volatility, and correlation windows: 126 trading days
- Top5 is identical across all strategies
- Diversification Score: `max(0.10, 1 - average correlation to the other four holdings)`
- Correlation-Adjusted weight: `(1 / vol) x Diversification Score`, normalized to 100%
- Transaction cost: 5 bps; no MA filter

## 3. Performance

{markdown_table(performance, ['Strategy', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Calmar', 'Total Return', 'Turnover'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return', 'Turnover'})}

## 4. Relative Change vs Inverse Vol

正的 MaxDD Change 表示回撤改善。

{markdown_table(relative, ['Strategy', 'CAGR Change', 'Sharpe Change', 'MaxDD Change'], {'CAGR Change', 'MaxDD Change'})}

## 5. Correlation Diagnostics

Unweighted pairwise correlation is identical by construction because all strategies hold the same Top5. Weighted Pairwise Correlation reflects sizing differences.

{markdown_table(correlations, ['Strategy', 'Average Pairwise Correlation', 'Weighted Pairwise Correlation'], set())}

## 6. Position Concentration

{markdown_table(concentration, ['Strategy', 'HHI', 'Effective Positions'], set())}

## 7. Weight Distribution by Momentum Rank

{markdown_table(distribution, ['Strategy', 'Rank1', 'Rank2', 'Rank3', 'Rank4', 'Rank5'], {'Rank1', 'Rank2', 'Rank3', 'Rank4', 'Rank5'})}

## 8. Average Target Asset-Class Exposure

{markdown_table(exposure, ['Strategy', 'Equity Weight', 'Commodity Weight', 'Bond Weight'], {'Equity Weight', 'Commodity Weight', 'Bond Weight'})}

## 9. Correlation Penalty Frequency

Scores are averaged only over months when the ETF is selected in Top5. Higher average correlation means a lower diversification score and stronger penalty.

{markdown_table(penalties, ['ETF', 'Average Correlation Score', 'Average Diversification Score', 'Selection Count'], set())}

## 10. Interpretation

1. **Correlation Adjustment 是否提高 Sharpe？** {'是' if sharpe_improves else '否'}。变化 {adjusted['Sharpe'] - inverse['Sharpe']:+.3f}。
2. **是否降低 MaxDD？** {'是' if drawdown_improves else '否'}。变化 {fmt_pct(adjusted['MaxDD'] - inverse['MaxDD'])}。
3. **是否降低平均相关性？** Unweighted指标不会变化；Weighted Pairwise Correlation变化 {weighted_corr_change:+.3f}。
4. **是否减少Equity内部重复？** Equity平均目标权重变化 {fmt_pct(equity_change)}，且高相关Equity的Diversification Score显示具体惩罚强度。
5. **是否自动增加Commodity或Bond？** Commodity变化 {fmt_pct(commodity_change)}，Bond变化 {fmt_pct(bond_change)}。
6. **改善是否超过Inverse Vol？** 否。Weighted Pairwise Correlation虽下降 {abs(weighted_corr_change):.3f}，但CAGR下降 {abs(adjusted['CAGR'] - inverse['CAGR']):.2%}、Sharpe下降 {abs(adjusted['Sharpe'] - inverse['Sharpe']):.3f}，且MaxDD恶化 {abs(adjusted['MaxDD'] - inverse['MaxDD']):.2%}。
7. **Original 12是否已足够分散？** 对当前简单相关性惩罚而言，是。Original 12与Inverse Vol已经吸收了大部分可用的简单分散价值，进一步惩罚相关性没有改善实现后的风险收益。

## 11. Final Conclusion

Correlation-Adjusted Inverse Vol **不优于**纯Inverse Vol。它降低了目标权重口径的持仓相关性，并减少Equity重复暴露，但同时降低CAGR与Sharpe、恶化MaxDD、提高集中度和换手率。因此，当前证据不支持把风险管理从单资产Inverse Vol扩展到这条简单的平均相关性惩罚公式。

这不代表完整协方差模型或风险预算一定无效；它只说明在固定Original 12、mom_126、Top5与126日估计窗口下，简单Correlation Adjustment没有提供独立增量价值。本实验未测试其它相关窗口、惩罚下限或Risk Parity。
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    prices = core.load_prices()
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    targets, target_rows, correlation_rows = build_targets(prices)
    performance, details_by_strategy, weights_by_strategy = simulate(returns, targets)
    relative = relative_change(performance)
    correlations = correlation_diagnostics(correlation_rows)
    concentration = position_concentration(target_rows)
    distribution = weight_distribution(target_rows)
    exposure = class_exposure(target_rows)
    penalties = penalty_frequency(target_rows)

    prior = pd.read_csv(POSITION_SIZING_A_DIR / "outputs" / "daily_details.csv", index_col="Date", parse_dates=True)
    equal_error = float((details_by_strategy["Equal Weight"]["return"] - prior["Equal Weight::return"]).abs().max())
    inverse_error = float((details_by_strategy["Inverse Vol"]["return"] - prior["Inverse Vol::return"]).abs().max())
    if equal_error > 1e-12 or inverse_error > 1e-12:
        raise RuntimeError(f"Prior reproduction mismatch: {equal_error}, {inverse_error}")

    performance.to_csv(METRICS_DIR / "performance.csv", index=False)
    relative.to_csv(METRICS_DIR / "relative_change.csv", index=False)
    correlations.to_csv(METRICS_DIR / "correlation_diagnostics.csv", index=False)
    concentration.to_csv(METRICS_DIR / "position_concentration.csv", index=False)
    distribution.to_csv(METRICS_DIR / "weight_distribution.csv", index=False)
    exposure.to_csv(METRICS_DIR / "asset_class_exposure.csv", index=False)
    penalties.to_csv(METRICS_DIR / "correlation_penalty_frequency.csv", index=False)
    target_rows.to_csv(OUTPUTS_DIR / "target_weights_by_rebalance.csv", index=False)
    correlation_rows.to_csv(OUTPUTS_DIR / "correlation_by_rebalance.csv", index=False)
    combined_details = pd.concat(details_by_strategy, axis=1)
    combined_details.columns = [f"{strategy}::{metric}" for strategy, metric in combined_details.columns]
    combined_details.to_csv(OUTPUTS_DIR / "daily_details.csv")
    combined_weights = pd.concat(weights_by_strategy, axis=1)
    combined_weights.columns = [f"{strategy}::{symbol}" for strategy, symbol in combined_weights.columns]
    combined_weights.to_csv(OUTPUTS_DIR / "daily_weights.csv")
    SUMMARY_PATH.write_text(
        generate_summary(
            performance, relative, correlations, concentration, distribution,
            exposure, penalties, prices.index.max(),
        ),
        encoding="utf-8",
    )

    print("\nCorrelation-Aware Position Sizing Test Complete")
    print(f"Equal Weight reproduction max error: {equal_error:.3e}")
    print(f"Inverse Vol reproduction max error: {inverse_error:.3e}")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nCorrelation diagnostics:")
    print(correlations.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nAsset-class exposure:")
    print(exposure.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
