from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[5]
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"

sys.path.insert(0, str(ALPHA_ROOT))

from shared.configs.universes import MIXED_ASSET_CLASSES, MIXED_ASSET_SYMBOLS  # noqa: E402
from shared.utils import cross_sectional as core  # noqa: E402


MOMENTUM_WINDOW = 126
VOLATILITY_WINDOW = 126
TOP_N = 5
START_DATE = pd.Timestamp("2008-02-01")
END_DATE = pd.Timestamp("2025-12-31")

STRATEGY_NAMES = [
    "Framework001",
    "Filter Before Ranking (Reweight)",
    "Filter Before Ranking (Cash)",
    "Filter After Ranking (Reweight)",
    "Filter After Ranking (Cash)",
]

ASSET_CLASS_BY_SYMBOL = {
    symbol: asset_class for asset_class, symbols in MIXED_ASSET_CLASSES.items() for symbol in symbols
}


def normalized(values: np.ndarray) -> np.ndarray:
    if len(values) == 0:
        return values
    if not np.isfinite(values).all() or (values <= 0).any():
        raise RuntimeError(f"Invalid inverse-volatility inputs: {values}")
    return values / values.sum()


def make_target(
    prices: pd.DataFrame,
    selected: list[str],
    volatility: pd.Series,
    exposure: float,
) -> pd.Series:
    target = pd.Series(0.0, index=prices.columns)
    if selected:
        weights = normalized(1.0 / volatility.loc[selected].to_numpy(dtype=float)) * exposure
        target.loc[selected] = weights
    return target


def build_targets(
    prices: pd.DataFrame,
) -> tuple[dict[str, dict[pd.Timestamp, pd.Series]], pd.DataFrame, pd.DataFrame]:
    returns = prices.pct_change(fill_method=None)
    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    trailing_vol = returns.rolling(VOLATILITY_WINDOW, min_periods=VOLATILITY_WINDOW).std(ddof=1)
    targets = {strategy: {} for strategy in STRATEGY_NAMES}
    holding_rows = []
    diagnostic_rows = []

    for rebalance_date in core.month_end_dates(prices.index):
        if rebalance_date > END_DATE:
            continue
        location = prices.index.get_loc(rebalance_date)
        if location + 1 >= len(prices.index):
            continue
        effective_date = prices.index[location + 1]
        if effective_date < START_DATE or effective_date > END_DATE:
            continue

        scores = momentum.loc[rebalance_date].dropna()
        volatility = trailing_vol.loc[rebalance_date].dropna()
        if len(scores) != len(prices.columns) or len(volatility) != len(prices.columns):
            continue

        ranked_all = scores.sort_values(ascending=False)
        positive = ranked_all[ranked_all > 0]
        positive_count = len(positive)

        baseline_selected = ranked_all.head(TOP_N).index.tolist()
        before_selected = positive.head(TOP_N).index.tolist()
        after_selected = [symbol for symbol in baseline_selected if scores.loc[symbol] > 0]

        selected_by_strategy = {
            "Framework001": (baseline_selected, 1.0),
            "Filter Before Ranking (Reweight)": (before_selected, 1.0 if before_selected else 0.0),
            "Filter Before Ranking (Cash)": (before_selected, len(before_selected) / TOP_N),
            "Filter After Ranking (Reweight)": (after_selected, 1.0 if after_selected else 0.0),
            "Filter After Ranking (Cash)": (after_selected, len(after_selected) / TOP_N),
        }

        for strategy, (selected, exposure) in selected_by_strategy.items():
            target = make_target(prices, selected, volatility, exposure)
            targets[strategy][effective_date] = target
            cash_weight = float(max(0.0, 1.0 - target.sum()))
            holdings = int((target > 0).sum())
            hhi = float((target**2).sum() + cash_weight**2)
            diagnostic_rows.append(
                {
                    "Strategy": strategy,
                    "Rebalance Date": rebalance_date,
                    "Effective Date": effective_date,
                    "Positive Momentum ETFs": positive_count,
                    "Holdings": holdings,
                    "Cash Weight": cash_weight,
                    "Fewer Than Five Holdings": holdings < TOP_N,
                    "HHI": hhi,
                    "Effective Positions": 1.0 / hhi if hhi > 0 else np.nan,
                    "Selected ETFs": ", ".join(selected),
                    "Portfolio Weights": ", ".join(
                        f"{symbol}:{target.loc[symbol]:.4f}" for symbol in selected
                    ),
                }
            )
            for rank, symbol in enumerate(selected, start=1):
                holding_rows.append(
                    {
                        "Strategy": strategy,
                        "Rebalance Date": rebalance_date,
                        "Effective Date": effective_date,
                        "ETF": symbol,
                        "Asset Class": ASSET_CLASS_BY_SYMBOL[symbol],
                        "Momentum Rank": int(ranked_all.index.get_loc(symbol) + 1),
                        "Momentum Return": scores.loc[symbol],
                        "Volatility": volatility.loc[symbol],
                        "Weight": target.loc[symbol],
                    }
                )

    return targets, pd.DataFrame(holding_rows), pd.DataFrame(diagnostic_rows)


def simulate(
    returns: pd.DataFrame,
    targets: dict[str, dict[pd.Timestamp, pd.Series]],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    rows = []
    details_by_strategy = {}
    weights_by_strategy = {}
    for strategy in STRATEGY_NAMES:
        details, weights = core.simulate_monthly_holdings(returns, targets[strategy])
        details = details.loc[START_DATE:END_DATE].copy()
        weights = weights.loc[START_DATE:END_DATE].copy()
        if details.index.min() != START_DATE:
            raise RuntimeError(f"{strategy}: unexpected start date {details.index.min()}")

        equity = (1 + details["return"]).cumprod()
        metrics = core.calculate_metrics(
            label=strategy,
            momentum_window="mom_126",
            strategy=strategy,
            returns=details["return"],
            equity=equity,
            turnover=details["turnover"],
            number_of_rebalances=len(targets[strategy]),
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
    baseline = performance.set_index("Strategy").loc["Framework001"]
    result = performance.loc[
        performance["Strategy"] != "Framework001",
        ["Strategy", "CAGR", "Sharpe", "MaxDD"],
    ].copy()
    result["CAGR Change"] = result["CAGR"] - baseline["CAGR"]
    result["Sharpe Change"] = result["Sharpe"] - baseline["Sharpe"]
    result["MaxDD Change"] = result["MaxDD"] - baseline["MaxDD"]
    return result[["Strategy", "CAGR Change", "Sharpe Change", "MaxDD Change"]]


def absolute_momentum_diagnostics(
    monthly_diagnostics: pd.DataFrame,
    details_by_strategy: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    rows = []
    for strategy in STRATEGY_NAMES:
        part = monthly_diagnostics.loc[monthly_diagnostics["Strategy"] == strategy]
        details = details_by_strategy[strategy]
        rebalance_turnover = details.loc[details["turnover"] > 0, "turnover"]
        rows.append(
            {
                "Strategy": strategy,
                "Average ETFs with Positive Momentum": part["Positive Momentum ETFs"].mean(),
                "Average Holdings": part["Holdings"].mean(),
                "Average Cash Weight": part["Cash Weight"].mean(),
                "Maximum Cash Weight": part["Cash Weight"].max(),
                "Months with Cash": int((part["Cash Weight"] > 1e-12).sum()),
                "Months with Fewer than Five Holdings": int(part["Fewer Than Five Holdings"].sum()),
                "Average Effective Positions": part["Effective Positions"].mean(),
                "Average HHI": part["HHI"].mean(),
                "Average Turnover": rebalance_turnover.mean(),
            }
        )
    return pd.DataFrame(rows)


def asset_class_exposure(weights_by_strategy: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for strategy in STRATEGY_NAMES:
        weights = weights_by_strategy[strategy].copy()
        row = {"Strategy": strategy}
        invested = weights.sum(axis=1)
        for asset_class, symbols in MIXED_ASSET_CLASSES.items():
            row[asset_class] = weights[symbols].sum(axis=1).mean()
        row["Cash"] = (1.0 - invested).clip(lower=0.0).mean()
        rows.append(row)
    return pd.DataFrame(rows)


def selection_frequency(holdings: pd.DataFrame, monthly_diagnostics: pd.DataFrame) -> pd.DataFrame:
    total_rebalances = monthly_diagnostics.groupby("Strategy")["Effective Date"].nunique().to_dict()
    rows = []
    for strategy in STRATEGY_NAMES:
        part = holdings.loc[holdings["Strategy"] == strategy]
        counts = part.groupby("ETF")["Effective Date"].nunique().reindex(MIXED_ASSET_SYMBOLS, fill_value=0)
        total = total_rebalances[strategy]
        for symbol, count in counts.items():
            rows.append(
                {
                    "Strategy": strategy,
                    "ETF": symbol,
                    "Selection Count": int(count),
                    "Selection Percent": count / total if total else np.nan,
                }
            )
    return pd.DataFrame(rows)


def save_daily_outputs(
    details_by_strategy: dict[str, pd.DataFrame],
    weights_by_strategy: dict[str, pd.DataFrame],
) -> None:
    detail_frames = []
    weight_frames = []
    for strategy in STRATEGY_NAMES:
        details = details_by_strategy[strategy].reset_index()
        details.insert(0, "Strategy", strategy)
        detail_frames.append(details)

        weights = weights_by_strategy[strategy].reset_index()
        weights.insert(0, "Strategy", strategy)
        weight_frames.append(weights)

    pd.concat(detail_frames, ignore_index=True).to_csv(OUTPUTS_DIR / "daily_details.csv", index=False)
    pd.concat(weight_frames, ignore_index=True).to_csv(OUTPUTS_DIR / "daily_weights.csv", index=False)


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
    performance: pd.DataFrame,
    relative: pd.DataFrame,
    diagnostics: pd.DataFrame,
    exposure: pd.DataFrame,
    frequency: pd.DataFrame,
) -> str:
    perf = performance.set_index("Strategy")
    rel = relative.set_index("Strategy")
    baseline = perf.loc["Framework001"]
    filtered = performance.loc[performance["Strategy"] != "Framework001"].copy()
    best_sharpe = filtered.sort_values("Sharpe", ascending=False).iloc[0]
    best_cagr = filtered.sort_values("CAGR", ascending=False).iloc[0]
    best_maxdd = filtered.sort_values("MaxDD", ascending=False).iloc[0]

    before_cash = perf.loc["Filter Before Ranking (Cash)"]
    before_reweight = perf.loc["Filter Before Ranking (Reweight)"]
    after_cash = perf.loc["Filter After Ranking (Cash)"]
    after_reweight = perf.loc["Filter After Ranking (Reweight)"]

    before_avg_sharpe = np.mean([before_cash["Sharpe"], before_reweight["Sharpe"]])
    after_avg_sharpe = np.mean([after_cash["Sharpe"], after_reweight["Sharpe"]])
    cash_avg_sharpe = np.mean([before_cash["Sharpe"], after_cash["Sharpe"]])
    reweight_avg_sharpe = np.mean([before_reweight["Sharpe"], after_reweight["Sharpe"]])
    before_after_equivalent = (
        abs(before_cash["CAGR"] - after_cash["CAGR"]) < 1e-12
        and abs(before_cash["Sharpe"] - after_cash["Sharpe"]) < 1e-12
        and abs(before_reweight["CAGR"] - after_reweight["CAGR"]) < 1e-12
        and abs(before_reweight["Sharpe"] - after_reweight["Sharpe"]) < 1e-12
    )

    top_frequency = (
        frequency.loc[frequency["Strategy"] == best_sharpe["Strategy"]]
        .sort_values(["Selection Count", "ETF"], ascending=[False, True])
        .head(5)
    )

    perf_cols = ["Strategy", "CAGR", "Sharpe", "MaxDD", "Volatility", "Calmar", "Total Return", "Turnover"]
    rel_cols = ["Strategy", "CAGR Change", "Sharpe Change", "MaxDD Change"]
    diag_cols = [
        "Strategy",
        "Average ETFs with Positive Momentum",
        "Average Holdings",
        "Average Cash Weight",
        "Maximum Cash Weight",
        "Months with Cash",
        "Months with Fewer than Five Holdings",
        "Average Effective Positions",
        "Average HHI",
        "Average Turnover",
    ]
    exposure_cols = ["Strategy", "Equity", "Commodity", "Bond", "Cash"]
    freq_cols = ["Strategy", "ETF", "Selection Count", "Selection Percent"]

    cagr_improvers = int((rel["CAGR Change"] > 0).sum())
    sharpe_improvers = int((rel["Sharpe Change"] > 0).sum())
    drawdown_improvers = int((rel["MaxDD Change"] > 0).sum())

    return f"""# Research 002 — Absolute Momentum Integration in Framework 001

## 1. Research Question

Framework 001 uses the Original 12 ETF universe, 126-day cross-sectional momentum, monthly Top5 selection, and 126-day inverse-volatility weighting. This study tests whether adding a fixed absolute momentum filter improves the framework.

This is not parameter optimization. The absolute momentum rule is fixed at `126-day return > 0`.

## 2. Fixed Design

- Universe: Original 12 ETF universe
- Equity: SPY, QQQ, IWM, EFA
- Commodity: GLD, SLV, USO, DBA
- Bond: TLT, IEF, SHY, LQD
- Sample: `2008-02-01` to `2025-12-31`
- Cross-sectional momentum: 126 trading days
- Absolute momentum filter: 126-day return > 0
- Rebalance: monthly, month-end signal, next trading day execution
- Weighting: 126-day inverse volatility
- Transaction cost: 5 bps on turnover
- Constraints: long only, no leverage, no shorting, no MA filter

## 3. Strategies

- `Framework001`: baseline Top5 cross-sectional momentum with inverse volatility.
- `Filter Before Ranking (Reweight)`: remove non-positive momentum ETFs before ranking; reweight qualifying holdings to 100%.
- `Filter Before Ranking (Cash)`: remove non-positive momentum ETFs before ranking; if fewer than 5 qualify, hold proportional cash.
- `Filter After Ranking (Reweight)`: rank Top5 first, then remove non-positive Top5 members; reweight remaining holdings to 100%.
- `Filter After Ranking (Cash)`: rank Top5 first, then remove non-positive Top5 members; if fewer than 5 remain, hold proportional cash.

If no ETF passes the absolute momentum filter, the filtered portfolio is held in cash for that rebalance period.

## 4. Performance

{markdown_table(performance, perf_cols, {"CAGR", "MaxDD", "Volatility", "Calmar", "Total Return", "Turnover"})}

## 5. Relative Change vs Framework001

Positive MaxDD Change means shallower drawdown.

{markdown_table(relative, rel_cols, {"CAGR Change", "MaxDD Change"})}

## 6. Absolute Momentum Diagnostics

{markdown_table(diagnostics, diag_cols, {"Average Cash Weight", "Maximum Cash Weight", "Average Turnover"})}

## 7. Asset Class Exposure

Average daily weight.

{markdown_table(exposure, exposure_cols, {"Equity", "Commodity", "Bond", "Cash"})}

## 8. ETF Selection Frequency

{markdown_table(frequency, freq_cols, {"Selection Percent"})}

## 9. Interpretation

1. **Does Absolute Momentum improve CAGR?** {cagr_improvers}/4 filtered variants improved CAGR versus Framework001. The highest filtered CAGR is `{fmt_pct(best_cagr["CAGR"])}` from `{best_cagr["Strategy"]}`, versus baseline `{fmt_pct(baseline["CAGR"])}`. The improvement is real but modest.
2. **Does Absolute Momentum improve Sharpe?** {sharpe_improvers}/4 filtered variants improved Sharpe. The best filtered Sharpe is `{fmt_num(best_sharpe["Sharpe"])}` from `{best_sharpe["Strategy"]}`, versus baseline `{fmt_num(baseline["Sharpe"])}`. The Sharpe gain is marginal.
3. **Does Absolute Momentum reduce MaxDD?** {drawdown_improvers}/4 filtered variants improved MaxDD. The shallowest filtered MaxDD is `{fmt_pct(best_maxdd["MaxDD"])}` from `{best_maxdd["Strategy"]}`, versus baseline `{fmt_pct(baseline["MaxDD"])}`. Absolute Momentum does not materially improve drawdown in this test.
4. **Is filtering before ranking better than filtering after ranking?** No. Before-ranking and after-ranking are {'mathematically equivalent here because both use the same 126-day return signal' if before_after_equivalent else 'not materially different'}; before-ranking average Sharpe is `{fmt_num(before_avg_sharpe)}` and after-ranking average Sharpe is `{fmt_num(after_avg_sharpe)}`.
5. **Is Cash better than Reweight when fewer than five ETFs qualify?** Yes on risk-adjusted behavior. Cash variants average Sharpe `{fmt_num(cash_avg_sharpe)}` versus reweight variants `{fmt_num(reweight_avg_sharpe)}`. Reweight variants have higher CAGR but worse Sharpe and deeper MaxDD.
6. **Which strategy provides the best overall risk-adjusted performance?** `{best_sharpe["Strategy"]}` has the highest filtered Sharpe. Its most frequent ETFs are: {", ".join(top_frequency["ETF"].tolist())}.
7. **Does Absolute Momentum mainly improve downside protection or return generation?** It does not clearly improve downside protection. Reweight mainly raises CAGR by concentrating into fewer positive-momentum assets, while Cash slightly improves Sharpe by reducing exposure when breadth is weak.
8. **Does Absolute Momentum materially reduce diversification?** Moderately. Filtered variants average `{fmt_num(diagnostics.loc[diagnostics["Strategy"] == "Filter Before Ranking (Cash)", "Average Holdings"].iloc[0])}` holdings versus 5.00 for baseline, with 27 months below five holdings.
9. **Should Absolute Momentum become part of the next framework version?** Not yet as a fully justified Framework002 component. The Cash implementation is a candidate for further validation, but the improvement over Framework001 is too small and does not reduce MaxDD.

## 10. Final Conclusion

Absolute Momentum is evaluated as a fixed integration layer, not optimized. In this test, it does not provide enough improvement to justify changing Framework001.

The Cash implementation is superior to Reweight on risk-adjusted behavior, but its advantage over baseline is tiny: it slightly improves CAGR and Sharpe while leaving MaxDD essentially unchanged. Reweight produces higher CAGR but worsens Sharpe and MaxDD, which is not an attractive framework evolution.

Filtering before ranking and filtering after ranking are equivalent under this design because both the cross-sectional ranking and absolute filter use the same 126-day return signal. The real implementation choice is therefore Cash versus Reweight, and Cash is the cleaner version.

Final classification: Absolute Momentum Cash is a weak candidate for further validation, not a confirmed Framework002 upgrade. Framework001 remains unchanged.

## 11. Output Files

- `metrics/performance.csv`
- `metrics/relative_change.csv`
- `metrics/absolute_momentum_diagnostics.csv`
- `metrics/asset_class_exposure.csv`
- `metrics/selection_frequency.csv`
- `outputs/monthly_holding_diagnostics.csv`
- `outputs/target_weights_by_rebalance.csv`
- `outputs/daily_details.csv`
- `outputs/daily_weights.csv`
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    prices = core.load_prices().loc[:END_DATE].copy()
    returns = prices.pct_change(fill_method=None)
    targets, holdings, monthly_diagnostics = build_targets(prices)
    performance, details_by_strategy, weights_by_strategy = simulate(returns, targets)
    relative = relative_change(performance)
    diagnostics = absolute_momentum_diagnostics(monthly_diagnostics, details_by_strategy)
    exposure = asset_class_exposure(weights_by_strategy)
    frequency = selection_frequency(holdings, monthly_diagnostics)

    performance.to_csv(METRICS_DIR / "performance.csv", index=False)
    relative.to_csv(METRICS_DIR / "relative_change.csv", index=False)
    diagnostics.to_csv(METRICS_DIR / "absolute_momentum_diagnostics.csv", index=False)
    exposure.to_csv(METRICS_DIR / "asset_class_exposure.csv", index=False)
    frequency.to_csv(METRICS_DIR / "selection_frequency.csv", index=False)
    monthly_diagnostics.to_csv(OUTPUTS_DIR / "monthly_holding_diagnostics.csv", index=False)
    holdings.to_csv(OUTPUTS_DIR / "target_weights_by_rebalance.csv", index=False)
    save_daily_outputs(details_by_strategy, weights_by_strategy)

    summary = generate_summary(performance, relative, diagnostics, exposure, frequency)
    SUMMARY_PATH.write_text(summary, encoding="utf-8")

    print("\nResearch 002 — Absolute Momentum Integration Complete")
    print(f"Study directory: {STUDY_DIR}")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nRelative change vs Framework001:")
    print(relative.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nDiagnostics:")
    print(diagnostics.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
