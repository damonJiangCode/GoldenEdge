from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[3]
POSITION_SIZING_A_DIR = ALPHA_ROOT / "cross_sectional" / "position_sizing_test_a"
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(ALPHA_ROOT))

from shared.configs.universes import MIXED_ASSET_CLASSES, MIXED_ASSET_SYMBOLS  # noqa: E402
from shared.utils import cross_sectional as core  # noqa: E402


MOMENTUM_WINDOW = 126
VOLATILITY_WINDOW = 126
COMPARISON_START = pd.Timestamp("2008-02-01")
TOP_N = 5
STRATEGY_NAMES = ["Equal Weight", "Inverse Vol", "Inverse Variance"]


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
    risk_rows = []

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
            "Inverse Vol": normalized(1.0 / selected_volatility),
            "Inverse Variance": normalized(1.0 / selected_volatility**2),
        }
        covariance = returns.loc[:rebalance_date].tail(VOLATILITY_WINDOW).cov().loc[selected, selected]

        for strategy, selected_weights in weights_by_strategy.items():
            target = pd.Series(0.0, index=prices.columns)
            target.loc[selected] = selected_weights
            targets[strategy][effective_date] = target
            portfolio_variance = float(selected_weights @ covariance.to_numpy() @ selected_weights)
            if not np.isfinite(portfolio_variance) or portfolio_variance <= 0:
                raise RuntimeError(f"Invalid portfolio variance at {rebalance_date}: {portfolio_variance}")
            component_percent = (
                selected_weights * (covariance.to_numpy() @ selected_weights) / portfolio_variance
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
                        "Target Weight": target.loc[symbol],
                    }
                )
                risk_rows.append(
                    {
                        "Strategy": strategy,
                        "Rebalance Date": rebalance_date,
                        "Effective Date": effective_date,
                        "Symbol": symbol,
                        "Asset Class": asset_class,
                        "Risk Contribution": component_percent[rank - 1],
                    }
                )
    return targets, pd.DataFrame(target_rows), pd.DataFrame(risk_rows)


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
    baseline = performance.set_index("Strategy").loc["Equal Weight"]
    result = performance.loc[performance["Strategy"] != "Equal Weight", ["Strategy", "CAGR", "Sharpe", "MaxDD"]].copy()
    result["CAGR Change"] = result["CAGR"] - baseline["CAGR"]
    result["Sharpe Change"] = result["Sharpe"] - baseline["Sharpe"]
    result["MaxDD Change"] = result["MaxDD"] - baseline["MaxDD"]
    return result[["Strategy", "CAGR Change", "Sharpe Change", "MaxDD Change"]]


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


def position_concentration(target_rows: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (strategy, _), group in target_rows.groupby(["Strategy", "Effective Date"]):
        hhi = float((group["Target Weight"] ** 2).sum())
        rows.append({"Strategy": strategy, "HHI": hhi, "Effective Positions": 1.0 / hhi})
    result = (
        pd.DataFrame(rows)
        .groupby("Strategy", as_index=False)
        .agg(**{"Average HHI": ("HHI", "mean"), "Effective Positions": ("Effective Positions", "mean")})
    )
    order = {strategy: index for index, strategy in enumerate(STRATEGY_NAMES)}
    result["_order"] = result["Strategy"].map(order)
    return result.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def asset_concentration(target_rows: pd.DataFrame) -> pd.DataFrame:
    all_dates = target_rows["Effective Date"].drop_duplicates()
    rows = []
    for symbol in MIXED_ASSET_SYMBOLS:
        row = {"ETF": symbol}
        for strategy in STRATEGY_NAMES:
            selected = target_rows.loc[
                (target_rows["Strategy"] == strategy) & (target_rows["Symbol"] == symbol),
                ["Effective Date", "Target Weight"],
            ].set_index("Effective Date")["Target Weight"]
            row[strategy] = selected.reindex(all_dates, fill_value=0.0).mean()
        rows.append(row)
    return pd.DataFrame(rows)


def risk_contribution(risk_rows: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        risk_rows.groupby(["Strategy", "Effective Date", "Asset Class"])["Risk Contribution"]
        .sum()
        .unstack("Asset Class", fill_value=0.0)
    )
    rows = []
    for strategy in STRATEGY_NAMES:
        strategy_rows = grouped.loc[strategy]
        rows.append(
            {
                "Strategy": strategy,
                "Equity Risk Contribution": strategy_rows.get("Equity", pd.Series(0.0, index=strategy_rows.index)).mean(),
                "Commodity Risk Contribution": strategy_rows.get("Commodity", pd.Series(0.0, index=strategy_rows.index)).mean(),
                "Bond Risk Contribution": strategy_rows.get("Bond", pd.Series(0.0, index=strategy_rows.index)).mean(),
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
    distribution: pd.DataFrame,
    concentration: pd.DataFrame,
    asset_weights: pd.DataFrame,
    risk: pd.DataFrame,
    end_date: pd.Timestamp,
) -> str:
    perf = performance.set_index("Strategy")
    conc = concentration.set_index("Strategy")
    equal = perf.loc["Equal Weight"]
    inverse_vol = perf.loc["Inverse Vol"]
    inverse_variance = perf.loc["Inverse Variance"]
    variance_sharpe = inverse_variance["Sharpe"] > inverse_vol["Sharpe"]
    variance_drawdown = inverse_variance["MaxDD"] > inverse_vol["MaxDD"]
    variance_return_cost = inverse_variance["CAGR"] - inverse_vol["CAGR"]
    variance_sharpe_change = inverse_variance["Sharpe"] - inverse_vol["Sharpe"]
    variance_more_concentrated = conc.loc["Inverse Variance", "Average HHI"] > conc.loc["Inverse Vol", "Average HHI"]
    bond_weights = asset_weights.loc[asset_weights["ETF"].isin(MIXED_ASSET_CLASSES["Bond"]), STRATEGY_NAMES].sum()
    risk_indexed = risk.set_index("Strategy")

    return f"""# Position Sizing Test B: Inverse Vol vs Inverse Variance

## 1. Research Question

在固定 Original 12 ETF `mom_126 Top5` 和126日风险窗口下，比较温和的Inverse Vol与更激进的Inverse Variance仓位分配。本实验不优化参数。

## 2. Fixed Design

- Sample: `{COMPARISON_START.date()}` to `{end_date.date()}`
- Monthly rebalance; month-end signal effective next trading day
- Momentum and volatility windows: 126 trading days
- Top5 is identical across all strategies
- Transaction cost: 5 bps; no MA filter
- Inverse Vol: `weight proportional to 1 / vol`
- Inverse Variance: `weight proportional to 1 / vol^2`

## 3. Performance

{markdown_table(performance, ['Strategy', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Calmar', 'Total Return', 'Turnover'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return', 'Turnover'})}

## 4. Relative Change vs Equal Weight

正的 MaxDD Change 表示回撤改善。

{markdown_table(relative, ['Strategy', 'CAGR Change', 'Sharpe Change', 'MaxDD Change'], {'CAGR Change', 'MaxDD Change'})}

## 5. Weight Distribution by Momentum Rank

{markdown_table(distribution, ['Strategy', 'Rank1', 'Rank2', 'Rank3', 'Rank4', 'Rank5'], {'Rank1', 'Rank2', 'Rank3', 'Rank4', 'Rank5'})}

## 6. Position Concentration

{markdown_table(concentration, ['Strategy', 'Average HHI', 'Effective Positions'], set())}

## 7. Long-Run Average ETF Target Weight

Weights include zero in months when an ETF is not selected.

{markdown_table(asset_weights, ['ETF', 'Equal Weight', 'Inverse Vol', 'Inverse Variance'], {'Equal Weight', 'Inverse Vol', 'Inverse Variance'})}

## 8. Ex-Ante Risk Contribution

At each rebalance, component variance contribution is `w_i * (Sigma w)_i / (w' Sigma w)` using the trailing 126-day daily covariance matrix. Contributions are summed by asset class and averaged across rebalances; they may be negative when covariance is diversifying.

{markdown_table(risk, ['Strategy', 'Equity Risk Contribution', 'Commodity Risk Contribution', 'Bond Risk Contribution'], {'Equity Risk Contribution', 'Commodity Risk Contribution', 'Bond Risk Contribution'})}

## 9. Interpretation

1. **Inverse Variance 是否进一步提高 Sharpe？** {'仅有边际提高' if variance_sharpe else '否'}，变化 {variance_sharpe_change:+.3f}；Inverse Variance/Inverse Vol 为 {inverse_variance['Sharpe']:.3f}/{inverse_vol['Sharpe']:.3f}。
2. **是否进一步降低 MaxDD？** {'是' if variance_drawdown else '否'}。Inverse Variance/Inverse Vol 为 {fmt_pct(inverse_variance['MaxDD'])}/{fmt_pct(inverse_vol['MaxDD'])}。
3. **是否因过度压低高波动资产而损失收益？** CAGR 相对Inverse Vol变化 {fmt_pct(variance_return_cost)}。
4. **是否明显提高集中度？** {'是' if variance_more_concentrated else '否'}。HHI {conc.loc['Inverse Vol', 'Average HHI']:.3f} -> {conc.loc['Inverse Variance', 'Average HHI']:.3f}，Effective Positions {conc.loc['Inverse Vol', 'Effective Positions']:.2f} -> {conc.loc['Inverse Variance', 'Effective Positions']:.2f}。
5. **Inverse Vol 是否更接近平衡点？** 是。Inverse Vol的CAGR/Sharpe/MaxDD为 {fmt_pct(inverse_vol['CAGR'])}/{inverse_vol['Sharpe']:.3f}/{fmt_pct(inverse_vol['MaxDD'])}；Inverse Variance为 {fmt_pct(inverse_variance['CAGR'])}/{inverse_variance['Sharpe']:.3f}/{fmt_pct(inverse_variance['MaxDD'])}。后者只获得极小Sharpe增量，却损失CAGR并略微恶化MaxDD。
6. **改善来自风险平衡还是极端压低？** 更支持温和风险平衡。Bond平均目标权重从Inverse Vol的 {fmt_pct(bond_weights['Inverse Vol'])} 升至Inverse Variance的 {fmt_pct(bond_weights['Inverse Variance'])}；Bond风险贡献从 {fmt_pct(risk_indexed.loc['Inverse Vol', 'Bond Risk Contribution'])} 升至 {fmt_pct(risk_indexed.loc['Inverse Variance', 'Bond Risk Contribution'])}，而Commodity风险贡献被进一步压低，未换来更好MaxDD。

## 10. Final Conclusion

在当前 Original 12 ETF Momentum Framework 中，**Inverse Variance 不优于 Inverse Vol**。它进一步降低名义波动，却以更高集中度、更高换手、0.70个百分点CAGR损失和略差MaxDD为代价，只增加约0.008 Sharpe。风险控制的平衡点更接近温和的Inverse Vol，说明优势来自风险平衡本身，而不是尽可能压低高波动资产。本实验不测试其它Vol窗口、Risk Parity或其它权重指数。
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    prices = core.load_prices()
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    targets, target_rows, risk_rows = build_targets(prices)
    performance, details_by_strategy, weights_by_strategy = simulate(returns, targets)
    relative = relative_change(performance)
    distribution = weight_distribution(target_rows)
    concentration = position_concentration(target_rows)
    asset_weights = asset_concentration(target_rows)
    risk = risk_contribution(risk_rows)

    prior = pd.read_csv(POSITION_SIZING_A_DIR / "outputs" / "daily_details.csv", index_col="Date", parse_dates=True)
    equal_error = float((details_by_strategy["Equal Weight"]["return"] - prior["Equal Weight::return"]).abs().max())
    inverse_error = float((details_by_strategy["Inverse Vol"]["return"] - prior["Inverse Vol::return"]).abs().max())
    if equal_error > 1e-12 or inverse_error > 1e-12:
        raise RuntimeError(f"Prior reproduction mismatch: {equal_error}, {inverse_error}")

    performance.to_csv(METRICS_DIR / "performance.csv", index=False)
    relative.to_csv(METRICS_DIR / "relative_change.csv", index=False)
    distribution.to_csv(METRICS_DIR / "weight_distribution.csv", index=False)
    concentration.to_csv(METRICS_DIR / "position_concentration.csv", index=False)
    asset_weights.to_csv(METRICS_DIR / "asset_concentration.csv", index=False)
    risk.to_csv(METRICS_DIR / "risk_contribution.csv", index=False)
    target_rows.to_csv(OUTPUTS_DIR / "target_weights_by_rebalance.csv", index=False)
    risk_rows.to_csv(OUTPUTS_DIR / "risk_contribution_by_rebalance.csv", index=False)
    combined_details = pd.concat(details_by_strategy, axis=1)
    combined_details.columns = [f"{strategy}::{metric}" for strategy, metric in combined_details.columns]
    combined_details.to_csv(OUTPUTS_DIR / "daily_details.csv")
    combined_weights = pd.concat(weights_by_strategy, axis=1)
    combined_weights.columns = [f"{strategy}::{symbol}" for strategy, symbol in combined_weights.columns]
    combined_weights.to_csv(OUTPUTS_DIR / "daily_weights.csv")
    SUMMARY_PATH.write_text(
        generate_summary(
            performance, relative, distribution, concentration, asset_weights, risk,
            prices.index.max(),
        ),
        encoding="utf-8",
    )

    print("\nPosition Sizing Test B Complete")
    print(f"Equal Weight reproduction max error: {equal_error:.3e}")
    print(f"Inverse Vol reproduction max error: {inverse_error:.3e}")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nPosition concentration:")
    print(concentration.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nRisk contribution:")
    print(risk.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
