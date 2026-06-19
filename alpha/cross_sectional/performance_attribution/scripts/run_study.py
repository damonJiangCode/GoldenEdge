from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[3]
BASELINE_DIR = ALPHA_ROOT / "cross_sectional" / "mixed_asset_momentum"
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(ALPHA_ROOT))

from shared.utils import attribution as attribution_utils  # noqa: E402
from shared.utils import cross_sectional as core  # noqa: E402


MOMENTUM_WINDOW = 126
TOP_N = 5
STRATEGY_LABEL = "mom_126_Top5"


def build_targets(
    prices: pd.DataFrame,
    excluded_symbols: set[str],
) -> tuple[dict[pd.Timestamp, pd.Series], pd.DataFrame]:
    eligible_symbols = [symbol for symbol in prices.columns if symbol not in excluded_symbols]
    if len(eligible_symbols) < TOP_N:
        raise ValueError(f"Need at least {TOP_N} eligible symbols after exclusions.")

    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    targets: dict[pd.Timestamp, pd.Series] = {}
    selection_rows = []

    for rebalance_date in core.month_end_dates(prices.index):
        scores = momentum.loc[rebalance_date, eligible_symbols].dropna()
        if len(scores) != len(eligible_symbols):
            continue
        rebalance_location = prices.index.get_loc(rebalance_date)
        if rebalance_location + 1 >= len(prices.index):
            continue

        effective_date = prices.index[rebalance_location + 1]
        ranked = scores.sort_values(ascending=False)
        selected = ranked.head(TOP_N).index.tolist()
        target = pd.Series(0.0, index=prices.columns)
        target.loc[selected] = 1.0 / TOP_N
        targets[effective_date] = target

        for symbol in selected:
            selection_rows.append(
                {
                    "rebalance_date": rebalance_date,
                    "effective_date": effective_date,
                    "symbol": symbol,
                    "rank": int(ranked.index.get_loc(symbol) + 1),
                    "momentum": ranked.loc[symbol],
                    "target_weight": target.loc[symbol],
                }
            )

    return targets, pd.DataFrame(selection_rows)


def simulate_with_attribution(
    returns: pd.DataFrame,
    targets: dict[pd.Timestamp, pd.Series],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not targets:
        raise ValueError("No valid rebalance targets.")

    active_returns = returns.loc[min(targets):]
    current_weights = pd.Series(0.0, index=returns.columns)
    portfolio_rows = []
    contribution_rate_rows = []
    weight_rows = []

    for date, asset_returns in active_returns.iterrows():
        target = targets.get(date)
        if target is not None:
            absolute_trades = (target - current_weights).abs()
            turnover = float(absolute_trades.sum())
            cost_by_asset = absolute_trades * core.TRADING_COST
            current_weights = target.copy()
        else:
            turnover = 0.0
            cost_by_asset = pd.Series(0.0, index=returns.columns)

        gross_contribution_rates = current_weights * asset_returns
        net_contribution_rates = gross_contribution_rates - cost_by_asset
        gross_return = float(gross_contribution_rates.sum())
        cost = float(cost_by_asset.sum())
        net_return = float(net_contribution_rates.sum())

        portfolio_rows.append(
            {
                "Date": date,
                "return": net_return,
                "gross_return": gross_return,
                "cost": cost,
                "turnover": turnover,
            }
        )
        contribution_rate_rows.append({"Date": date, **net_contribution_rates.to_dict()})
        weight_rows.append({"Date": date, **current_weights.to_dict()})

        denominator = 1 + gross_return
        if denominator > 0:
            current_weights = current_weights * (1 + asset_returns) / denominator
        else:
            current_weights = pd.Series(0.0, index=returns.columns)

    portfolio = pd.DataFrame(portfolio_rows).set_index("Date")
    contribution_rates = pd.DataFrame(contribution_rate_rows).set_index("Date")
    weights = pd.DataFrame(weight_rows).set_index("Date")
    return portfolio, contribution_rates, weights


def calculate_asset_contributions(
    returns: pd.DataFrame,
    portfolio: pd.DataFrame,
    contribution_rates: pd.DataFrame,
    weights: pd.DataFrame,
    selections: pd.DataFrame,
    analysis_index: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    portfolio = portfolio.reindex(analysis_index)
    contribution_rates = contribution_rates.reindex(analysis_index)
    weights = weights.reindex(analysis_index)
    asset_returns = returns.reindex(analysis_index)

    equity = (1 + portfolio["return"]).cumprod()
    equity_before = equity.shift(1, fill_value=1.0)
    pnl = contribution_rates.mul(equity_before, axis=0)
    total_portfolio_return = float(equity.iloc[-1] - 1)

    in_sample_selections = selections.loc[
        pd.to_datetime(selections["effective_date"]).between(analysis_index.min(), analysis_index.max())
    ]
    rebalance_count = in_sample_selections["effective_date"].nunique()
    selection_count = in_sample_selections.groupby("symbol").size()

    rows = []
    daily_rows = []
    for symbol in returns.columns:
        held = weights[symbol] > 1e-12
        total_contribution = float(pnl[symbol].sum())
        rows.append(
            {
                "symbol": symbol,
                "selection_count": int(selection_count.get(symbol, 0)),
                "selection_pct": selection_count.get(symbol, 0) / rebalance_count,
                "avg_weight": weights.loc[held, symbol].mean() if held.any() else 0.0,
                "avg_return_when_held": asset_returns.loc[held, symbol].mean() if held.any() else np.nan,
                "total_contribution": total_contribution,
                "contribution_pct": total_contribution / total_portfolio_return,
            }
        )
        symbol_daily = pd.DataFrame(
            {
                "Date": analysis_index,
                "symbol": symbol,
                "weight": weights[symbol].values,
                "asset_return": asset_returns[symbol].values,
                "net_return_contribution": contribution_rates[symbol].values,
                "pnl_contribution": pnl[symbol].values,
            }
        )
        daily_rows.append(symbol_daily)

    contribution = pd.DataFrame(rows).sort_values("total_contribution", ascending=False).reset_index(drop=True)
    daily_attribution = pd.concat(daily_rows, ignore_index=True).sort_values(["Date", "symbol"])

    reconciliation_error = contribution["total_contribution"].sum() - total_portfolio_return
    if abs(reconciliation_error) > 1e-10:
        raise RuntimeError(f"PnL attribution does not reconcile: {reconciliation_error}")
    return contribution, daily_attribution


def calculate_removal_sensitivity(
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    analysis_index: pd.DatetimeIndex,
    ranked_contributors: list[str],
) -> pd.DataFrame:
    rows = []
    scenarios = [("Baseline", [])]
    scenarios.extend(
        (f"RemoveTop{count}", ranked_contributors[:count])
        for count in range(1, 4)
    )

    for scenario, removed in scenarios:
        targets, _ = attribution_utils.build_targets(prices, MOMENTUM_WINDOW, TOP_N, set(removed))
        portfolio, _, _ = attribution_utils.simulate_with_attribution(returns, targets)
        aligned = portfolio.reindex(analysis_index)
        if aligned["return"].isna().any():
            raise RuntimeError(f"{scenario}: missing returns in common analysis sample")
        equity = (1 + aligned["return"]).cumprod()
        metrics = core.calculate_metrics(
            label=scenario,
            momentum_window=f"mom_{MOMENTUM_WINDOW}",
            strategy=f"Top{TOP_N}",
            returns=aligned["return"],
            equity=equity,
            turnover=aligned["turnover"],
            number_of_rebalances=len(core.monthly_returns(aligned["return"])),
        )
        rows.append(
            {
                "scenario": scenario,
                "removed_count": len(removed),
                "removed_symbols": ",".join(removed),
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

    result = pd.DataFrame(rows)
    baseline = result.iloc[0]
    result["CAGR Retention"] = result["CAGR"] / baseline["CAGR"]
    result["Sharpe Retention"] = result["Sharpe"] / baseline["Sharpe"]
    result["MaxDD Change"] = result["MaxDD"] - baseline["MaxDD"]
    return result


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


def generate_summary(
    contribution: pd.DataFrame,
    sensitivity: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> str:
    top_three = contribution.head(3)
    top_three_symbols = ", ".join(top_three["symbol"])
    top_three_share = top_three["contribution_pct"].sum()
    baseline = sensitivity.iloc[0]
    remove_three = sensitivity.loc[sensitivity["scenario"] == "RemoveTop3"].iloc[0]

    cagr_retention = remove_three["CAGR Retention"]
    sharpe_retention = remove_three["Sharpe Retention"]
    maxdd_worsening = min(0.0, remove_three["MaxDD Change"])
    if cagr_retention >= 0.70 and sharpe_retention >= 0.70 and maxdd_worsening >= -0.10:
        breadth_conclusion = (
            "移除前三大贡献资产后，策略仍保留至少 70% 的 CAGR 与 Sharpe，且 MaxDD 未恶化超过 10 个百分点。"
            "当前证据支持收益来源具有较广泛的 Cross-Asset breadth。"
        )
    elif cagr_retention < 0.50 or sharpe_retention < 0.50 or maxdd_worsening < -0.15:
        breadth_conclusion = (
            "移除前三大贡献资产后，CAGR 或 Sharpe 保留不足 50%，或 MaxDD 恶化超过 15 个百分点。"
            "策略明显依赖少数核心赢家，不能视为广泛稳定的 Cross-Asset Alpha。"
        )
    else:
        breadth_conclusion = (
            "移除前三大贡献资产后策略仍为正，但 CAGR/Sharpe 有实质下降。"
            "收益存在一定 breadth，同时也有不可忽视的赢家集中度。"
        )

    contribution_columns = [
        "symbol", "selection_count", "selection_pct", "avg_weight", "avg_return_when_held",
        "total_contribution", "contribution_pct",
    ]
    sensitivity_columns = [
        "scenario", "removed_symbols", "CAGR", "Sharpe", "MaxDD", "CAGR Retention",
        "Sharpe Retention", "MaxDD Change",
    ]
    return f"""# Mixed Asset Momentum Performance Attribution

## 1. Research Scope

- Strategy: `{STRATEGY_LABEL}`
- Universe: 12 ETF Mixed Asset Universe
- Sample: `{start_date.date()}` to `{end_date.date()}`
- Monthly rebalance, Top5 equal weight, 5 bps transaction cost
- Momentum signal: 126 trading days

本分析回答收益来自哪些资产，以及移除主要赢家后策略是否仍然成立。它是全样本归因和集中度诊断，不是独立样本外检验。

## 2. Attribution Method

- 每日资产毛贡献率：`start_of_day_weight × asset_return`
- 交易成本按各资产绝对调仓额分摊
- 每日资产 PnL：`portfolio_equity_before_return × net_asset_contribution_rate`
- 所有资产 `total_contribution` 之和精确等于组合最终 Total Return
- `avg_return_when_held` 是资产在日初权重大于零时的平均日收益

## 3. Asset Contribution

{markdown_table(contribution, contribution_columns, {"selection_pct", "avg_weight", "avg_return_when_held", "total_contribution", "contribution_pct"})}

## 4. Top Contributors

1. 前三大贡献资产：`{top_three_symbols}`。
2. 前三大资产合计贡献组合净收益的 {fmt_pct(top_three_share)}。当其他资产存在负贡献时，该比例可能超过 100%。

## 5. Removal Sensitivity

每个移除场景都会从投资 Universe 删除对应资产，然后重新计算排名、Top5 持仓、换手和交易成本。

{markdown_table(sensitivity, sensitivity_columns, {"CAGR", "MaxDD", "CAGR Retention", "Sharpe Retention", "MaxDD Change"})}

- Baseline: CAGR {fmt_pct(baseline['CAGR'])}, Sharpe {fmt_num(baseline['Sharpe'])}, MaxDD {fmt_pct(baseline['MaxDD'])}。
- Remove Top1: CAGR {fmt_pct(sensitivity.iloc[1]['CAGR'])}, Sharpe {fmt_num(sensitivity.iloc[1]['Sharpe'])}, MaxDD {fmt_pct(sensitivity.iloc[1]['MaxDD'])}。
- Remove Top2: CAGR {fmt_pct(sensitivity.iloc[2]['CAGR'])}, Sharpe {fmt_num(sensitivity.iloc[2]['Sharpe'])}, MaxDD {fmt_pct(sensitivity.iloc[2]['MaxDD'])}。
- Remove Top3: CAGR {fmt_pct(remove_three['CAGR'])}, Sharpe {fmt_num(remove_three['Sharpe'])}, MaxDD {fmt_pct(remove_three['MaxDD'])}。

## 6. Final Conclusion

{breadth_conclusion}

需要注意：贡献资产和移除对象都由同一全样本识别，因此该结果适合判断历史收益集中度，不适合直接预测未来应该排除或保留哪些资产。
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    prices = core.load_prices()
    returns = prices.pct_change(fill_method=None).fillna(0.0)

    existing_daily = pd.read_csv(BASELINE_DIR / "outputs" / "daily_returns.csv", index_col="Date", parse_dates=True)
    if STRATEGY_LABEL not in existing_daily.columns:
        raise RuntimeError(f"Missing existing strategy returns: {STRATEGY_LABEL}")
    analysis_index = existing_daily.index

    targets, selections = attribution_utils.build_targets(prices, MOMENTUM_WINDOW, TOP_N, set())
    portfolio, contribution_rates, weights = attribution_utils.simulate_with_attribution(returns, targets)
    reproduced_returns = portfolio["return"].reindex(analysis_index)
    maximum_return_error = float((reproduced_returns - existing_daily[STRATEGY_LABEL]).abs().max())
    if maximum_return_error > 1e-12:
        raise RuntimeError(f"Baseline reproduction mismatch: {maximum_return_error}")

    contribution, daily_attribution = attribution_utils.calculate_asset_contributions(
        returns,
        portfolio,
        contribution_rates,
        weights,
        selections,
        analysis_index,
    )
    ranked_contributors = contribution["symbol"].head(3).tolist()
    sensitivity = calculate_removal_sensitivity(
        prices,
        returns,
        analysis_index,
        ranked_contributors,
    )

    contribution.to_csv(METRICS_DIR / "asset_contribution.csv", index=False)
    sensitivity.to_csv(METRICS_DIR / "removal_sensitivity.csv", index=False)
    daily_attribution.to_csv(OUTPUTS_DIR / "daily_asset_attribution.csv", index=False)
    summary = generate_summary(
        contribution,
        sensitivity,
        analysis_index.min(),
        analysis_index.max(),
    )
    SUMMARY_PATH.write_text(summary, encoding="utf-8")

    print("\nMixed Asset Momentum Performance Attribution Complete")
    print(f"Study directory: {STUDY_DIR}")
    print(f"Baseline reproduction max error: {maximum_return_error:.3e}")
    print("\nAsset contribution:")
    print(contribution.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nRemoval sensitivity:")
    print(sensitivity.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
