from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


STUDY_DIR = Path(__file__).resolve().parent
RESULTS_DIR = STUDY_DIR / "results"
OUTPUT_DIR = RESULTS_DIR / "attribution" / "asset_class_removal"
sys.path.insert(0, str(STUDY_DIR))

import run_cross_sectional_momentum as core  # noqa: E402
import run_performance_attribution as attribution  # noqa: E402


ASSET_CLASSES = {
    "Equity": ["SPY", "QQQ", "IWM", "EFA"],
    "Commodity": ["GLD", "SLV", "USO", "DBA"],
    "Bond": ["TLT", "IEF", "SHY", "LQD"],
}

SCENARIOS = [
    {
        "scenario": "Baseline",
        "removed_class": "None",
        "removed_symbols": [],
        "remaining_classes": "Equity + Commodity + Bond",
        "equivalent_portfolio": "Baseline",
    },
    {
        "scenario": "Remove Equity",
        "removed_class": "Equity",
        "removed_symbols": ASSET_CLASSES["Equity"],
        "remaining_classes": "Commodity + Bond",
        "equivalent_portfolio": "Commodity + Bond",
    },
    {
        "scenario": "Remove Commodity",
        "removed_class": "Commodity",
        "removed_symbols": ASSET_CLASSES["Commodity"],
        "remaining_classes": "Equity + Bond",
        "equivalent_portfolio": "Equity + Bond",
    },
    {
        "scenario": "Remove Bond",
        "removed_class": "Bond",
        "removed_symbols": ASSET_CLASSES["Bond"],
        "remaining_classes": "Equity + Commodity",
        "equivalent_portfolio": "Equity + Commodity",
    },
]


def run_scenarios(
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    analysis_index: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    metric_rows = []
    daily_returns = {}

    for specification in SCENARIOS:
        targets, _ = attribution.build_targets(
            prices,
            set(specification["removed_symbols"]),
        )
        portfolio, _, _ = attribution.simulate_with_attribution(returns, targets)
        aligned = portfolio.reindex(analysis_index)
        if aligned["return"].isna().any():
            raise RuntimeError(f"{specification['scenario']}: incomplete common sample")

        equity = (1 + aligned["return"]).cumprod()
        metrics = core.calculate_metrics(
            label=specification["scenario"],
            momentum_window="mom_126",
            strategy="Top5",
            returns=aligned["return"],
            equity=equity,
            turnover=aligned["turnover"],
            number_of_rebalances=len(core.monthly_returns(aligned["return"])),
        )
        metric_rows.append(
            {
                "scenario": specification["scenario"],
                "removed_class": specification["removed_class"],
                "removed_symbols": ",".join(specification["removed_symbols"]),
                "remaining_classes": specification["remaining_classes"],
                "equivalent_portfolio": specification["equivalent_portfolio"],
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
        daily_returns[specification["scenario"]] = aligned["return"]

    result = pd.DataFrame(metric_rows)
    baseline = result.iloc[0]
    result["CAGR Retention"] = result["CAGR"] / baseline["CAGR"]
    result["Sharpe Retention"] = result["Sharpe"] / baseline["Sharpe"]
    result["MaxDD Change"] = result["MaxDD"] - baseline["MaxDD"]
    result["Volatility Change"] = result["Volatility"] - baseline["Volatility"]
    return result, pd.DataFrame(daily_returns, index=analysis_index)


def aggregate_class_contribution(asset_contribution: pd.DataFrame) -> pd.DataFrame:
    symbol_to_class = {
        symbol: asset_class
        for asset_class, symbols in ASSET_CLASSES.items()
        for symbol in symbols
    }
    contribution = asset_contribution.copy()
    contribution["asset_class"] = contribution["symbol"].map(symbol_to_class)
    if contribution["asset_class"].isna().any():
        missing = contribution.loc[contribution["asset_class"].isna(), "symbol"].tolist()
        raise RuntimeError(f"Unmapped symbols in attribution: {missing}")

    grouped = (
        contribution.groupby("asset_class")
        .agg(
            asset_count=("symbol", "size"),
            selection_count=("selection_count", "sum"),
            total_contribution=("total_contribution", "sum"),
            contribution_pct=("contribution_pct", "sum"),
        )
        .reset_index()
        .sort_values("total_contribution", ascending=False)
        .reset_index(drop=True)
    )
    grouped["selection_slot_pct"] = grouped["selection_count"] / grouped["selection_count"].sum()
    return grouped[
        [
            "asset_class",
            "asset_count",
            "selection_count",
            "selection_slot_pct",
            "total_contribution",
            "contribution_pct",
        ]
    ]


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
            elif isinstance(value, float):
                cells.append(fmt_num(value))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def generate_summary(
    class_contribution: pd.DataFrame,
    scenarios: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> str:
    baseline = scenarios.iloc[0]
    removals = scenarios.iloc[1:].set_index("removed_class")
    contribution = class_contribution.set_index("asset_class")

    largest_contributor = class_contribution.iloc[0]["asset_class"]
    largest_cagr_loss_class = (baseline["CAGR"] - removals["CAGR"]).idxmax()
    largest_sharpe_loss_class = (baseline["Sharpe"] - removals["Sharpe"]).idxmax()
    worst_drawdown_impact_class = removals["MaxDD Change"].idxmin()

    equity = removals.loc["Equity"]
    commodity = removals.loc["Commodity"]
    bond = removals.loc["Bond"]

    evidence_rows = pd.DataFrame(
        [
            {
                "evidence_level": "Strong Evidence",
                "finding": "Equity is the primary return engine",
                "basis": (
                    f"Equity contributes {fmt_pct(contribution.loc['Equity', 'contribution_pct'])} of PnL; "
                    f"removal cuts CAGR to {fmt_pct(equity['CAGR'])} and Sharpe to {equity['Sharpe']:.2f}."
                ),
            },
            {
                "evidence_level": "Strong Evidence",
                "finding": "Bond is the primary risk diversifier",
                "basis": (
                    f"Bond contributes only {fmt_pct(contribution.loc['Bond', 'contribution_pct'])} of PnL, but removal "
                    f"worsens MaxDD by {fmt_pct(abs(bond['MaxDD Change']))} and raises volatility by "
                    f"{fmt_pct(bond['Volatility Change'])}."
                ),
            },
            {
                "evidence_level": "Moderate Evidence",
                "finding": "Commodity is a return enhancer, not an essential Sharpe source",
                "basis": (
                    f"Commodity contributes {fmt_pct(contribution.loc['Commodity', 'contribution_pct'])} of PnL, yet "
                    f"removal retains {fmt_pct(commodity['Sharpe Retention'])} of Sharpe and improves MaxDD."
                ),
            },
            {
                "evidence_level": "Moderate Evidence",
                "finding": "Asset rotation across classes adds value",
                "basis": "Baseline has higher CAGR and Sharpe than every two-class universe, but class roles are asymmetric.",
            },
            {
                "evidence_level": "Weak Evidence",
                "finding": "Commodity is the dominant standalone Alpha source",
                "basis": "Its historical PnL contribution is high, but removing it leaves 97%+ of baseline Sharpe.",
            },
        ]
    )

    scenario_columns = [
        "scenario",
        "remaining_classes",
        "CAGR",
        "Sharpe",
        "MaxDD",
        "Volatility",
        "Calmar",
        "Total Return",
        "Turnover",
        "CAGR Retention",
        "Sharpe Retention",
        "MaxDD Change",
    ]
    contribution_columns = [
        "asset_class",
        "asset_count",
        "selection_count",
        "selection_slot_pct",
        "total_contribution",
        "contribution_pct",
    ]

    return f"""# Asset Class Removal Test

## 1. Research Goal

识别 12 ETF Mixed Asset `mom_126 Top5` 的收益与风险优势究竟来自 Equity、Commodity、Bond，还是来自跨类别轮动本身。

- Sample: `{start_date.date()}` to `{end_date.date()}`
- Monthly rebalance, Top5 equal weight
- Momentum window: 126 trading days
- Transaction cost: 5 bps
- 不搜索任何新参数

## 2. Baseline And Removal Scenarios

{markdown_table(scenarios, scenario_columns, {"CAGR", "MaxDD", "Volatility", "Total Return", "Turnover", "CAGR Retention", "Sharpe Retention", "MaxDD Change"})}

`Remove Equity` 等价于 `Commodity + Bond`；`Remove Commodity` 等价于 `Equity + Bond`；`Remove Bond` 等价于 `Equity + Commodity`。它们是同一组 Universe，不作为重复证据计算。

## 3. Historical PnL By Asset Class

{markdown_table(class_contribution, contribution_columns, {"selection_slot_pct", "total_contribution", "contribution_pct"})}

PnL contribution 是 baseline 持仓的历史会计归因；removal test 则会重新排名并允许剩余资产替代被删除资产，因此两者回答不同问题。

## 4. Interpretation

1. 历史 PnL 贡献最大的类别：`{largest_contributor}`。
2. 删除后 CAGR 损失最大的类别：`{largest_cagr_loss_class}`；Sharpe 损失最大的类别：`{largest_sharpe_loss_class}`。
3. 更像 Alpha/return 来源：`Equity` 最强，`Commodity` 次之。
4. 更像风险分散器：`{worst_drawdown_impact_class}`。删除 Bond 后 MaxDD 从 {fmt_pct(baseline['MaxDD'])} 恶化至 {fmt_pct(bond['MaxDD'])}。
5. Mixed Asset 优势主要来自：Equity Trend 提供核心收益、Commodity Trend 增强收益、Bond Diversification 压低波动与回撤，并由跨类别排名实现 Asset Rotation。

## 5. Evidence Levels

{markdown_table(evidence_rows, ["evidence_level", "finding", "basis"], set())}

## 6. Final Answer

当前 Mixed Asset Momentum 的优势不是某一个资产类别单独产生的。

- **Strong Evidence:** Equity 是主要收益引擎；Bond 是主要风险分散器。
- **Moderate Evidence:** Commodity 提供重要历史收益贡献，跨类别轮动使完整 Universe 的 CAGR/Sharpe 高于所有双类别组合。
- **Weak Evidence:** Commodity 是不可替代的风险调整 Alpha 来源。删除 Commodity 后 Sharpe 几乎完全保留，且 MaxDD 改善。

最准确的结构性解释是：`Equity Trend + Commodity Return Enhancement + Bond Diversification + Cross-Class Rotation`。其中 Equity 和 Bond 对完整策略最不可替代，Commodity 的作用更偏向提高收益，而不是提高 Sharpe。

## 7. Limitations

- 这是全样本 sensitivity analysis，不是 out-of-sample 因果证明。
- 删除某一类别后仍维持 Top5，会提高剩余类别内的持仓密度；结果包含替代效应。
- 资产类别贡献与移除影响不是线性可加的，不能把 retention 简单解释为独立因果份额。
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    prices = core.load_prices()
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    existing_daily = pd.read_csv(RESULTS_DIR / "daily_returns.csv", index_col="Date", parse_dates=True)
    analysis_index = existing_daily.index

    scenarios, scenario_daily_returns = run_scenarios(prices, returns, analysis_index)
    baseline_error = float(
        (
            scenario_daily_returns["Baseline"]
            - existing_daily[attribution.STRATEGY_LABEL]
        ).abs().max()
    )
    if baseline_error > 1e-12:
        raise RuntimeError(f"Baseline reproduction mismatch: {baseline_error}")

    targets, selections = attribution.build_targets(prices, set())
    portfolio, contribution_rates, weights = attribution.simulate_with_attribution(returns, targets)
    asset_contribution, _ = attribution.calculate_asset_contributions(
        returns,
        portfolio,
        contribution_rates,
        weights,
        selections,
        analysis_index,
    )
    class_contribution = aggregate_class_contribution(asset_contribution)

    contribution_total = class_contribution["total_contribution"].sum()
    baseline_total_return = scenarios.iloc[0]["Total Return"]
    if abs(contribution_total - baseline_total_return) > 1e-10:
        raise RuntimeError("Asset class contribution does not reconcile to baseline Total Return")

    scenarios.to_csv(OUTPUT_DIR / "class_removal_sensitivity.csv", index=False)
    class_contribution.to_csv(OUTPUT_DIR / "asset_class_contribution.csv", index=False)
    scenario_daily_returns.to_csv(OUTPUT_DIR / "scenario_daily_returns.csv")
    summary = generate_summary(
        class_contribution,
        scenarios,
        analysis_index.min(),
        analysis_index.max(),
    )
    (OUTPUT_DIR / "summary.md").write_text(summary, encoding="utf-8")

    print("\nAsset Class Removal Test Complete")
    print(f"Results directory: {OUTPUT_DIR}")
    print(f"Baseline reproduction max error: {baseline_error:.3e}")
    print("\nClass contribution:")
    print(class_contribution.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nRemoval sensitivity:")
    print(scenarios.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
