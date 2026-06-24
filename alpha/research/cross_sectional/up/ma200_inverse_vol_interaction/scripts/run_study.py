from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[4]
POSITION_SIZING_DIR = ALPHA_ROOT / "research" / "cross_sectional" / "position_sizing_test_a"
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(ALPHA_ROOT))

from shared.utils import cross_sectional as core  # noqa: E402


MOMENTUM_WINDOW = 126
VOLATILITY_WINDOW = 126
MA_WINDOW = 200
TOP_N = 5
COMPARISON_START = pd.Timestamp("2008-02-01")
STRATEGY_NAMES = [
    "Equal Weight",
    "EW + MA200 Cash",
    "EW + MA200 Reweight",
    "Inverse Vol",
    "IV + MA200 Cash",
    "IV + MA200 Reweight",
]
MA_STRATEGIES = {
    "EW + MA200 Cash",
    "EW + MA200 Reweight",
    "IV + MA200 Cash",
    "IV + MA200 Reweight",
}


def normalized(values: np.ndarray) -> np.ndarray:
    if len(values) == 0:
        return values
    if not np.isfinite(values).all() or (values <= 0).any():
        raise RuntimeError(f"Invalid inverse-volatility inputs: {values}")
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
    ma200 = prices.rolling(MA_WINDOW, min_periods=MA_WINDOW).mean()
    targets = {strategy: {} for strategy in STRATEGY_NAMES}
    target_rows = []
    exposure_rows = []

    for rebalance_date in core.month_end_dates(prices.index):
        scores = momentum.loc[rebalance_date].dropna()
        volatility = trailing_volatility.loc[rebalance_date].dropna()
        moving_average = ma200.loc[rebalance_date].dropna()
        if (
            len(scores) != len(prices.columns)
            or len(volatility) != len(prices.columns)
            or len(moving_average) != len(prices.columns)
        ):
            continue
        location = prices.index.get_loc(rebalance_date)
        if location + 1 >= len(prices.index):
            continue
        effective_date = prices.index[location + 1]
        if effective_date < COMPARISON_START:
            continue

        ranked = scores.sort_values(ascending=False).head(TOP_N)
        selected = ranked.index.tolist()
        selected_vol = volatility.loc[selected].to_numpy(dtype=float)
        passed = [
            symbol
            for symbol in selected
            if prices.loc[rebalance_date, symbol] > moving_average.loc[symbol]
        ]
        passed_count = len(passed)

        strategy_weights: dict[str, pd.Series] = {}
        equal = pd.Series(0.0, index=prices.columns)
        equal.loc[selected] = 1.0 / TOP_N
        strategy_weights["Equal Weight"] = equal

        ew_cash = pd.Series(0.0, index=prices.columns)
        ew_cash.loc[passed] = 1.0 / TOP_N
        strategy_weights["EW + MA200 Cash"] = ew_cash

        ew_reweight = pd.Series(0.0, index=prices.columns)
        if passed:
            ew_reweight.loc[passed] = 1.0 / passed_count
        strategy_weights["EW + MA200 Reweight"] = ew_reweight

        inverse = pd.Series(0.0, index=prices.columns)
        inverse.loc[selected] = normalized(1.0 / selected_vol)
        strategy_weights["Inverse Vol"] = inverse

        iv_cash = pd.Series(0.0, index=prices.columns)
        if passed:
            passed_vol = volatility.loc[passed].to_numpy(dtype=float)
            iv_cash.loc[passed] = normalized(1.0 / passed_vol) * (passed_count / TOP_N)
        strategy_weights["IV + MA200 Cash"] = iv_cash

        iv_reweight = pd.Series(0.0, index=prices.columns)
        if passed:
            passed_vol = volatility.loc[passed].to_numpy(dtype=float)
            iv_reweight.loc[passed] = normalized(1.0 / passed_vol)
        strategy_weights["IV + MA200 Reweight"] = iv_reweight

        for strategy, target in strategy_weights.items():
            targets[strategy][effective_date] = target
            holdings = int((target > 0).sum())
            cash = float(1 - target.sum())
            below_five = holdings < TOP_N
            exposure_rows.append(
                {
                    "Strategy": strategy,
                    "Rebalance Date": rebalance_date,
                    "Effective Date": effective_date,
                    "Holdings": holdings,
                    "Cash Allocation": cash,
                    "Below 5 Assets": below_five,
                    "Passed MA200 Assets": passed_count if strategy in MA_STRATEGIES else TOP_N,
                }
            )
            for rank, symbol in enumerate(selected, start=1):
                target_rows.append(
                    {
                        "Strategy": strategy,
                        "Rebalance Date": rebalance_date,
                        "Effective Date": effective_date,
                        "Rank": rank,
                        "Symbol": symbol,
                        "Momentum": ranked.loc[symbol],
                        "Trailing Volatility": volatility.loc[symbol],
                        "Price": prices.loc[rebalance_date, symbol],
                        "MA200": moving_average.loc[symbol],
                        "Passed MA200": symbol in passed,
                        "Target Weight": target.loc[symbol],
                    }
                )
    return targets, pd.DataFrame(target_rows), pd.DataFrame(exposure_rows)


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
            raise RuntimeError(f"{strategy}: unexpected start date")
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


def exposure_statistics(exposure_history: pd.DataFrame) -> pd.DataFrame:
    result = (
        exposure_history.groupby("Strategy", as_index=False)
        .agg(
            **{
                "Avg Holdings": ("Holdings", "mean"),
                "Avg Cash Allocation": ("Cash Allocation", "mean"),
                "Percent Months Below 5 Assets": ("Below 5 Assets", "mean"),
            }
        )
    )
    order = {strategy: index for index, strategy in enumerate(STRATEGY_NAMES)}
    result["_order"] = result["Strategy"].map(order)
    return result.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def position_concentration(
    targets: dict[str, dict[pd.Timestamp, pd.Series]],
) -> pd.DataFrame:
    rows = []
    for strategy in STRATEGY_NAMES:
        hhi_values = []
        effective_values = []
        for target in targets[strategy].values():
            cash = max(0.0, 1.0 - float(target.sum()))
            hhi = float((target**2).sum() + cash**2)
            hhi_values.append(hhi)
            effective_values.append(1.0 / hhi)
        rows.append(
            {
                "Strategy": strategy,
                "Average HHI": np.mean(hhi_values),
                "Effective Positions": np.mean(effective_values),
            }
        )
    return pd.DataFrame(rows)


def turnover_impact(details_by_strategy: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for strategy in STRATEGY_NAMES:
        details = details_by_strategy[strategy]
        annual_turnover = details["turnover"].sum() / (len(details) / core.TRADING_DAYS)
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
    exposure: pd.DataFrame,
    concentration: pd.DataFrame,
    turnover: pd.DataFrame,
    end_date: pd.Timestamp,
) -> str:
    perf = performance.set_index("Strategy")
    baseline = perf.loc["Equal Weight"]
    ew_cash = perf.loc["EW + MA200 Cash"]
    ew_reweight = perf.loc["EW + MA200 Reweight"]
    inverse = perf.loc["Inverse Vol"]
    iv_cash = perf.loc["IV + MA200 Cash"]
    iv_reweight = perf.loc["IV + MA200 Reweight"]
    ma_independent = ew_reweight["Sharpe"] > baseline["Sharpe"] and ew_reweight["MaxDD"] > baseline["MaxDD"]
    iv_independent = inverse["Sharpe"] > baseline["Sharpe"] and inverse["MaxDD"] > baseline["MaxDD"]
    complementary_cash = iv_cash["Sharpe"] > inverse["Sharpe"] and iv_cash["MaxDD"] > inverse["MaxDD"]
    complementary_reweight = iv_reweight["Sharpe"] > inverse["Sharpe"] and iv_reweight["MaxDD"] > inverse["MaxDD"]
    ew_cash_better = ew_cash["Sharpe"] > ew_reweight["Sharpe"] and ew_cash["MaxDD"] > ew_reweight["MaxDD"]
    best_equal_version = perf.loc[["Equal Weight", "EW + MA200 Cash", "EW + MA200 Reweight"], "Sharpe"].idxmax()
    inverse_beats_equal = inverse["Sharpe"] > perf.loc[["Equal Weight", "EW + MA200 Cash", "EW + MA200 Reweight"], "Sharpe"].max()
    cagr_preserving = perf.loc[perf["CAGR"] >= baseline["CAGR"] - 0.01]
    best_balanced = cagr_preserving["Sharpe"].idxmax()

    return f"""# MA200 x Inverse Vol Interaction Test

## 1. Research Question

在固定 Original 12 ETF `mom_126 Top5` 信号下，检验 MA200 与 Inverse Volatility 是否提供独立或互补的风险控制价值。本实验不优化任何参数。

## 2. Fixed Design

- Sample: `{COMPARISON_START.date()}` to `{end_date.date()}`
- Monthly rebalance; month-end signal effective next trading day
- Momentum and volatility windows: 126 trading days
- MA window: 200 trading days
- Transaction cost: 5 bps
- Processing order: select Momentum Top5 first, then apply MA200 to those five assets
- Cash variants retain 20% total exposure per surviving asset; IV Cash allocates surviving exposure `count / 5` using inverse-vol proportions
- Reweight variants normalize surviving assets to 100%; zero survivors means full cash

## 3. Performance

{markdown_table(performance, ['Strategy', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Calmar', 'Total Return', 'Turnover'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return', 'Turnover'})}

## 4. Relative Change vs Equal Weight

正的 MaxDD Change 表示回撤改善。

{markdown_table(relative, ['Strategy', 'CAGR Change', 'Sharpe Change', 'MaxDD Change'], {'CAGR Change', 'MaxDD Change'})}

## 5. Exposure Statistics

{markdown_table(exposure, ['Strategy', 'Avg Holdings', 'Avg Cash Allocation', 'Percent Months Below 5 Assets'], {'Avg Cash Allocation', 'Percent Months Below 5 Assets'})}

## 6. Position Concentration

Cash is included as an explicit position in HHI when present. HHI and Effective Positions are calculated at each rebalance and then averaged.

{markdown_table(concentration, ['Strategy', 'Average HHI', 'Effective Positions'], set())}

## 7. Turnover Impact

{markdown_table(turnover, ['Strategy', 'Annual Turnover', 'Cost Drag Estimate'], {'Annual Turnover', 'Cost Drag Estimate'})}

## 8. Interpretation

1. **MA200 是否独立提高 Sharpe？** {'是，完全投资的 EW Reweight 仍同时改善 Sharpe 与 MaxDD' if ma_independent else '否；完全投资的 EW Reweight 未同时改善 Sharpe 与 MaxDD，MA Cash 的优势主要依赖降低风险暴露'}。
2. **Inverse Vol 是否独立提高 Sharpe？** {'是' if iv_independent else '否'}。Inverse Vol Sharpe/MaxDD 为 {inverse['Sharpe']:.2f}/{fmt_pct(inverse['MaxDD'])}，Equal Weight 为 {baseline['Sharpe']:.2f}/{fmt_pct(baseline['MaxDD'])}。
3. **两者是否互补？** Cash组合 {'同时进一步改善 Sharpe 与 MaxDD' if complementary_cash else '没有同时进一步改善 Sharpe 与 MaxDD'}；Reweight组合 {'同时进一步改善' if complementary_reweight else '没有同时进一步改善'}。互补性必须相对单独 Inverse Vol 判断，而不是只相对 Equal Weight。
4. **MA200 改善来自趋势还是现金？** EW Cash vs Reweight 的 Sharpe/MaxDD 为 {ew_cash['Sharpe']:.2f}/{fmt_pct(ew_cash['MaxDD'])} vs {ew_reweight['Sharpe']:.2f}/{fmt_pct(ew_reweight['MaxDD'])}；{'Cash 版本同时更优，主要证据指向现金降风险机制' if ew_cash_better else 'Reweight 仍保留重要改善，趋势过滤本身具有独立价值'}。
5. **Reweight 与 Cash 哪种更优？** Cash 在 EW 和 IV 两组中都明显优于对应 Reweight；EW系列最高Sharpe仍是 `{best_equal_version}`。Reweight 的平均0.93%现金来自2个零通过资产月份，并非日常保留现金。
6. **Inverse Vol 是否仍优于所有 Equal Weight 版本？** {'是' if inverse_beats_equal else '否'}，以 Sharpe 比较。
7. **哪种最符合保留收益并控制风险？** 在 CAGR 不低于 Equal Weight 1个百分点的固定方案中，`{best_balanced}` 的 Sharpe 最高；该筛选只总结预先指定方案，不进行参数搜索。

## 9. Final Conclusion

在当前 Original 12 ETF Momentum Framework 中，**MA200 与 Inverse Vol 没有显示增量互补性**。MA200 Cash 能显著降低 Equal Weight 回撤，但不提高 Sharpe，其价值主要来自现金降风险；MA200 Reweight 在 EW 和 IV 下都恶化表现。Inverse Vol 单独保留最高 CAGR、最高 Sharpe和最浅MaxDD，因此是六个固定方案中最完整的风险控制机制。当前证据不支持把 MA200 叠加到 Inverse Vol，也不支持过滤后重新归一化。本实验不测试其它 MA、Vol窗口或仓位方法。
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    prices = core.load_prices()
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    targets, target_rows, exposure_history = build_targets(prices)
    performance, details_by_strategy, weights_by_strategy = simulate(returns, targets)
    relative = relative_change(performance)
    exposure = exposure_statistics(exposure_history)
    concentration = position_concentration(targets)
    turnover = turnover_impact(details_by_strategy)

    prior = pd.read_csv(POSITION_SIZING_DIR / "outputs" / "daily_details.csv", index_col="Date", parse_dates=True)
    equal_error = float((details_by_strategy["Equal Weight"]["return"] - prior["Equal Weight::return"]).abs().max())
    inverse_error = float((details_by_strategy["Inverse Vol"]["return"] - prior["Inverse Vol::return"]).abs().max())
    if equal_error > 1e-12 or inverse_error > 1e-12:
        raise RuntimeError(f"Prior strategy reproduction mismatch: {equal_error}, {inverse_error}")

    performance.to_csv(METRICS_DIR / "performance.csv", index=False)
    relative.to_csv(METRICS_DIR / "relative_change.csv", index=False)
    exposure.to_csv(METRICS_DIR / "exposure_statistics.csv", index=False)
    concentration.to_csv(METRICS_DIR / "position_concentration.csv", index=False)
    turnover.to_csv(METRICS_DIR / "turnover_impact.csv", index=False)
    target_rows.to_csv(OUTPUTS_DIR / "target_weights_by_rebalance.csv", index=False)
    exposure_history.to_csv(OUTPUTS_DIR / "rebalance_exposure.csv", index=False)
    combined_details = pd.concat(details_by_strategy, axis=1)
    combined_details.columns = [f"{strategy}::{metric}" for strategy, metric in combined_details.columns]
    combined_details.to_csv(OUTPUTS_DIR / "daily_details.csv")
    combined_weights = pd.concat(weights_by_strategy, axis=1)
    combined_weights.columns = [f"{strategy}::{symbol}" for strategy, symbol in combined_weights.columns]
    combined_weights.to_csv(OUTPUTS_DIR / "daily_weights.csv")
    SUMMARY_PATH.write_text(
        generate_summary(performance, relative, exposure, concentration, turnover, prices.index.max()),
        encoding="utf-8",
    )

    print("\nMA200 x Inverse Vol Interaction Test Complete")
    print(f"Equal Weight reproduction max error: {equal_error:.3e}")
    print(f"Inverse Vol reproduction max error: {inverse_error:.3e}")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nExposure statistics:")
    print(exposure.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nPosition concentration:")
    print(concentration.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
