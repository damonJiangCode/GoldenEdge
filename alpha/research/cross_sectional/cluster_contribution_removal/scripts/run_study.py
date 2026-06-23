from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[4]
DATA_ROOT = ALPHA_ROOT / "shared" / "data"
BASELINE_STUDY_DIR = ALPHA_ROOT / "research" / "cross_sectional" / "representative_category_balanced"
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(ALPHA_ROOT))

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
CATEGORY_SLOTS = {"Equity": 2, "Commodity": 2, "Bond": 1, "Currency": 0}
SCENARIOS = {
    "Baseline": [],
    "Remove Equity": ["SPY", "XLU"],
    "Remove Bond": ["IEF"],
    "Remove Agriculture": ["DBA"],
    "Remove Energy": ["DBC"],
    "Remove Precious Metals": ["GLD"],
    "Remove Palladium": ["PALL"],
    "Remove Natural Gas": ["UNG"],
    "Remove USD": ["UUP"],
}
CLUSTER_BY_SCENARIO = {
    "Remove Equity": "Equity",
    "Remove Bond": "Bond",
    "Remove Agriculture": "Agriculture",
    "Remove Energy": "Energy / Broad Commodity",
    "Remove Precious Metals": "Precious Metals",
    "Remove Palladium": "Palladium",
    "Remove Natural Gas": "Natural Gas",
    "Remove USD": "US Dollar",
}
CONTRIBUTION_GROUPS = {
    "Equity": ["SPY", "XLU"],
    "Bond": ["IEF"],
    "Agriculture": ["DBA"],
    "Energy / Broad Commodity": ["DBC"],
    "Precious Metals": ["GLD"],
    "Palladium": ["PALL"],
    "Natural Gas": ["UNG"],
    "US Dollar": ["UUP"],
}
ALL_SYMBOLS = [symbol for symbols in REPRESENTATIVE_CLASSES.values() for symbol in symbols]
SMALL_CAGR_IMPACT = 0.005
SMALL_SHARPE_IMPACT = 0.05
SMALL_MAXDD_IMPACT = 0.02


def load_prices() -> pd.DataFrame:
    frames = []
    for asset_class, symbols in REPRESENTATIVE_CLASSES.items():
        directory = DATA_ROOT / asset_class.lower()
        for symbol in symbols:
            frame = load_symbol(directory / f"{symbol}.csv")
            if frame is None:
                raise RuntimeError(f"Failed to load {symbol}")
            frames.append(frame)
    return pd.concat(frames, axis=1).sort_index().dropna(how="any")[ALL_SYMBOLS]


def build_targets(
    prices: pd.DataFrame,
) -> tuple[dict[str, dict[pd.Timestamp, pd.Series]], pd.DataFrame]:
    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    targets = {scenario: {} for scenario in SCENARIOS}
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

        for scenario, removed_symbols in SCENARIOS.items():
            removed = set(removed_symbols)
            selected = []
            for asset_class, slots in CATEGORY_SLOTS.items():
                eligible = [symbol for symbol in REPRESENTATIVE_CLASSES[asset_class] if symbol not in removed]
                if slots and eligible:
                    selected.extend(scores.loc[eligible].nlargest(min(slots, len(eligible))).index.tolist())
            target = pd.Series(0.0, index=prices.columns)
            target.loc[selected] = SLOT_WEIGHT
            targets[scenario][effective_date] = target
            for symbol in selected:
                asset_class = next(name for name, symbols in REPRESENTATIVE_CLASSES.items() if symbol in symbols)
                selection_rows.append(
                    {
                        "Scenario": scenario,
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
    details_by_scenario = {}
    weights_by_scenario = {}
    for scenario, scenario_targets in targets.items():
        details, weights = core.simulate_monthly_holdings(returns, scenario_targets)
        if details.index.min() != COMPARISON_START:
            raise RuntimeError(f"{scenario}: unexpected comparison start")
        equity = (1 + details["return"]).cumprod()
        metrics = core.calculate_metrics(
            label=scenario,
            momentum_window="mom_126",
            strategy="Representative Category Balanced",
            returns=details["return"],
            equity=equity,
            turnover=details["turnover"],
            number_of_rebalances=len(scenario_targets),
        )
        rows.append(
            {
                "Scenario": scenario,
                "CAGR": metrics["CAGR"],
                "Sharpe": metrics["Sharpe"],
                "MaxDD": metrics["MaxDD"],
                "Volatility": metrics["Volatility"],
                "Calmar": metrics["Calmar"],
                "Total Return": metrics["Total Return"],
                "Turnover": metrics["Turnover"],
            }
        )
        details_by_scenario[scenario] = details
        weights_by_scenario[scenario] = weights
    return pd.DataFrame(rows), details_by_scenario, weights_by_scenario


def relative_changes(performance: pd.DataFrame) -> pd.DataFrame:
    indexed = performance.set_index("Scenario")
    baseline = indexed.loc["Baseline"]
    result = performance.loc[performance["Scenario"] != "Baseline", ["Scenario", "CAGR", "Sharpe", "MaxDD"]].copy()
    result["CAGR Change"] = result["CAGR"] - baseline["CAGR"]
    result["Sharpe Change"] = result["Sharpe"] - baseline["Sharpe"]
    result["MaxDD Change"] = result["MaxDD"] - baseline["MaxDD"]
    result["Cluster"] = result["Scenario"].map(CLUSTER_BY_SCENARIO)
    result = result[["Scenario", "Cluster", "CAGR Change", "Sharpe Change", "MaxDD Change"]]
    numeric = ["CAGR Change", "Sharpe Change", "MaxDD Change"]
    result[numeric] = result[numeric].mask(result[numeric].abs() < 1e-12, 0.0)
    return result


def importance_rankings(relative: pd.DataFrame) -> pd.DataFrame:
    impact = relative.copy()
    impact["CAGR Impact"] = -impact["CAGR Change"]
    impact["Sharpe Impact"] = -impact["Sharpe Change"]
    impact["Risk Impact"] = -impact["MaxDD Change"]
    rows = []
    for metric in ["CAGR Impact", "Sharpe Impact", "Risk Impact"]:
        ordered = impact.sort_values([metric, "Cluster"], ascending=[False, True]).reset_index(drop=True)
        for rank, row in ordered.iterrows():
            rows.append(
                {
                    "Dimension": metric,
                    "Rank": rank + 1,
                    "Cluster": row["Cluster"],
                    "Scenario": row["Scenario"],
                    "Impact": row[metric],
                }
            )
    result = pd.DataFrame(rows)
    result["Impact"] = result["Impact"].mask(result["Impact"].abs() < 1e-12, 0.0)
    return result


def scenario_exposure(weights_by_scenario: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for scenario, weights in weights_by_scenario.items():
        row = {"Scenario": scenario}
        for asset_class, symbols in REPRESENTATIVE_CLASSES.items():
            row[asset_class] = weights[symbols].sum(axis=1).mean()
        row["Cash"] = (1 - weights.sum(axis=1)).mean()
        rows.append(row)
    result = pd.DataFrame(rows)
    numeric = ["Equity", "Commodity", "Bond", "Currency", "Cash"]
    result[numeric] = result[numeric].mask(result[numeric].abs() < 1e-12, 0.0)
    return result


def baseline_contribution(
    returns: pd.DataFrame,
    details: pd.DataFrame,
    weights: pd.DataFrame,
) -> pd.DataFrame:
    strategy_returns = returns.loc[details.index]
    starting_wealth = (1 + details["return"]).cumprod().shift(1, fill_value=1.0)
    contributions = {}
    for cluster, symbols in CONTRIBUTION_GROUPS.items():
        daily_return = (weights[symbols] * strategy_returns[symbols]).sum(axis=1)
        contributions[cluster] = float((starting_wealth * daily_return).sum())
    total = sum(contributions.values())
    return pd.DataFrame(
        [
            {
                "Cluster": cluster,
                "Total Gross PnL Contribution": contribution,
                "Contribution Percent": contribution / total,
            }
            for cluster, contribution in contributions.items()
        ]
    ).sort_values("Total Gross PnL Contribution", ascending=False).reset_index(drop=True)


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


def ranking_table(rankings: pd.DataFrame, dimension: str) -> str:
    selected = rankings.loc[rankings["Dimension"] == dimension]
    return markdown_table(selected, ["Rank", "Cluster", "Impact"], {"Impact"} if dimension != "Sharpe Impact" else set())


def generate_summary(
    performance: pd.DataFrame,
    relative: pd.DataFrame,
    rankings: pd.DataFrame,
    exposure: pd.DataFrame,
    contribution: pd.DataFrame,
    end_date: pd.Timestamp,
) -> str:
    cagr_rank = rankings.loc[rankings["Dimension"] == "CAGR Impact"].sort_values("Rank")
    sharpe_rank = rankings.loc[rankings["Dimension"] == "Sharpe Impact"].sort_values("Rank")
    risk_rank = rankings.loc[rankings["Dimension"] == "Risk Impact"].sort_values("Rank")
    return_engine = cagr_rank.iloc[0]["Cluster"]
    sharpe_engine = sharpe_rank.iloc[0]["Cluster"]
    risk_buffer = risk_rank.iloc[0]["Cluster"]
    small = relative.loc[
        (relative["CAGR Change"].abs() <= SMALL_CAGR_IMPACT)
        & (relative["Sharpe Change"].abs() <= SMALL_SHARPE_IMPACT)
        & (relative["MaxDD Change"].abs() <= SMALL_MAXDD_IMPACT),
        "Cluster",
    ].tolist()
    small_text = ", ".join(small) if small else "None"
    baseline = performance.set_index("Scenario").loc["Baseline"]

    return f"""# Cluster Contribution & Removal Test

## 1. Research Question

识别 Representative Category Balanced 框架中各风险簇的直接收益贡献、删除敏感度和组合职责。本实验不优化任何参数。

## 2. Fixed Baseline and Removal Rules

- Sample: `{COMPARISON_START.date()}` to `{end_date.date()}`
- Monthly rebalance; month-end signal effective next trading day
- Momentum: 126 trading days; transaction cost: 5 bps
- Category slots remain Equity Top2, Commodity Top2, Bond Top1 at 20% each
- A removed cluster is excluded before ranking; unavailable category slots remain cash
- Baseline CAGR/Sharpe/MaxDD: {fmt_pct(baseline['CAGR'])} / {baseline['Sharpe']:.2f} / {fmt_pct(baseline['MaxDD'])}
- Small-impact diagnostic: absolute CAGR <= 0.5 percentage points, Sharpe <= 0.05, MaxDD <= 2 percentage points

## 3. Performance

{markdown_table(performance, ['Scenario', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Calmar', 'Total Return', 'Turnover'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return', 'Turnover'})}

## 4. Relative Change vs Baseline

正的 MaxDD Change 表示回撤改善。

{markdown_table(relative, ['Scenario', 'Cluster', 'CAGR Change', 'Sharpe Change', 'MaxDD Change'], {'CAGR Change', 'MaxDD Change'})}

## 5. Baseline Direct Gross PnL Contribution

Contribution 使用期初组合财富加权的毛 PnL，在风险簇之间归一化；交易成本不归属于单个簇。它与删除后替代效应不同。

{markdown_table(contribution, ['Cluster', 'Total Gross PnL Contribution', 'Contribution Percent'], {'Contribution Percent'})}

## 6. Contribution Importance Rankings

Positive impact means removal damaged the corresponding metric. Negative impact means removal improved it.

### CAGR Impact

{ranking_table(rankings, 'CAGR Impact')}

### Sharpe Impact

{ranking_table(rankings, 'Sharpe Impact')}

### Risk Impact

Risk Impact is positive when removal makes MaxDD more negative.

{ranking_table(rankings, 'Risk Impact')}

## 7. Scenario Exposure and Cash

{markdown_table(exposure, ['Scenario', 'Equity', 'Commodity', 'Bond', 'Currency', 'Cash'], {'Equity', 'Commodity', 'Bond', 'Currency', 'Cash'})}

## 8. Interpretation

1. **主要收益引擎？** 按删除后 CAGR 下降，`{return_engine}` 排名第一。
2. **对 Sharpe 最重要？** `{sharpe_engine}` 删除后造成最大 Sharpe 损失。
3. **主要风险缓冲器？** `{risk_buffer}` 删除后造成最大 MaxDD 恶化。
4. **删除后影响很小？** 按预设三项 small-impact 标准：{small_text}。其中 US Dollar 在当前规则中从未配置，影响严格为零；Agriculture 和 Energy 可被其它 Commodity 代表替代。
5. **可简化的 Satellite Clusters？** Natural Gas 是最强的简化候选：Baseline 直接贡献为负，删除后 CAGR 和 Sharpe 均明显上升。该结论仍需样本外验证，不能据此直接永久删除。US Dollar 在当前无 Currency 席位的规则下可从交易 Universe 移除但不改变策略。Bond 虽在 small-impact 范围内，却是排名第一的回撤缓冲器，不应按小收益影响机械删除。
6. **框架依赖哪些风险来源？** Equity、Precious Metals 和 Palladium 承担主要收益；Equity 与 Precious Metals 对 Sharpe 最重要；Bond 提供幅度有限但方向明确的回撤保护。Equity/Bond 整类删除还会产生 40%/20% 现金，因此它们的影响同时包含资产缺失和降风险暴露；Commodity 单簇删除主要衡量同类别替代能力。

## 9. Final Conclusion

当前框架中不可替代性应按三个维度分别判断：`{return_engine}` 是主要 CAGR 来源，`{sharpe_engine}` 对风险调整表现最重要，`{risk_buffer}` 是主要回撤缓冲器。Precious Metals 和 Palladium 也是重要收益来源；Natural Gas 是样本内主要拖累，US Dollar 在当前规则下没有组合职责。删除测试是条件敏感度分析，不应把样本内负面贡献机械解释成永久移除建议。
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    prices = load_prices()
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    targets, selections = build_targets(prices)
    performance, details_by_scenario, weights_by_scenario = simulate(returns, targets)
    relative = relative_changes(performance)
    rankings = importance_rankings(relative)
    exposure = scenario_exposure(weights_by_scenario)
    contribution = baseline_contribution(
        returns, details_by_scenario["Baseline"], weights_by_scenario["Baseline"]
    )

    prior = pd.read_csv(BASELINE_STUDY_DIR / "outputs" / "daily_details.csv", index_col="Date", parse_dates=True)
    baseline_error = float((details_by_scenario["Baseline"]["return"] - prior["Representative Category Balanced::return"]).abs().max())
    if baseline_error > 1e-12:
        raise RuntimeError(f"Baseline reproduction mismatch: {baseline_error}")

    performance.to_csv(METRICS_DIR / "performance.csv", index=False)
    relative.to_csv(METRICS_DIR / "relative_change.csv", index=False)
    rankings.to_csv(METRICS_DIR / "importance_rankings.csv", index=False)
    contribution.to_csv(METRICS_DIR / "baseline_cluster_contribution.csv", index=False)
    exposure.to_csv(METRICS_DIR / "scenario_exposure.csv", index=False)
    selections.to_csv(OUTPUTS_DIR / "selections.csv", index=False)
    combined_details = pd.concat(details_by_scenario, axis=1)
    combined_details.columns = [f"{scenario}::{metric}" for scenario, metric in combined_details.columns]
    combined_details.to_csv(OUTPUTS_DIR / "daily_details.csv")
    combined_weights = pd.concat(weights_by_scenario, axis=1)
    combined_weights.columns = [f"{scenario}::{symbol}" for scenario, symbol in combined_weights.columns]
    combined_weights.to_csv(OUTPUTS_DIR / "daily_weights.csv")
    SUMMARY_PATH.write_text(
        generate_summary(performance, relative, rankings, exposure, contribution, prices.index.max()),
        encoding="utf-8",
    )

    print("\nCluster Contribution & Removal Test Complete")
    print(f"Baseline reproduction max error: {baseline_error:.3e}")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nRelative changes:")
    print(relative.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nImportance rankings:")
    print(rankings.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nBaseline contribution:")
    print(contribution.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
