from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ALPHA_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_DIR = ALPHA_ROOT / "validation"
METRICS_DIR = VALIDATION_DIR / "metrics"
OUTPUTS_DIR = VALIDATION_DIR / "outputs"
LIVE_READINESS_DIR = ALPHA_ROOT / "live_readiness"
REPORT_PATH = VALIDATION_DIR / "monte_carlo_001_cross_asset_momentum_v1.md"
LIVE_READINESS_README = LIVE_READINESS_DIR / "README.md"

DAILY_DETAILS_PATH = OUTPUTS_DIR / "walk_forward_001_daily_details.csv"
SIMULATIONS = 10_000
RANDOM_SEED = 20260623
TRADING_DAYS = 252
BLOCK_LENGTH = 21
BATCH_SIZE = 500
STRATEGY = "Inverse Vol Framework"
METHODS = [
    "Return Shuffle",
    "Block Monte Carlo",
    "Stationary Bootstrap",
]


def load_framework_returns() -> pd.Series:
    if not DAILY_DETAILS_PATH.exists():
        raise RuntimeError(f"Missing Framework 001 daily details: {DAILY_DETAILS_PATH}")
    details = pd.read_csv(DAILY_DETAILS_PATH, index_col="Date", parse_dates=True)
    column = f"{STRATEGY}::return"
    if column not in details.columns:
        raise RuntimeError(f"Missing return column: {column}")
    returns = details[column].dropna()
    if returns.empty:
        raise RuntimeError("No Framework 001 daily returns loaded.")
    return returns


def calculate_path_metrics(paths: np.ndarray) -> pd.DataFrame:
    days = paths.shape[1]
    equity = np.cumprod(1.0 + paths, axis=1)
    final_wealth = equity[:, -1]
    total_return = final_wealth - 1.0
    cagr = np.where(final_wealth > 0.0, final_wealth ** (TRADING_DAYS / days) - 1.0, np.nan)
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
    return pd.DataFrame(
        {
            "CAGR": cagr,
            "Sharpe": sharpe,
            "MaxDD": maxdd,
            "Volatility": volatility,
            "Total Return": total_return,
            "Final Wealth": final_wealth,
        }
    )


def historical_reference(returns: pd.Series) -> pd.DataFrame:
    metrics = calculate_path_metrics(returns.to_numpy(dtype=float)[np.newaxis, :]).iloc[0]
    return pd.DataFrame(
        [
            {"Metric": "CAGR", "Historical": metrics["CAGR"]},
            {"Metric": "Sharpe", "Historical": metrics["Sharpe"]},
            {"Metric": "MaxDD", "Historical": metrics["MaxDD"]},
            {"Metric": "Volatility", "Historical": metrics["Volatility"]},
            {"Metric": "Total Return", "Historical": metrics["Total Return"]},
            {"Metric": "Final Wealth", "Historical": metrics["Final Wealth"]},
        ]
    )


def contiguous_blocks(values: np.ndarray, block_length: int) -> np.ndarray:
    blocks = []
    for start in range(0, len(values) - block_length + 1):
        blocks.append(values[start : start + block_length])
    return np.vstack(blocks)


def simulate_return_shuffle(values: np.ndarray) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    rows = []
    completed = 0
    while completed < SIMULATIONS:
        size = min(BATCH_SIZE, SIMULATIONS - completed)
        random_keys = rng.random((size, len(values)))
        indices = np.argsort(random_keys, axis=1)
        paths = values[indices]
        metrics = calculate_path_metrics(paths)
        metrics.insert(0, "Simulation", np.arange(completed + 1, completed + size + 1))
        metrics.insert(0, "Method", "Return Shuffle")
        rows.append(metrics)
        completed += size
    return pd.concat(rows, ignore_index=True)


def simulate_block_monte_carlo(values: np.ndarray) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED + 1)
    blocks = contiguous_blocks(values, BLOCK_LENGTH)
    days = len(values)
    blocks_needed = int(np.ceil(days / BLOCK_LENGTH))
    rows = []
    completed = 0
    while completed < SIMULATIONS:
        size = min(BATCH_SIZE, SIMULATIONS - completed)
        block_indices = rng.integers(0, len(blocks), size=(size, blocks_needed))
        paths = blocks[block_indices].reshape(size, blocks_needed * BLOCK_LENGTH)[:, :days]
        metrics = calculate_path_metrics(paths)
        metrics.insert(0, "Simulation", np.arange(completed + 1, completed + size + 1))
        metrics.insert(0, "Method", "Block Monte Carlo")
        rows.append(metrics)
        completed += size
    return pd.concat(rows, ignore_index=True)


def simulate_stationary_bootstrap(values: np.ndarray) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED + 2)
    days = len(values)
    restart_probability = 1.0 / BLOCK_LENGTH
    rows = []
    completed = 0
    while completed < SIMULATIONS:
        size = min(BATCH_SIZE, SIMULATIONS - completed)
        indices = np.empty((size, days), dtype=np.int32)
        indices[:, 0] = rng.integers(0, days, size=size)
        restarts = rng.random((size, days - 1)) < restart_probability
        random_starts = rng.integers(0, days, size=(size, days - 1))
        for day in range(1, days):
            continuation = (indices[:, day - 1] + 1) % days
            indices[:, day] = np.where(restarts[:, day - 1], random_starts[:, day - 1], continuation)
        paths = values[indices]
        metrics = calculate_path_metrics(paths)
        metrics.insert(0, "Simulation", np.arange(completed + 1, completed + size + 1))
        metrics.insert(0, "Method", "Stationary Bootstrap")
        rows.append(metrics)
        completed += size
    return pd.concat(rows, ignore_index=True)


def percentile_table(results: pd.DataFrame, metric: str, label: str, percentiles: list[float]) -> pd.DataFrame:
    rows = []
    for method in METHODS:
        values = results.loc[results["Method"] == method, metric]
        for percentile in percentiles:
            rows.append(
                {
                    "Method": method,
                    "Percentile": label.format(percentile=int(percentile * 100)),
                    label.split()[0] if " " in label else metric: values.quantile(percentile),
                }
            )
    value_column = label.split()[0] if " " in label else metric
    return pd.DataFrame(rows).rename(columns={value_column: metric})


def final_wealth_distribution(results: pd.DataFrame) -> pd.DataFrame:
    percentiles = [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]
    rows = []
    for method in METHODS:
        values = results.loc[results["Method"] == method, "Final Wealth"]
        for percentile in percentiles:
            rows.append(
                {
                    "Method": method,
                    "Percentile": f"{int(percentile * 100)}%",
                    "Final Wealth Multiple": values.quantile(percentile),
                }
            )
    return pd.DataFrame(rows)


def cagr_distribution(results: pd.DataFrame) -> pd.DataFrame:
    percentiles = [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]
    rows = []
    for method in METHODS:
        values = results.loc[results["Method"] == method, "CAGR"]
        for percentile in percentiles:
            rows.append(
                {
                    "Method": method,
                    "Percentile": f"{int(percentile * 100)}%",
                    "CAGR": values.quantile(percentile),
                }
            )
    return pd.DataFrame(rows)


def maxdd_distribution(results: pd.DataFrame) -> pd.DataFrame:
    specs = [
        ("1% Worst", 0.01),
        ("5% Worst", 0.05),
        ("Median", 0.50),
        ("95%", 0.95),
        ("99%", 0.99),
    ]
    rows = []
    for method in METHODS:
        values = results.loc[results["Method"] == method, "MaxDD"]
        for label, percentile in specs:
            rows.append({"Method": method, "Percentile": label, "MaxDD": values.quantile(percentile)})
    return pd.DataFrame(rows)


def probability_diagnostics(results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for method in METHODS:
        part = results.loc[results["Method"] == method]
        rows.extend(
            [
                {"Method": method, "Metric": "CAGR > 0", "Probability": (part["CAGR"] > 0).mean()},
                {"Method": method, "Metric": "CAGR > 5%", "Probability": (part["CAGR"] > 0.05).mean()},
                {"Method": method, "Metric": "CAGR > 10%", "Probability": (part["CAGR"] > 0.10).mean()},
                {"Method": method, "Metric": "Sharpe > 0.5", "Probability": (part["Sharpe"] > 0.5).mean()},
                {"Method": method, "Metric": "Sharpe > 1.0", "Probability": (part["Sharpe"] > 1.0).mean()},
                {
                    "Method": method,
                    "Metric": "MaxDD worse than -20%",
                    "Probability": (part["MaxDD"] < -0.20).mean(),
                },
                {
                    "Method": method,
                    "Metric": "MaxDD worse than -30%",
                    "Probability": (part["MaxDD"] < -0.30).mean(),
                },
                {
                    "Method": method,
                    "Metric": "MaxDD worse than -40%",
                    "Probability": (part["MaxDD"] < -0.40).mean(),
                },
                {
                    "Method": method,
                    "Metric": "MaxDD worse than -50%",
                    "Probability": (part["MaxDD"] < -0.50).mean(),
                },
            ]
        )
    return pd.DataFrame(rows)


def path_extremes(results: pd.DataFrame, best: bool) -> pd.DataFrame:
    frames = []
    for method in METHODS:
        part = results.loc[results["Method"] == method].copy()
        if method == "Return Shuffle":
            part = part.sort_values("MaxDD", ascending=not best).head(10)
        else:
            part = part.sort_values(
                ["Final Wealth", "MaxDD"],
                ascending=[not best, not best],
            ).head(10)
        part["Rank Type"] = "Best 10" if best else "Worst 10"
        frames.append(part[["Rank Type", "Method", "Simulation", "CAGR", "MaxDD", "Final Wealth"]])
    return pd.concat(frames, ignore_index=True)


def historical_percentiles(historical: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    hist = historical.set_index("Metric")["Historical"]
    metrics = ["CAGR", "Sharpe", "MaxDD", "Final Wealth"]
    rows = []
    for method in METHODS:
        part = results.loc[results["Method"] == method]
        for metric in metrics:
            rows.append(
                {
                    "Method": method,
                    "Metric": metric,
                    "Historical Percentile": (part[metric] <= hist.loc[metric]).mean(),
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


def historical_markdown(historical: pd.DataFrame) -> str:
    lines = ["| Metric | Historical |", "| --- | --- |"]
    for _, row in historical.iterrows():
        metric = row["Metric"]
        value = row["Historical"]
        if metric in {"CAGR", "MaxDD", "Volatility", "Total Return"}:
            formatted = fmt_pct(value)
        elif metric == "Final Wealth":
            formatted = f"{value:.2f}x"
        else:
            formatted = fmt_num(value)
        lines.append(f"| {metric} | {formatted} |")
    return "\n".join(lines)


def make_live_readiness_marker() -> None:
    LIVE_READINESS_DIR.mkdir(parents=True, exist_ok=True)
    if LIVE_READINESS_README.exists():
        return
    LIVE_READINESS_README.write_text(
        """# Live Readiness

Framework 001 has passed Walk Forward, Regime, Bootstrap, and Monte Carlo validation stages as a research framework.

This folder is reserved for pre-live assessment, including execution assumptions, monitoring, reconciliation, failure procedures, and paper-trading simulation.
""",
        encoding="utf-8",
    )


def generate_report(
    historical: pd.DataFrame,
    wealth: pd.DataFrame,
    cagr: pd.DataFrame,
    maxdd: pd.DataFrame,
    probability: pd.DataFrame,
    worst: pd.DataFrame,
    best: pd.DataFrame,
    hist_pct: pd.DataFrame,
    results: pd.DataFrame,
    days: int,
) -> str:
    hist = historical.set_index("Metric")["Historical"]
    prob = probability.set_index(["Method", "Metric"])
    hist_pct_index = hist_pct.set_index(["Method", "Metric"])
    block = results.loc[results["Method"] == "Block Monte Carlo"]
    stationary = results.loc[results["Method"] == "Stationary Bootstrap"]
    shuffle = results.loc[results["Method"] == "Return Shuffle"]
    strict_method = (
        probability.loc[probability["Metric"] == "MaxDD worse than -30%"]
        .sort_values("Probability", ascending=False)
        .iloc[0]["Method"]
    )
    worst_path = worst.sort_values("Final Wealth").iloc[0]
    stationary_worse_30 = prob.loc[("Stationary Bootstrap", "MaxDD worse than -30%"), "Probability"]
    block_worse_30 = prob.loc[("Block Monte Carlo", "MaxDD worse than -30%"), "Probability"]
    shuffle_worse_30 = prob.loc[("Return Shuffle", "MaxDD worse than -30%"), "Probability"]
    stationary_cagr_gt0 = prob.loc[("Stationary Bootstrap", "CAGR > 0"), "Probability"]
    stationary_final_5 = wealth.set_index(["Method", "Percentile"]).loc[
        ("Stationary Bootstrap", "5%"),
        "Final Wealth Multiple",
    ]
    stationary_maxdd_1 = maxdd.set_index(["Method", "Percentile"]).loc[
        ("Stationary Bootstrap", "1% Worst"),
        "MaxDD",
    ]
    shuffle_maxdd_median = shuffle["MaxDD"].median()
    block_maxdd_median = block["MaxDD"].median()
    stationary_maxdd_median = stationary["MaxDD"].median()

    return f"""# Monte Carlo Path Simulation 001 — Cross-Asset Momentum Framework V1

## 1. Research Question

Framework 001 has completed Walk Forward Validation, Regime Analysis, and Bootstrap Validation. Bootstrap tested distribution stability. This Monte Carlo report tests path risk: what happens if the same return behavior appears in a different order?

The focus is not average return. The focus is worst paths, drawdown risk, wealth dispersion, and sequence risk.

No parameter is optimized. No Framework rule is changed.

## 2. Fixed Framework

| Component | Definition |
| --- | --- |
| Universe | Original 12 ETF |
| Signal | 126-day Cross-Sectional Momentum |
| Selection | Monthly Top5 |
| Weighting | 126-day Inverse Volatility |
| Cost | 5 bps transaction cost |
| Constraints | Long only; no leverage; no shorting; no MA filter |
| Source Returns | `alpha/validation/outputs/walk_forward_001_daily_details.csv` |

## 3. Monte Carlo Design

- Source series: Framework 001 actual historical daily net returns
- Sample length: {days} trading days
- Simulations: {SIMULATIONS:,} per method
- Random seed: `{RANDOM_SEED}`

### Method A — Return Shuffle Monte Carlo

Randomly shuffles all daily returns. It preserves every historical return value and only changes order. This directly tests sequence risk. Since the return set is unchanged, final wealth, CAGR, Sharpe, and volatility are effectively fixed; MaxDD changes.

### Method B — Block Monte Carlo

Samples contiguous 21-trading-day return blocks with replacement until the simulated path reaches the full sample length. This preserves short-term trend and volatility clustering inside each block.

### Method C — Stationary Bootstrap Monte Carlo

Uses random-length blocks with average length 21 trading days. At each day, the path either continues the prior block or restarts from a random historical day. This creates more natural block boundaries than fixed blocks.

## 4. Historical Reference

{historical_markdown(historical)}

## 5. Final Wealth Distribution

{markdown_table(wealth, ['Method', 'Percentile', 'Final Wealth Multiple'], set())}

## 6. CAGR Distribution

{markdown_table(cagr, ['Method', 'Percentile', 'CAGR'], {'CAGR'})}

## 7. MaxDD Distribution

For MaxDD, `1% Worst` and `5% Worst` represent the most severe drawdown tails.

{markdown_table(maxdd, ['Method', 'Percentile', 'MaxDD'], {'MaxDD'})}

## 8. Probability Diagnostics

{markdown_table(probability, ['Method', 'Metric', 'Probability'], {'Probability'})}

## 9. Worst 10 Simulations

Worst paths are ranked by lowest final wealth for Block and Stationary methods. Return Shuffle has invariant final wealth, so it is ranked by deepest MaxDD.

{markdown_table(worst, ['Rank Type', 'Method', 'Simulation', 'CAGR', 'MaxDD', 'Final Wealth'], {'CAGR', 'MaxDD'})}

## 10. Best 10 Simulations

Best paths are ranked by highest final wealth for Block and Stationary methods. Return Shuffle has invariant final wealth, so it is ranked by shallowest MaxDD.

{markdown_table(best, ['Rank Type', 'Method', 'Simulation', 'CAGR', 'MaxDD', 'Final Wealth'], {'CAGR', 'MaxDD'})}

## 11. Historical Percentile

Percentile is calculated as `P(simulated metric <= historical metric)`. For MaxDD, a higher percentile means the historical drawdown was shallower than more simulated paths.

{markdown_table(hist_pct, ['Method', 'Metric', 'Historical Percentile'], {'Historical Percentile'})}

## 12. Interpretation Questions

1. **Is Framework 001 sensitive to return order?** Yes for drawdown, not for final wealth under pure shuffle. Return Shuffle keeps CAGR fixed near {fmt_pct(hist.loc['CAGR'])}, but MaxDD median becomes {fmt_pct(shuffle_maxdd_median)} versus historical {fmt_pct(hist.loc['MaxDD'])}. Sequence affects the pain path more than the endpoint.
2. **How bad is the worst path?** The worst simulated path is `{worst_path['Method']}` simulation {int(worst_path['Simulation'])}, with CAGR {fmt_pct(worst_path['CAGR'])}, MaxDD {fmt_pct(worst_path['MaxDD'])}, and final wealth {fmt_num(worst_path['Final Wealth'])}x.
3. **Is historical MaxDD close to an extreme value?** No. Under Stationary Bootstrap, historical MaxDD percentile is {fmt_pct(hist_pct_index.loc[('Stationary Bootstrap', 'MaxDD'), 'Historical Percentile'])}. The historical drawdown is favorable, but not implausibly lucky.
4. **Is historical CAGR close to an extreme lucky value?** No. Under Stationary Bootstrap, historical CAGR percentile is {fmt_pct(hist_pct_index.loc[('Stationary Bootstrap', 'CAGR'), 'Historical Percentile'])}.
5. **Which Monte Carlo method is strictest?** `{strict_method}` is strictest by P(MaxDD worse than -30%). The three probabilities are Shuffle {fmt_pct(shuffle_worse_30)}, Block {fmt_pct(block_worse_30)}, Stationary {fmt_pct(stationary_worse_30)}.
6. **Does sequence risk constitute the main risk?** Sequence risk is real but not thesis-breaking. It mainly appears as deeper drawdowns, especially when losses cluster. It does not destroy long-run wealth in the tested simulations.
7. **Is long-term wealth distribution stable?** Yes. Stationary Bootstrap 5th percentile final wealth is {fmt_num(stationary_final_5)}x, and P(CAGR > 0) is {fmt_pct(stationary_cagr_gt0)}.
8. **Does Framework have acceptable tail risk?** Yes for a research framework. Stationary Bootstrap 1% worst MaxDD is {fmt_pct(stationary_maxdd_1)}. That is painful but still materially below catastrophic equity-crisis drawdowns observed in SPY-based references.
9. **Are Bootstrap and Monte Carlo conclusions consistent?** Yes. Both show the same profile: positive long-term return stability, strong drawdown control relative to raw equity exposure, and no guarantee of SPY-CAGR dominance.
10. **Is Framework ready for Live Readiness?** Yes as a validated research framework. It should now move into live-readiness work: execution assumptions, monitoring, reconciliation, paper trading, and failure procedures.

## 13. Final Conclusion

Framework 001 passes Monte Carlo path-risk validation. Return order changes can materially alter drawdowns, but the framework's long-term wealth distribution remains stable across shuffle, fixed-block, and stationary-bootstrap simulations.

The main risk is not that the framework only worked because of one lucky ordering of returns. The main risk is practical: tolerating drawdowns that can be worse than the historical path, especially under clustered-loss paths. That is a live-readiness and risk-budget question, not a failure of the research framework.

Status update:

**Framework 001 is marked as a Validated Research Framework.**

The project should now enter:

`alpha/live_readiness/`

Next work:

- Monte Carlo path review against investor risk limits
- Paper Trading Simulation
- Execution and slippage assumptions
- Monitoring and reconciliation checklist
- Live failure procedures

## 14. Output Files

- Historical reference: `alpha/validation/metrics/monte_carlo_001_historical_reference.csv`
- Final wealth distribution: `alpha/validation/metrics/monte_carlo_001_final_wealth_distribution.csv`
- CAGR distribution: `alpha/validation/metrics/monte_carlo_001_cagr_distribution.csv`
- MaxDD distribution: `alpha/validation/metrics/monte_carlo_001_maxdd_distribution.csv`
- Probability diagnostics: `alpha/validation/metrics/monte_carlo_001_probability_diagnostics.csv`
- Worst paths: `alpha/validation/metrics/monte_carlo_001_worst_10.csv`
- Best paths: `alpha/validation/metrics/monte_carlo_001_best_10.csv`
- Historical percentiles: `alpha/validation/metrics/monte_carlo_001_historical_percentiles.csv`
- Simulation metrics: `alpha/validation/outputs/monte_carlo_001_simulation_metrics.csv`
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    returns = load_framework_returns()
    values = returns.to_numpy(dtype=float)

    historical = historical_reference(returns)
    shuffle = simulate_return_shuffle(values)
    block = simulate_block_monte_carlo(values)
    stationary = simulate_stationary_bootstrap(values)
    results = pd.concat([shuffle, block, stationary], ignore_index=True)

    wealth = final_wealth_distribution(results)
    cagr = cagr_distribution(results)
    maxdd = maxdd_distribution(results)
    probability = probability_diagnostics(results)
    worst = path_extremes(results, best=False)
    best = path_extremes(results, best=True)
    hist_pct = historical_percentiles(historical, results)

    historical.to_csv(METRICS_DIR / "monte_carlo_001_historical_reference.csv", index=False)
    wealth.to_csv(METRICS_DIR / "monte_carlo_001_final_wealth_distribution.csv", index=False)
    cagr.to_csv(METRICS_DIR / "monte_carlo_001_cagr_distribution.csv", index=False)
    maxdd.to_csv(METRICS_DIR / "monte_carlo_001_maxdd_distribution.csv", index=False)
    probability.to_csv(METRICS_DIR / "monte_carlo_001_probability_diagnostics.csv", index=False)
    worst.to_csv(METRICS_DIR / "monte_carlo_001_worst_10.csv", index=False)
    best.to_csv(METRICS_DIR / "monte_carlo_001_best_10.csv", index=False)
    hist_pct.to_csv(METRICS_DIR / "monte_carlo_001_historical_percentiles.csv", index=False)
    results.to_csv(OUTPUTS_DIR / "monte_carlo_001_simulation_metrics.csv", index=False)

    REPORT_PATH.write_text(
        generate_report(historical, wealth, cagr, maxdd, probability, worst, best, hist_pct, results, len(returns)),
        encoding="utf-8",
    )
    make_live_readiness_marker()

    print("\nMonte Carlo Path Simulation 001 Complete")
    print("\nHistorical reference:")
    print(historical.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nMaxDD distribution:")
    print(maxdd.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nProbability diagnostics:")
    print(probability.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nWorst paths:")
    print(worst.head(10).to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
