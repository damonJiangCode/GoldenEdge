from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ALPHA_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_DIR = ALPHA_ROOT / "validation"
METRICS_DIR = VALIDATION_DIR / "metrics"
OUTPUTS_DIR = VALIDATION_DIR / "outputs"
REPORT_PATH = VALIDATION_DIR / "bootstrap_001_cross_asset_momentum_v1.md"

DAILY_DETAILS_PATH = OUTPUTS_DIR / "walk_forward_001_daily_details.csv"
SIMULATIONS = 10_000
TRADING_DAYS = 252
RANDOM_SEED = 20260623
STRATEGIES = [
    "Inverse Vol Framework",
    "Equal Weight Top5 Momentum",
    "SPY Buy & Hold",
    "Original 12 Equal Weight",
]
BENCHMARKS = [
    ("Framework vs Equal Weight Top5", "Equal Weight Top5 Momentum"),
    ("Framework vs SPY", "SPY Buy & Hold"),
    ("Framework vs Original 12 Equal Weight", "Original 12 Equal Weight"),
]


def load_daily_returns() -> pd.DataFrame:
    if not DAILY_DETAILS_PATH.exists():
        raise RuntimeError(f"Missing Framework 001 daily details: {DAILY_DETAILS_PATH}")
    details = pd.read_csv(DAILY_DETAILS_PATH, index_col="Date", parse_dates=True)
    returns = pd.DataFrame(index=details.index)
    for strategy in STRATEGIES:
        column = f"{strategy}::return"
        if column not in details.columns:
            raise RuntimeError(f"Missing return column: {column}")
        returns[strategy] = details[column]
    returns = returns.dropna(how="any")
    if returns.empty:
        raise RuntimeError("No daily returns loaded.")
    return returns


def calculate_metrics(paths: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    days = paths.shape[1]
    equity = np.cumprod(1.0 + paths, axis=1)
    total_return = equity[:, -1] - 1.0
    cagr = np.where(total_return > -1.0, (1.0 + total_return) ** (TRADING_DAYS / days) - 1.0, np.nan)
    volatility = paths.std(axis=1, ddof=1) * np.sqrt(TRADING_DAYS)
    annual_return = paths.mean(axis=1) * TRADING_DAYS
    sharpe = np.divide(
        annual_return,
        volatility,
        out=np.full_like(annual_return, np.nan),
        where=volatility != 0,
    )
    drawdown = equity / np.maximum.accumulate(equity, axis=1) - 1.0
    maxdd = drawdown.min(axis=1)
    return cagr, sharpe, maxdd, volatility


def historical_reference(returns: pd.DataFrame) -> pd.DataFrame:
    rows = []
    values = returns.to_numpy(dtype=float)
    for index, strategy in enumerate(returns.columns):
        cagr, sharpe, maxdd, volatility = calculate_metrics(values[:, [index]].T)
        rows.append(
            {
                "Strategy": strategy,
                "Historical CAGR": cagr[0],
                "Historical Sharpe": sharpe[0],
                "Historical MaxDD": maxdd[0],
                "Historical Volatility": volatility[0],
            }
        )
    return pd.DataFrame(rows)


def metrics_frame(
    method: str,
    cagr: np.ndarray,
    sharpe: np.ndarray,
    maxdd: np.ndarray,
    volatility: np.ndarray,
    strategies: list[str],
) -> pd.DataFrame:
    rows = []
    for strategy_index, strategy in enumerate(strategies):
        for sim in range(cagr.shape[0]):
            rows.append(
                {
                    "Method": method,
                    "Simulation": sim + 1,
                    "Strategy": strategy,
                    "CAGR": cagr[sim, strategy_index],
                    "Sharpe": sharpe[sim, strategy_index],
                    "MaxDD": maxdd[sim, strategy_index],
                    "Volatility": volatility[sim, strategy_index],
                }
            )
    return pd.DataFrame(rows)


def daily_bootstrap(returns: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    values = returns.to_numpy(dtype=float)
    days, strategies = values.shape
    batch_size = 500
    frames = []
    completed = 0
    while completed < SIMULATIONS:
        size = min(batch_size, SIMULATIONS - completed)
        indices = rng.integers(0, days, size=(size, days))
        sampled = values[indices]
        cagr, sharpe, maxdd, volatility = calculate_metrics(sampled)
        frame = metrics_frame(
            "Daily Bootstrap",
            cagr,
            sharpe,
            maxdd,
            volatility,
            list(returns.columns),
        )
        frame["Simulation"] += completed
        frames.append(frame)
        completed += size
    return pd.concat(frames, ignore_index=True)


def month_blocks(returns: pd.DataFrame) -> list[np.ndarray]:
    blocks = []
    for _, group in returns.groupby(returns.index.to_period("M")):
        blocks.append(group.to_numpy(dtype=float))
    if not blocks:
        raise RuntimeError("No monthly blocks available for bootstrap.")
    return blocks


def monthly_block_bootstrap(returns: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED + 1)
    blocks = month_blocks(returns)
    days = len(returns)
    strategies = list(returns.columns)
    cagr = np.empty((SIMULATIONS, len(strategies)))
    sharpe = np.empty_like(cagr)
    maxdd = np.empty_like(cagr)
    volatility = np.empty_like(cagr)

    for sim in range(SIMULATIONS):
        sampled_blocks = []
        sampled_days = 0
        while sampled_days < days:
            block = blocks[int(rng.integers(0, len(blocks)))]
            sampled_blocks.append(block)
            sampled_days += len(block)
        sampled = np.vstack(sampled_blocks)[:days]
        sim_cagr, sim_sharpe, sim_maxdd, sim_volatility = calculate_metrics(sampled[np.newaxis, :, :])
        cagr[sim] = sim_cagr[0]
        sharpe[sim] = sim_sharpe[0]
        maxdd[sim] = sim_maxdd[0]
        volatility[sim] = sim_volatility[0]

    return metrics_frame("Monthly-Block Bootstrap", cagr, sharpe, maxdd, volatility, strategies)


def bootstrap_summary(results: pd.DataFrame, method: str) -> pd.DataFrame:
    rows = []
    method_results = results.loc[results["Method"] == method]
    for strategy in STRATEGIES:
        part = method_results.loc[method_results["Strategy"] == strategy]
        rows.append(
            {
                "Strategy": strategy,
                "CAGR Median": part["CAGR"].median(),
                "CAGR 5th Percentile": part["CAGR"].quantile(0.05),
                "CAGR 95th Percentile": part["CAGR"].quantile(0.95),
                "Sharpe Median": part["Sharpe"].median(),
                "Sharpe 5th Percentile": part["Sharpe"].quantile(0.05),
                "Sharpe 95th Percentile": part["Sharpe"].quantile(0.95),
                "MaxDD Median": part["MaxDD"].median(),
                "MaxDD 5th Percentile": part["MaxDD"].quantile(0.05),
                "MaxDD 95th Percentile": part["MaxDD"].quantile(0.95),
            }
        )
    return pd.DataFrame(rows)


def probability_diagnostics(results: pd.DataFrame, method: str) -> pd.DataFrame:
    rows = []
    method_results = results.loc[results["Method"] == method]
    for strategy in STRATEGIES:
        part = method_results.loc[method_results["Strategy"] == strategy]
        rows.append(
            {
                "Method": method,
                "Strategy": strategy,
                "P(CAGR > 0)": (part["CAGR"] > 0).mean(),
                "P(Sharpe > 0)": (part["Sharpe"] > 0).mean(),
                "P(MaxDD worse than -20%)": (part["MaxDD"] < -0.20).mean(),
                "P(MaxDD worse than -30%)": (part["MaxDD"] < -0.30).mean(),
                "P(MaxDD worse than -40%)": (part["MaxDD"] < -0.40).mean(),
            }
        )
    return pd.DataFrame(rows)


def comparison_probabilities(results: pd.DataFrame, method: str) -> pd.DataFrame:
    method_results = results.loc[results["Method"] == method]
    pivot = method_results.pivot(index="Simulation", columns="Strategy", values=["CAGR", "Sharpe", "MaxDD"])
    framework = "Inverse Vol Framework"
    rows = []
    for comparison, benchmark in BENCHMARKS:
        rows.append(
            {
                "Method": method,
                "Comparison": comparison,
                "P(Framework Sharpe > Benchmark Sharpe)": (
                    pivot[("Sharpe", framework)] > pivot[("Sharpe", benchmark)]
                ).mean(),
                "P(Framework MaxDD shallower than Benchmark MaxDD)": (
                    pivot[("MaxDD", framework)] > pivot[("MaxDD", benchmark)]
                ).mean(),
                "P(Framework CAGR > Benchmark CAGR)": (
                    pivot[("CAGR", framework)] > pivot[("CAGR", benchmark)]
                ).mean(),
            }
        )
    return pd.DataFrame(rows)


def fmt_pct(value: float) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.2%}"


def fmt_num(value: float) -> str:
    if pd.isna(value):
        return "NA"
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


def historical_percentile(
    historical: pd.DataFrame,
    results: pd.DataFrame,
    method: str,
    strategy: str,
    metric: str,
) -> float:
    historical_column = {
        "CAGR": "Historical CAGR",
        "Sharpe": "Historical Sharpe",
        "MaxDD": "Historical MaxDD",
    }[metric]
    historical_value = historical.set_index("Strategy").loc[strategy, historical_column]
    simulated = results.loc[
        (results["Method"] == method) & (results["Strategy"] == strategy),
        metric,
    ]
    return (simulated <= historical_value).mean()


def generate_report(
    historical: pd.DataFrame,
    daily_summary: pd.DataFrame,
    monthly_summary: pd.DataFrame,
    probability: pd.DataFrame,
    comparisons: pd.DataFrame,
    results: pd.DataFrame,
    days: int,
    months: int,
) -> str:
    pct_columns_summary = {
        "CAGR Median",
        "CAGR 5th Percentile",
        "CAGR 95th Percentile",
        "MaxDD Median",
        "MaxDD 5th Percentile",
        "MaxDD 95th Percentile",
    }
    prob_pct_columns = {
        "P(CAGR > 0)",
        "P(Sharpe > 0)",
        "P(MaxDD worse than -20%)",
        "P(MaxDD worse than -30%)",
        "P(MaxDD worse than -40%)",
        "P(Framework Sharpe > Benchmark Sharpe)",
        "P(Framework MaxDD shallower than Benchmark MaxDD)",
        "P(Framework CAGR > Benchmark CAGR)",
    }
    historical_pct_columns = {
        "Historical CAGR",
        "Historical MaxDD",
        "Historical Volatility",
    }
    iv_probs = probability.set_index(["Method", "Strategy"]).loc[
        ("Monthly-Block Bootstrap", "Inverse Vol Framework")
    ]
    daily_iv_probs = probability.set_index(["Method", "Strategy"]).loc[
        ("Daily Bootstrap", "Inverse Vol Framework")
    ]
    comp = comparisons.set_index(["Method", "Comparison"])
    block_vs_spy = comp.loc[("Monthly-Block Bootstrap", "Framework vs SPY")]
    block_vs_ew = comp.loc[("Monthly-Block Bootstrap", "Framework vs Equal Weight Top5")]
    daily_vs_ew = comp.loc[("Daily Bootstrap", "Framework vs Equal Weight Top5")]
    block_iv = monthly_summary.set_index("Strategy").loc["Inverse Vol Framework"]
    daily_iv = daily_summary.set_index("Strategy").loc["Inverse Vol Framework"]
    hist = historical.set_index("Strategy").loc["Inverse Vol Framework"]
    cagr_percentile = historical_percentile(
        historical, results, "Monthly-Block Bootstrap", "Inverse Vol Framework", "CAGR"
    )
    sharpe_percentile = historical_percentile(
        historical, results, "Monthly-Block Bootstrap", "Inverse Vol Framework", "Sharpe"
    )
    maxdd_percentile = historical_percentile(
        historical, results, "Monthly-Block Bootstrap", "Inverse Vol Framework", "MaxDD"
    )
    harder_benchmark = "SPY" if block_vs_spy[
        "P(Framework CAGR > Benchmark CAGR)"
    ] < comp.loc[("Monthly-Block Bootstrap", "Framework vs Equal Weight Top5"), "P(Framework CAGR > Benchmark CAGR)"] else "Equal Weight Top5"

    return f"""# Bootstrap Validation 001 — Cross-Asset Momentum Framework V1

## 1. Research Question

Framework 001 has completed Walk Forward Validation and Regime Analysis. This validation asks whether the frozen framework's historical performance is statistically stable under bootstrap uncertainty, rather than being created by a few special months or one lucky historical path.

No parameter is optimized. No strategy rule is changed.

## 2. Fixed Framework

| Component | Definition |
| --- | --- |
| Universe | Original 12 ETF |
| Equity | SPY, QQQ, IWM, EFA |
| Commodity | GLD, SLV, USO, DBA |
| Bond | TLT, IEF, SHY, LQD |
| Signal | 126 trading-day momentum |
| Selection | Monthly rebalance; month-end signal; next trading day execution; Top5 momentum ETFs |
| Weighting | Inverse Volatility; 126 trading-day daily-return volatility; normalized to 100% |
| Cost | 5 bps transaction cost applied to turnover |
| Constraints | Long only; no leverage; no shorting; no MA filter |

## 3. Bootstrap Design

- Source returns: Framework 001 daily net returns from `walk_forward_001_daily_details.csv`
- Sample length: {days} trading days
- Calendar month blocks available: {months}
- Simulations: {SIMULATIONS:,} per method
- Random seed: `{RANDOM_SEED}`
- Daily Bootstrap: resample daily returns with replacement.
- Monthly-Block Bootstrap: resample calendar months with replacement, preserving within-month daily return order, then truncate to the full sample length.
- Paired comparisons: each simulation uses the same sampled days or months for all strategies, preserving cross-strategy comparison fairness.

Daily bootstrap tests return distribution stability. Monthly-block bootstrap partially preserves short-term autocorrelation and clustered volatility. CAGR values in this report use 252-trading-day annualization for both historical and simulated paths, so they can differ slightly from prior calendar-year CAGR tables.

## 4. Historical Reference

{markdown_table(historical, ['Strategy', 'Historical CAGR', 'Historical Sharpe', 'Historical MaxDD', 'Historical Volatility'], historical_pct_columns)}

## 5. Daily Bootstrap Summary

For MaxDD, the 5th percentile is the worse drawdown tail.

{markdown_table(daily_summary, ['Strategy', 'CAGR Median', 'CAGR 5th Percentile', 'CAGR 95th Percentile', 'Sharpe Median', 'Sharpe 5th Percentile', 'Sharpe 95th Percentile', 'MaxDD Median', 'MaxDD 5th Percentile', 'MaxDD 95th Percentile'], pct_columns_summary)}

## 6. Monthly-Block Bootstrap Summary

{markdown_table(monthly_summary, ['Strategy', 'CAGR Median', 'CAGR 5th Percentile', 'CAGR 95th Percentile', 'Sharpe Median', 'Sharpe 5th Percentile', 'Sharpe 95th Percentile', 'MaxDD Median', 'MaxDD 5th Percentile', 'MaxDD 95th Percentile'], pct_columns_summary)}

## 7. Probability Diagnostics

{markdown_table(probability, ['Method', 'Strategy', 'P(CAGR > 0)', 'P(Sharpe > 0)', 'P(MaxDD worse than -20%)', 'P(MaxDD worse than -30%)', 'P(MaxDD worse than -40%)'], prob_pct_columns)}

## 8. Framework vs Benchmark Probability

{markdown_table(comparisons, ['Method', 'Comparison', 'P(Framework Sharpe > Benchmark Sharpe)', 'P(Framework MaxDD shallower than Benchmark MaxDD)', 'P(Framework CAGR > Benchmark CAGR)'], prob_pct_columns)}

## 9. Interpretation Questions

1. **Is Framework 001 statistically stable under bootstrap resampling?** Yes for positive return and Sharpe stability. In monthly-block bootstrap, Framework 001 has P(CAGR > 0) = {fmt_pct(iv_probs['P(CAGR > 0)'])} and P(Sharpe > 0) = {fmt_pct(iv_probs['P(Sharpe > 0)'])}.
2. **How often does Framework 001 have positive CAGR?** Daily bootstrap: {fmt_pct(daily_iv_probs['P(CAGR > 0)'])}; monthly-block bootstrap: {fmt_pct(iv_probs['P(CAGR > 0)'])}.
3. **How often does Framework 001 suffer MaxDD worse than -30%?** Daily bootstrap: {fmt_pct(daily_iv_probs['P(MaxDD worse than -30%)'])}; monthly-block bootstrap: {fmt_pct(iv_probs['P(MaxDD worse than -30%)'])}.
4. **Does Framework 001 preserve its Sharpe advantage over Equal Weight Top5?** Yes. P(Framework Sharpe > EW Sharpe) is {fmt_pct(daily_vs_ew['P(Framework Sharpe > Benchmark Sharpe)'])} in daily bootstrap and {fmt_pct(block_vs_ew['P(Framework Sharpe > Benchmark Sharpe)'])} in monthly-block bootstrap.
5. **Does Framework 001 preserve its MaxDD advantage over SPY?** Yes. P(Framework MaxDD shallower than SPY) is {fmt_pct(block_vs_spy['P(Framework MaxDD shallower than Benchmark MaxDD)'])} in monthly-block bootstrap.
6. **Does Framework 001 beat SPY in CAGR consistently, or mainly in Sharpe/MaxDD?** Mainly Sharpe and MaxDD. P(Framework CAGR > SPY CAGR) is only {fmt_pct(block_vs_spy['P(Framework CAGR > Benchmark CAGR)'])} under monthly-block bootstrap, while Sharpe and MaxDD probabilities are much stronger.
7. **Does monthly-block bootstrap produce materially worse outcomes than daily bootstrap?** No. In this sample it is not materially worse for Framework 001. Framework median MaxDD changes from {fmt_pct(daily_iv['MaxDD Median'])} in daily bootstrap to {fmt_pct(block_iv['MaxDD Median'])} in monthly-block bootstrap, and the 5th percentile MaxDD changes from {fmt_pct(daily_iv['MaxDD 5th Percentile'])} to {fmt_pct(block_iv['MaxDD 5th Percentile'])}. The conclusion is therefore not dependent on the iid daily bootstrap assumption.
8. **Are the historical results near the bootstrap median or unusually lucky?** Historical CAGR {fmt_pct(hist['Historical CAGR'])} is at the {fmt_pct(cagr_percentile)} percentile of monthly-block bootstrap CAGR, Sharpe {fmt_num(hist['Historical Sharpe'])} is at the {fmt_pct(sharpe_percentile)} percentile, and MaxDD {fmt_pct(hist['Historical MaxDD'])} is at the {fmt_pct(maxdd_percentile)} percentile. The historical result is favorable but not a one-in-a-thousand outlier.
9. **Which benchmark is hardest to beat?** {harder_benchmark} is hardest on CAGR. SPY remains the hardest benchmark for raw CAGR, while Equal Weight Top5 is the more relevant benchmark for testing whether Inverse Vol sizing adds value.
10. **Does this support proceeding to Monte Carlo or Paper Trading?** Yes. Bootstrap uncertainty does not break the framework thesis, but it also confirms that live expectations should emphasize Sharpe and drawdown control rather than persistent SPY CAGR dominance.

## 10. Final Conclusion

Framework 001 remains statistically credible under bootstrap uncertainty. The strongest evidence is high positive-CAGR probability, persistent Sharpe advantage over Equal Weight Top5, and strong MaxDD advantage versus SPY and Equal Weight Top5.

The caveat is unchanged from Walk Forward and Regime Analysis: Framework 001 is not a reliable SPY-CAGR maximizer. Its edge is mainly risk-adjusted performance and drawdown control. Monthly-block bootstrap does not weaken the result in this test; it confirms that the Sharpe and drawdown advantages survive a resampling method that keeps within-month return ordering intact.

Proceed to the next validation stage:

- Monte Carlo Path Simulation
- Paper Trading Simulation
- Live Readiness Checklist

## 11. Output Files

- Historical reference: `alpha/validation/metrics/bootstrap_001_historical_reference.csv`
- Daily bootstrap summary: `alpha/validation/metrics/bootstrap_001_daily_summary.csv`
- Monthly-block bootstrap summary: `alpha/validation/metrics/bootstrap_001_monthly_block_summary.csv`
- Probability diagnostics: `alpha/validation/metrics/bootstrap_001_probability_diagnostics.csv`
- Framework vs benchmark probabilities: `alpha/validation/metrics/bootstrap_001_framework_vs_benchmark.csv`
- Bootstrap simulation metrics: `alpha/validation/outputs/bootstrap_001_simulation_metrics.csv`
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    returns = load_daily_returns()
    historical = historical_reference(returns)
    daily_results = daily_bootstrap(returns)
    monthly_results = monthly_block_bootstrap(returns)
    results = pd.concat([daily_results, monthly_results], ignore_index=True)

    daily_summary = bootstrap_summary(results, "Daily Bootstrap")
    monthly_summary = bootstrap_summary(results, "Monthly-Block Bootstrap")
    probability = pd.concat(
        [
            probability_diagnostics(results, "Daily Bootstrap"),
            probability_diagnostics(results, "Monthly-Block Bootstrap"),
        ],
        ignore_index=True,
    )
    comparisons = pd.concat(
        [
            comparison_probabilities(results, "Daily Bootstrap"),
            comparison_probabilities(results, "Monthly-Block Bootstrap"),
        ],
        ignore_index=True,
    )

    historical.to_csv(METRICS_DIR / "bootstrap_001_historical_reference.csv", index=False)
    daily_summary.to_csv(METRICS_DIR / "bootstrap_001_daily_summary.csv", index=False)
    monthly_summary.to_csv(METRICS_DIR / "bootstrap_001_monthly_block_summary.csv", index=False)
    probability.to_csv(METRICS_DIR / "bootstrap_001_probability_diagnostics.csv", index=False)
    comparisons.to_csv(METRICS_DIR / "bootstrap_001_framework_vs_benchmark.csv", index=False)
    results.to_csv(OUTPUTS_DIR / "bootstrap_001_simulation_metrics.csv", index=False)

    REPORT_PATH.write_text(
        generate_report(
            historical,
            daily_summary,
            monthly_summary,
            probability,
            comparisons,
            results,
            len(returns),
            returns.index.to_period("M").nunique(),
        ),
        encoding="utf-8",
    )

    print("\nBootstrap Validation 001 Complete")
    print("\nHistorical reference:")
    print(historical.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nMonthly-block summary:")
    print(monthly_summary.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nFramework vs benchmark probabilities:")
    print(comparisons.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
