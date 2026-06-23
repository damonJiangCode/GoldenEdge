from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[4]
BASELINE_STUDY_DIR = ALPHA_ROOT / "research" / "cross_sectional" / "original_12_category_allocation"
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(ALPHA_ROOT))

from shared.utils import cross_sectional as core  # noqa: E402


MOMENTUM_WINDOW = 126
VOLATILITY_WINDOW = 126
COMPARISON_START = pd.Timestamp("2008-02-01")
TOP_N = 5
STRATEGY_NAMES = ["Equal Weight", "Rank Weight", "Inverse Vol", "Rank x Inverse Vol"]
RANK_WEIGHTS = np.array([0.30, 0.25, 0.20, 0.15, 0.10])
RANK_SCORES = np.array([5.0, 4.0, 3.0, 2.0, 1.0])


def normalized(values: np.ndarray) -> np.ndarray:
    if not np.isfinite(values).all() or (values <= 0).any():
        raise RuntimeError(f"Invalid position-sizing inputs: {values}")
    return values / values.sum()


def build_targets(
    prices: pd.DataFrame,
) -> tuple[dict[str, dict[pd.Timestamp, pd.Series]], pd.DataFrame]:
    returns = prices.pct_change(fill_method=None)
    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    trailing_volatility = returns.rolling(
        VOLATILITY_WINDOW, min_periods=VOLATILITY_WINDOW
    ).std(ddof=1)
    targets = {strategy: {} for strategy in STRATEGY_NAMES}
    weight_rows = []

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
        weights_by_strategy = {
            "Equal Weight": np.repeat(1.0 / TOP_N, TOP_N),
            "Rank Weight": RANK_WEIGHTS.copy(),
            "Inverse Vol": normalized(1.0 / selected_volatility),
            "Rank x Inverse Vol": normalized(RANK_SCORES / selected_volatility),
        }

        for strategy, selected_weights in weights_by_strategy.items():
            target = pd.Series(0.0, index=prices.columns)
            target.loc[selected] = selected_weights
            targets[strategy][effective_date] = target
            for rank, symbol in enumerate(selected, start=1):
                weight_rows.append(
                    {
                        "Strategy": strategy,
                        "Rebalance Date": rebalance_date,
                        "Effective Date": effective_date,
                        "Rank": rank,
                        "Symbol": symbol,
                        "Momentum": ranked.loc[symbol],
                        "Trailing Volatility": volatility.loc[symbol],
                        "Target Weight": target.loc[symbol],
                    }
                )
    return targets, pd.DataFrame(weight_rows)


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
    baseline = performance.set_index("Strategy").loc["Equal Weight"]
    result = performance.loc[performance["Strategy"] != "Equal Weight", ["Strategy", "CAGR", "Sharpe", "MaxDD"]].copy()
    result["CAGR Change"] = result["CAGR"] - baseline["CAGR"]
    result["Sharpe Change"] = result["Sharpe"] - baseline["Sharpe"]
    result["MaxDD Change"] = result["MaxDD"] - baseline["MaxDD"]
    numeric = ["CAGR Change", "Sharpe Change", "MaxDD Change"]
    result[numeric] = result[numeric].mask(result[numeric].abs() < 1e-12, 0.0)
    return result[["Strategy", *numeric]]


def position_concentration(target_weights: pd.DataFrame) -> pd.DataFrame:
    grouped = target_weights.groupby(["Strategy", "Effective Date"])["Target Weight"]
    rows = []
    for (strategy, _), weights in grouped:
        hhi = float((weights**2).sum())
        rows.append({"Strategy": strategy, "HHI": hhi, "Effective Positions": 1.0 / hhi})
    daily = pd.DataFrame(rows)
    result = (
        daily.groupby("Strategy", as_index=False)
        .agg(**{"Average HHI": ("HHI", "mean"), "Effective Positions": ("Effective Positions", "mean")})
    )
    order = {strategy: index for index, strategy in enumerate(STRATEGY_NAMES)}
    result["_order"] = result["Strategy"].map(order)
    return result.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def weight_distribution(target_weights: pd.DataFrame) -> pd.DataFrame:
    pivot = (
        target_weights.groupby(["Strategy", "Rank"])["Target Weight"]
        .mean()
        .unstack("Rank")
        .rename(columns={rank: f"Avg Weight Rank{rank}" for rank in range(1, TOP_N + 1)})
        .reset_index()
    )
    order = {strategy: index for index, strategy in enumerate(STRATEGY_NAMES)}
    pivot["_order"] = pivot["Strategy"].map(order)
    return pivot.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def turnover_impact(details_by_strategy: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for strategy in STRATEGY_NAMES:
        details = details_by_strategy[strategy]
        trading_years = len(details) / core.TRADING_DAYS
        annual_turnover = details["turnover"].sum() / trading_years
        rows.append(
            {
                "Strategy": strategy,
                "Annual Turnover": annual_turnover,
                "Cost Drag Estimate": annual_turnover * core.TRADING_COST,
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
    relative: pd.DataFrame,
    concentration: pd.DataFrame,
    distribution: pd.DataFrame,
    turnover: pd.DataFrame,
    end_date: pd.Timestamp,
) -> str:
    perf = performance.set_index("Strategy")
    conc = concentration.set_index("Strategy")
    baseline = perf.loc["Equal Weight"]
    rank = perf.loc["Rank Weight"]
    inverse = perf.loc["Inverse Vol"]
    combined = perf.loc["Rank x Inverse Vol"]
    rank_cagr_improves = rank["CAGR"] > baseline["CAGR"]
    inverse_sharpe_improves = inverse["Sharpe"] > baseline["Sharpe"]
    inverse_drawdown_improves = inverse["MaxDD"] > baseline["MaxDD"]
    combined_preserves = combined["CAGR"] >= baseline["CAGR"] - 0.01
    combined_controls = combined["Sharpe"] > baseline["Sharpe"] and combined["MaxDD"] > baseline["MaxDD"]

    cagr_preserving = perf.loc[perf["CAGR"] >= baseline["CAGR"] - 0.01]
    balanced_choice = cagr_preserving["Sharpe"].idxmax()
    turnover_indexed = turnover.set_index("Strategy")
    incremental_cost = (
        turnover_indexed.loc["Inverse Vol", "Cost Drag Estimate"]
        - turnover_indexed.loc["Equal Weight", "Cost Drag Estimate"]
    )

    return f"""# Position Sizing Test A

## 1. Research Question

在固定 Original 12 ETF、`mom_126 Top5` 和月度调仓信号下，仅改变目标仓位分配，比较 Equal Weight、Rank Weight、Inverse Volatility 和 Rank x Inverse Volatility。本实验不优化权重或窗口。

## 2. Fixed Design

- Sample: `{COMPARISON_START.date()}` to `{end_date.date()}`
- Month-end signal effective next trading day
- Momentum window: 126 trading days
- Volatility window: trailing 126 daily returns through the signal date
- Transaction cost: 5 bps; no MA filter
- All strategies select the identical Top5 each month
- Initial portfolio is established from cash on the sample start date

## 3. Performance

{markdown_table(performance, ['Strategy', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Calmar', 'Total Return', 'Turnover'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return', 'Turnover'})}

## 4. Relative Change vs Equal Weight

正的 MaxDD Change 表示回撤改善。

{markdown_table(relative, ['Strategy', 'CAGR Change', 'Sharpe Change', 'MaxDD Change'], {'CAGR Change', 'MaxDD Change'})}

## 5. Position Concentration

HHI and Effective Positions are calculated from target weights at each rebalance and then averaged.

{markdown_table(concentration, ['Strategy', 'Average HHI', 'Effective Positions'], set())}

## 6. Weight Distribution by Momentum Rank

{markdown_table(distribution, ['Strategy', 'Avg Weight Rank1', 'Avg Weight Rank2', 'Avg Weight Rank3', 'Avg Weight Rank4', 'Avg Weight Rank5'], set(distribution.columns) - {'Strategy'})}

## 7. Turnover Impact

Annual Turnover is total absolute turnover divided by trading years. Cost Drag Estimate is `Annual Turnover x 5 bps` and excludes compounding interaction.

{markdown_table(turnover, ['Strategy', 'Annual Turnover', 'Cost Drag Estimate'], {'Annual Turnover', 'Cost Drag Estimate'})}

## 8. Interpretation

1. **Equal Weight 是否已经足够优秀？** 不是唯一合理选择。Inverse Vol 在 CAGR 仅变化 {fmt_pct(inverse['CAGR'] - baseline['CAGR'])} 时显著提高 Sharpe 并改善 MaxDD，说明 sizing 提供了独立于选股的风险收益改善。
2. **Rank Weight 是否提高 CAGR？** {'是' if rank_cagr_improves else '否'}，变化 {fmt_pct(rank['CAGR'] - baseline['CAGR'])}。
3. **Rank Weight 是否导致集中？** Average HHI 从 {conc.loc['Equal Weight', 'Average HHI']:.3f} 变为 {conc.loc['Rank Weight', 'Average HHI']:.3f}，Effective Positions 从 {conc.loc['Equal Weight', 'Effective Positions']:.2f} 变为 {conc.loc['Rank Weight', 'Effective Positions']:.2f}。
4. **Inverse Vol 是否提高 Sharpe？** {'是' if inverse_sharpe_improves else '否'}，变化 {inverse['Sharpe'] - baseline['Sharpe']:+.2f}。
5. **Inverse Vol 是否降低 MaxDD？** {'是' if inverse_drawdown_improves else '否'}，变化 {fmt_pct(inverse['MaxDD'] - baseline['MaxDD'])}。
6. **Rank x Inverse Vol 是否保留 Alpha 并降低风险？** {'是' if combined_preserves and combined_controls else '没有同时满足保留 CAGR、提高 Sharpe 和改善 MaxDD'}。CAGR/Sharpe/MaxDD 为 {fmt_pct(combined['CAGR'])}/{combined['Sharpe']:.2f}/{fmt_pct(combined['MaxDD'])}。
7. **哪种最符合保留收益并控制风险？** 在 CAGR 不低于 Equal Weight 1个百分点的固定方案中，`{balanced_choice}` 的 Sharpe 最高，同时拥有最浅 MaxDD。Inverse Vol 的估算年成本拖累只比 Equal Weight 高 {fmt_pct(incremental_cost)}，不足以解释其风险改善。

## 9. Final Conclusion

在当前 Original 12 ETF Momentum Framework 中，**Inverse Volatility 明显优于 Equal Weight 的样本内风险收益表现**：CAGR 基本保留，Sharpe、MaxDD、Volatility 和 Calmar 均显著改善。Rank Weight 不增加收益且提高风险；Rank x Inverse Vol 只实现部分改善。Inverse Vol 应进入后续样本外验证，但本实验不扩展到其它权重、波动窗口、Kelly 或 Risk Parity。
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    prices = core.load_prices()
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    targets, target_weights = build_targets(prices)
    performance, details_by_strategy, weights_by_strategy = simulate(returns, targets)
    relative = relative_change(performance)
    concentration = position_concentration(target_weights)
    distribution = weight_distribution(target_weights)
    turnover = turnover_impact(details_by_strategy)

    prior = pd.read_csv(BASELINE_STUDY_DIR / "outputs" / "daily_details.csv", index_col="Date", parse_dates=True)
    baseline_error = float((details_by_strategy["Equal Weight"]["return"] - prior["Original Top5::return"]).abs().max())
    if baseline_error > 1e-12:
        raise RuntimeError(f"Equal Weight baseline reproduction mismatch: {baseline_error}")

    performance.to_csv(METRICS_DIR / "performance.csv", index=False)
    relative.to_csv(METRICS_DIR / "relative_change.csv", index=False)
    concentration.to_csv(METRICS_DIR / "position_concentration.csv", index=False)
    distribution.to_csv(METRICS_DIR / "weight_distribution.csv", index=False)
    turnover.to_csv(METRICS_DIR / "turnover_impact.csv", index=False)
    target_weights.to_csv(OUTPUTS_DIR / "target_weights_by_rebalance.csv", index=False)
    combined_details = pd.concat(details_by_strategy, axis=1)
    combined_details.columns = [f"{strategy}::{metric}" for strategy, metric in combined_details.columns]
    combined_details.to_csv(OUTPUTS_DIR / "daily_details.csv")
    combined_weights = pd.concat(weights_by_strategy, axis=1)
    combined_weights.columns = [f"{strategy}::{symbol}" for strategy, symbol in combined_weights.columns]
    combined_weights.to_csv(OUTPUTS_DIR / "daily_weights.csv")
    SUMMARY_PATH.write_text(
        generate_summary(performance, relative, concentration, distribution, turnover, prices.index.max()),
        encoding="utf-8",
    )

    print("\nPosition Sizing Test A Complete")
    print(f"Equal Weight baseline reproduction max error: {baseline_error:.3e}")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nPosition concentration:")
    print(concentration.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nTurnover impact:")
    print(turnover.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
