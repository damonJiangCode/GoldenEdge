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


MOMENTUM_WINDOWS = [63, 126, 252]
BASELINE_WINDOW = 126
VOLATILITY_WINDOW = 126
TOP_N = 5
START_DATE = pd.Timestamp("2008-02-01")
END_DATE = pd.Timestamp("2025-12-31")
STRATEGY_ORDER = ["Framework001 Baseline", "Momentum Ensemble"]
BASELINE = "Framework001 Baseline"
ENSEMBLE = "Momentum Ensemble"

ASSET_CLASS_BY_SYMBOL = {
    symbol: asset_class for asset_class, symbols in MIXED_ASSET_CLASSES.items() for symbol in symbols
}


def normalized(values: np.ndarray) -> np.ndarray:
    if not np.isfinite(values).all() or (values <= 0).any():
        raise RuntimeError(f"Invalid inverse-volatility inputs: {values}")
    return values / values.sum()


def build_targets(prices: pd.DataFrame) -> tuple[dict[str, dict[pd.Timestamp, pd.Series]], pd.DataFrame, pd.DataFrame]:
    returns = prices.pct_change(fill_method=None)
    momentum = {window: prices / prices.shift(window) - 1 for window in MOMENTUM_WINDOWS}
    trailing_vol = returns.rolling(VOLATILITY_WINDOW, min_periods=VOLATILITY_WINDOW).std(ddof=1)
    targets = {strategy: {} for strategy in STRATEGY_ORDER}
    holding_rows = []
    overlap_rows = []

    for rebalance_date in core.month_end_dates(prices.index):
        if rebalance_date > END_DATE:
            continue
        location = prices.index.get_loc(rebalance_date)
        if location + 1 >= len(prices.index):
            continue
        effective_date = prices.index[location + 1]
        if effective_date < START_DATE or effective_date > END_DATE:
            continue

        scores = {window: momentum[window].loc[rebalance_date].dropna() for window in MOMENTUM_WINDOWS}
        volatility = trailing_vol.loc[rebalance_date].dropna()
        if any(len(frame) != len(prices.columns) for frame in scores.values()) or len(volatility) != len(prices.columns):
            continue

        rank_frame = pd.DataFrame(
            {
                f"Rank{window}": scores[window].rank(ascending=False, method="first")
                for window in MOMENTUM_WINDOWS
            }
        )
        rank_frame["Average Rank"] = rank_frame[[f"Rank{window}" for window in MOMENTUM_WINDOWS]].mean(axis=1)
        baseline_selected = scores[BASELINE_WINDOW].sort_values(ascending=False).head(TOP_N).index.tolist()
        ensemble_selected = rank_frame.sort_values(["Average Rank", "Rank126", "Rank63"]).head(TOP_N).index.tolist()

        selected_by_strategy = {
            BASELINE: baseline_selected,
            ENSEMBLE: ensemble_selected,
        }

        for strategy, selected in selected_by_strategy.items():
            weights = normalized(1.0 / volatility.loc[selected].to_numpy(dtype=float))
            target = pd.Series(0.0, index=prices.columns)
            target.loc[selected] = weights
            targets[strategy][effective_date] = target
            for rank, symbol in enumerate(selected, start=1):
                holding_rows.append(
                    {
                        "Strategy": strategy,
                        "Rebalance Date": rebalance_date,
                        "Effective Date": effective_date,
                        "ETF": symbol,
                        "Asset Class": ASSET_CLASS_BY_SYMBOL[symbol],
                        "Selection Rank": rank,
                        "Rank63": rank_frame.loc[symbol, "Rank63"],
                        "Rank126": rank_frame.loc[symbol, "Rank126"],
                        "Rank252": rank_frame.loc[symbol, "Rank252"],
                        "Average Rank": rank_frame.loc[symbol, "Average Rank"],
                        "Momentum63": scores[63].loc[symbol],
                        "Momentum126": scores[126].loc[symbol],
                        "Momentum252": scores[252].loc[symbol],
                        "Volatility": volatility.loc[symbol],
                        "Weight": target.loc[symbol],
                    }
                )

        overlap = len(set(baseline_selected).intersection(ensemble_selected))
        overlap_rows.append(
            {
                "Rebalance Date": rebalance_date,
                "Effective Date": effective_date,
                "Framework001 Selected": ", ".join(baseline_selected),
                "Ensemble Selected": ", ".join(ensemble_selected),
                "Overlap Count": overlap,
                "Overlap Percent": overlap / TOP_N,
            }
        )

    return targets, pd.DataFrame(holding_rows), pd.DataFrame(overlap_rows)


def simulate(
    returns: pd.DataFrame,
    targets: dict[str, dict[pd.Timestamp, pd.Series]],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    rows = []
    details_by_strategy = {}
    weights_by_strategy = {}
    for strategy in STRATEGY_ORDER:
        details, weights = core.simulate_monthly_holdings(returns, targets[strategy])
        details = details.loc[START_DATE:END_DATE].copy()
        weights = weights.loc[START_DATE:END_DATE].copy()
        if details.index.min() != START_DATE:
            raise RuntimeError(f"{strategy}: unexpected start date {details.index.min()}")

        equity = (1 + details["return"]).cumprod()
        metrics = core.calculate_metrics(
            label=strategy,
            momentum_window="ensemble" if strategy == ENSEMBLE else "mom_126",
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
    baseline = performance.set_index("Strategy").loc[BASELINE]
    result = performance.loc[performance["Strategy"] == ENSEMBLE, ["Strategy", "CAGR", "Sharpe", "MaxDD"]].copy()
    result["CAGR Change"] = result["CAGR"] - baseline["CAGR"]
    result["Sharpe Change"] = result["Sharpe"] - baseline["Sharpe"]
    result["MaxDD Change"] = result["MaxDD"] - baseline["MaxDD"]
    return result[["Strategy", "CAGR Change", "Sharpe Change", "MaxDD Change"]]


def ensemble_diagnostics(
    holdings: pd.DataFrame,
    targets: dict[str, dict[pd.Timestamp, pd.Series]],
    details_by_strategy: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    part = holdings.loc[holdings["Strategy"] == ENSEMBLE].copy()
    hhi_values = []
    effective_values = []
    for target in targets[ENSEMBLE].values():
        weights = target[target > 0]
        hhi = float((weights**2).sum())
        hhi_values.append(hhi)
        effective_values.append(1.0 / hhi)
    details = details_by_strategy[ENSEMBLE]
    rebalance_turnover = details.loc[details["turnover"] > 0, "turnover"]
    rows = [
        {"Metric": "Average Rank63 of selected ETFs", "Value": part["Rank63"].mean()},
        {"Metric": "Average Rank126 of selected ETFs", "Value": part["Rank126"].mean()},
        {"Metric": "Average Rank252 of selected ETFs", "Value": part["Rank252"].mean()},
        {"Metric": "Average Ensemble Rank", "Value": part["Average Rank"].mean()},
        {"Metric": "Average Turnover", "Value": rebalance_turnover.mean()},
        {"Metric": "Average Effective Positions", "Value": np.mean(effective_values)},
        {"Metric": "Average HHI", "Value": np.mean(hhi_values)},
    ]
    return pd.DataFrame(rows)


def selection_overlap(overlap_rows: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {"Metric": "Average Overlap Count", "Value": overlap_rows["Overlap Count"].mean()},
        {"Metric": "Average Overlap Percent", "Value": overlap_rows["Overlap Percent"].mean()},
        {"Metric": "Months with Same Top5", "Value": int((overlap_rows["Overlap Count"] == 5).sum())},
        {"Metric": "Months with 4/5 Overlap", "Value": int((overlap_rows["Overlap Count"] == 4).sum())},
        {"Metric": "Months with 3/5 or Less Overlap", "Value": int((overlap_rows["Overlap Count"] <= 3).sum())},
    ]
    return pd.DataFrame(rows)


def asset_class_exposure(weights_by_strategy: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for strategy in STRATEGY_ORDER:
        weights = weights_by_strategy[strategy]
        row = {"Strategy": strategy}
        for asset_class, symbols in MIXED_ASSET_CLASSES.items():
            row[asset_class] = weights[symbols].sum(axis=1).mean()
        rows.append(row)
    return pd.DataFrame(rows)


def selection_frequency(holdings: pd.DataFrame) -> pd.DataFrame:
    total_rebalances = holdings.groupby("Strategy")["Effective Date"].nunique().to_dict()
    result = pd.DataFrame({"ETF": MIXED_ASSET_SYMBOLS})
    for strategy in STRATEGY_ORDER:
        counts = (
            holdings.loc[holdings["Strategy"] == strategy]
            .groupby("ETF")["Effective Date"]
            .nunique()
            .reindex(MIXED_ASSET_SYMBOLS, fill_value=0)
        )
        result[f"{strategy} Selection Percent"] = result["ETF"].map((counts / total_rebalances[strategy]).to_dict())
    return result


def save_daily_outputs(
    details_by_strategy: dict[str, pd.DataFrame],
    weights_by_strategy: dict[str, pd.DataFrame],
) -> None:
    detail_frames = []
    weight_frames = []
    for strategy in STRATEGY_ORDER:
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


def metric_value(df: pd.DataFrame, metric: str) -> float:
    return float(df.loc[df["Metric"] == metric, "Value"].iloc[0])


def generate_summary(
    performance: pd.DataFrame,
    relative: pd.DataFrame,
    diagnostics: pd.DataFrame,
    overlap: pd.DataFrame,
    exposure: pd.DataFrame,
    frequency: pd.DataFrame,
) -> str:
    perf = performance.set_index("Strategy")
    baseline = perf.loc[BASELINE]
    ensemble = perf.loc[ENSEMBLE]
    rel = relative.iloc[0]
    overlap_count = metric_value(overlap, "Average Overlap Count")
    overlap_percent = metric_value(overlap, "Average Overlap Percent")
    same_top5 = int(metric_value(overlap, "Months with Same Top5"))
    three_or_less = int(metric_value(overlap, "Months with 3/5 or Less Overlap"))

    ensemble_freq_col = f"{ENSEMBLE} Selection Percent"
    baseline_freq_col = f"{BASELINE} Selection Percent"
    beneficiaries = frequency.copy()
    beneficiaries["Selection Change"] = beneficiaries[ensemble_freq_col] - beneficiaries[baseline_freq_col]
    top_beneficiaries = beneficiaries.sort_values("Selection Change", ascending=False).head(3)
    diagnostics_display = diagnostics.copy()
    diagnostics_display["Display Value"] = diagnostics_display.apply(
        lambda row: fmt_pct(row["Value"])
        if row["Metric"] == "Average Turnover"
        else fmt_num(row["Value"]),
        axis=1,
    )
    overlap_display = overlap.copy()
    overlap_display["Display Value"] = overlap_display.apply(
        lambda row: fmt_pct(row["Value"])
        if row["Metric"] == "Average Overlap Percent"
        else str(int(row["Value"]))
        if row["Metric"].startswith("Months")
        else fmt_num(row["Value"]),
        axis=1,
    )

    if ensemble["Sharpe"] > baseline["Sharpe"] and ensemble["MaxDD"] > baseline["MaxDD"]:
        conclusion = "The ensemble improves risk-adjusted performance and drawdown, making it a serious Framework002 candidate."
    elif ensemble["Sharpe"] > baseline["Sharpe"] or ensemble["MaxDD"] > baseline["MaxDD"]:
        conclusion = "The ensemble improves one risk metric but not enough dimensions to replace the simpler 126-day signal."
    else:
        conclusion = "The ensemble does not improve Framework001 enough to justify replacing the 126-day signal."

    perf_cols = ["Strategy", "CAGR", "Sharpe", "MaxDD", "Volatility", "Calmar", "Total Return", "Turnover"]
    rel_cols = ["Strategy", "CAGR Change", "Sharpe Change", "MaxDD Change"]
    exposure_cols = ["Strategy", "Equity", "Commodity", "Bond"]
    freq_cols = ["ETF", baseline_freq_col, ensemble_freq_col]

    return f"""# Research 004 — Momentum Ensemble in Framework001

## 1. Research Question

Framework001 currently uses a single 126-day cross-sectional momentum signal. This study tests one predefined ensemble signal based on average rank across 63-day, 126-day, and 252-day momentum.

No horizon optimization is performed. The inverse-volatility sizing rule is unchanged.

## 2. Fixed Design

- Universe: Original 12 ETF universe
- Equity: SPY, QQQ, IWM, EFA
- Commodity: GLD, SLV, USO, DBA
- Bond: TLT, IEF, SHY, LQD
- Sample: `2008-02-01` to `2025-12-31`
- Rebalance: monthly
- Signal date: month-end
- Execution: next trading day
- Transaction cost: 5 bps
- Constraints: long only, no leverage, no shorting, no MA filter
- Weighting: 126-day inverse volatility

## 3. Strategies

- `Framework001 Baseline`: Top5 by 126-day momentum rank, then 126-day inverse-volatility weighting.
- `Momentum Ensemble`: Top5 by lowest average rank across 63-day, 126-day, and 252-day momentum ranks, then 126-day inverse-volatility weighting.

## 4. Performance

{markdown_table(performance, perf_cols, {"CAGR", "MaxDD", "Volatility", "Calmar", "Total Return", "Turnover"})}

## 5. Relative Change vs Framework001

Positive MaxDD Change means shallower drawdown.

{markdown_table(relative, rel_cols, {"CAGR Change", "MaxDD Change"})}

## 6. Ensemble Diagnostics

{markdown_table(diagnostics_display, ["Metric", "Display Value"], set())}

## 7. Selection Overlap

{markdown_table(overlap_display, ["Metric", "Display Value"], set())}

## 8. Asset Class Exposure

Average daily portfolio weight.

{markdown_table(exposure, exposure_cols, {"Equity", "Commodity", "Bond"})}

## 9. ETF Selection Frequency

{markdown_table(frequency, freq_cols, {baseline_freq_col, ensemble_freq_col})}

## 10. Interpretation

1. **Does Momentum Ensemble improve CAGR?** {'Yes' if ensemble["CAGR"] > baseline["CAGR"] else 'No'}. Ensemble CAGR is `{fmt_pct(ensemble["CAGR"])}` versus baseline `{fmt_pct(baseline["CAGR"])}`.
2. **Does Momentum Ensemble improve Sharpe?** {'Yes' if ensemble["Sharpe"] > baseline["Sharpe"] else 'No'}. Ensemble Sharpe is `{fmt_num(ensemble["Sharpe"])}` versus baseline `{fmt_num(baseline["Sharpe"])}`.
3. **Does Momentum Ensemble reduce MaxDD?** {'Yes' if ensemble["MaxDD"] > baseline["MaxDD"] else 'No'}. Ensemble MaxDD is `{fmt_pct(ensemble["MaxDD"])}` versus baseline `{fmt_pct(baseline["MaxDD"])}`.
4. **Does Ensemble reduce turnover?** {'Yes' if ensemble["Turnover"] < baseline["Turnover"] else 'No'}. Ensemble turnover is `{fmt_pct(ensemble["Turnover"])}` versus baseline `{fmt_pct(baseline["Turnover"])}`.
5. **Does Ensemble materially change holdings versus 126-day momentum?** Average overlap is `{fmt_num(overlap_count)}/5`, or `{fmt_pct(overlap_percent)}`. Same Top5 occurred in `{same_top5}` months; 3/5 or less overlap occurred in `{three_or_less}` months.
6. **Does Ensemble create more stable selections or just dilute the 126-day signal?** The answer depends on whether lower turnover comes with better Sharpe and MaxDD. Here, the relative table is the decisive evidence.
7. **Which assets benefit most from Ensemble selection?** Largest selection-frequency increases are: {", ".join(top_beneficiaries["ETF"].tolist())}.
8. **Should Ensemble replace 126-day momentum in Framework001?** {conclusion}

## 11. Final Conclusion

{conclusion}

This study only tests the predefined 63/126/252 average-rank ensemble. It does not search other horizon combinations, does not change inverse-volatility sizing, and does not introduce filters.

Framework001 should only be updated if the ensemble delivers a meaningful improvement across CAGR, Sharpe, MaxDD, and turnover. Otherwise, the single 126-day signal remains the cleaner framework component.

## 12. Output Files

- `metrics/performance.csv`
- `metrics/relative_change.csv`
- `metrics/ensemble_diagnostics.csv`
- `metrics/selection_overlap.csv`
- `metrics/asset_class_exposure.csv`
- `metrics/selection_frequency.csv`
- `outputs/monthly_holding_diagnostics.csv`
- `outputs/selection_overlap_by_rebalance.csv`
- `outputs/daily_weights.csv`
- `outputs/daily_details.csv`
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    prices = core.load_prices().loc[:END_DATE].copy()
    returns = prices.pct_change(fill_method=None)
    targets, holdings, overlap_rows = build_targets(prices)
    performance, details_by_strategy, weights_by_strategy = simulate(returns, targets)
    relative = relative_change(performance)
    diagnostics = ensemble_diagnostics(holdings, targets, details_by_strategy)
    overlap = selection_overlap(overlap_rows)
    exposure = asset_class_exposure(weights_by_strategy)
    frequency = selection_frequency(holdings)

    performance.to_csv(METRICS_DIR / "performance.csv", index=False)
    relative.to_csv(METRICS_DIR / "relative_change.csv", index=False)
    diagnostics.to_csv(METRICS_DIR / "ensemble_diagnostics.csv", index=False)
    overlap.to_csv(METRICS_DIR / "selection_overlap.csv", index=False)
    exposure.to_csv(METRICS_DIR / "asset_class_exposure.csv", index=False)
    frequency.to_csv(METRICS_DIR / "selection_frequency.csv", index=False)
    holdings.to_csv(OUTPUTS_DIR / "monthly_holding_diagnostics.csv", index=False)
    overlap_rows.to_csv(OUTPUTS_DIR / "selection_overlap_by_rebalance.csv", index=False)
    save_daily_outputs(details_by_strategy, weights_by_strategy)

    summary = generate_summary(performance, relative, diagnostics, overlap, exposure, frequency)
    SUMMARY_PATH.write_text(summary, encoding="utf-8")

    print("\nResearch 004 — Momentum Ensemble Complete")
    print(f"Study directory: {STUDY_DIR}")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nRelative change vs Framework001:")
    print(relative.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nSelection overlap:")
    print(overlap.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
