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
START_DATE = pd.Timestamp("2008-02-01")
END_DATE = pd.Timestamp("2025-12-31")
TOP_N_BY_STRATEGY = {
    "Top3": 3,
    "Framework001 (Top5)": 5,
    "Top7": 7,
}
STRATEGY_ORDER = ["Top3", "Framework001 (Top5)", "Top7"]
BASELINE = "Framework001 (Top5)"

ASSET_CLASS_BY_SYMBOL = {
    symbol: asset_class for asset_class, symbols in MIXED_ASSET_CLASSES.items() for symbol in symbols
}


def normalized(values: np.ndarray) -> np.ndarray:
    if not np.isfinite(values).all() or (values <= 0).any():
        raise RuntimeError(f"Invalid inverse-volatility inputs: {values}")
    return values / values.sum()


def build_targets(prices: pd.DataFrame) -> tuple[dict[str, dict[pd.Timestamp, pd.Series]], pd.DataFrame]:
    returns = prices.pct_change(fill_method=None)
    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    trailing_vol = returns.rolling(VOLATILITY_WINDOW, min_periods=VOLATILITY_WINDOW).std(ddof=1)
    targets = {strategy: {} for strategy in STRATEGY_ORDER}
    holding_rows = []

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
        for strategy, top_n in TOP_N_BY_STRATEGY.items():
            selected = ranked_all.head(top_n).index.tolist()
            weights = normalized(1.0 / volatility.loc[selected].to_numpy(dtype=float))
            target = pd.Series(0.0, index=prices.columns)
            target.loc[selected] = weights
            targets[strategy][effective_date] = target
            for rank, symbol in enumerate(selected, start=1):
                holding_rows.append(
                    {
                        "Strategy": strategy,
                        "Top N": top_n,
                        "Rebalance Date": rebalance_date,
                        "Effective Date": effective_date,
                        "ETF": symbol,
                        "Asset Class": ASSET_CLASS_BY_SYMBOL[symbol],
                        "Momentum Rank": rank,
                        "Momentum Return": ranked_all.loc[symbol],
                        "Volatility": volatility.loc[symbol],
                        "Weight": target.loc[symbol],
                    }
                )

    return targets, pd.DataFrame(holding_rows)


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
    baseline = performance.set_index("Strategy").loc[BASELINE]
    result = performance.loc[performance["Strategy"] != BASELINE, ["Strategy", "CAGR", "Sharpe", "MaxDD"]].copy()
    result["CAGR Change"] = result["CAGR"] - baseline["CAGR"]
    result["Sharpe Change"] = result["Sharpe"] - baseline["Sharpe"]
    result["MaxDD Change"] = result["MaxDD"] - baseline["MaxDD"]
    return result[["Strategy", "CAGR Change", "Sharpe Change", "MaxDD Change"]]


def portfolio_diagnostics(
    targets: dict[str, dict[pd.Timestamp, pd.Series]],
    details_by_strategy: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    rows = []
    for strategy in STRATEGY_ORDER:
        hhi_values = []
        effective_values = []
        holding_values = []
        for target in targets[strategy].values():
            weights = target[target > 0]
            hhi = float((weights**2).sum())
            hhi_values.append(hhi)
            effective_values.append(1.0 / hhi)
            holding_values.append(len(weights))
        details = details_by_strategy[strategy]
        rebalance_turnover = details.loc[details["turnover"] > 0, "turnover"]
        rows.append(
            {
                "Strategy": strategy,
                "Average Holdings": np.mean(holding_values),
                "Average Effective Positions": np.mean(effective_values),
                "Average HHI": np.mean(hhi_values),
                "Average Turnover": rebalance_turnover.mean(),
            }
        )
    return pd.DataFrame(rows)


def position_weight_diagnostics(holdings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    max_rank = max(TOP_N_BY_STRATEGY.values())
    for strategy in STRATEGY_ORDER:
        part = holdings.loc[holdings["Strategy"] == strategy]
        row = {"Strategy": strategy}
        rank_means = part.groupby("Momentum Rank")["Weight"].mean()
        for rank in range(1, max_rank + 1):
            row[f"Rank{rank}"] = rank_means.get(rank, np.nan)
        rows.append(row)
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
    counts_by_strategy = {}
    total_rebalances = holdings.groupby("Strategy")["Effective Date"].nunique().to_dict()
    for strategy in STRATEGY_ORDER:
        counts = (
            holdings.loc[holdings["Strategy"] == strategy]
            .groupby("ETF")["Effective Date"]
            .nunique()
            .reindex(MIXED_ASSET_SYMBOLS, fill_value=0)
        )
        counts_by_strategy[strategy] = counts / total_rebalances[strategy]
    result = pd.DataFrame({"ETF": MIXED_ASSET_SYMBOLS})
    for strategy in STRATEGY_ORDER:
        result[strategy] = result["ETF"].map(counts_by_strategy[strategy].to_dict())
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


def generate_summary(
    performance: pd.DataFrame,
    relative: pd.DataFrame,
    diagnostics: pd.DataFrame,
    weights_by_rank: pd.DataFrame,
    exposure: pd.DataFrame,
    frequency: pd.DataFrame,
) -> str:
    perf = performance.set_index("Strategy")
    diag = diagnostics.set_index("Strategy")
    top3 = perf.loc["Top3"]
    top5 = perf.loc["Framework001 (Top5)"]
    top7 = perf.loc["Top7"]
    best_sharpe = performance.sort_values("Sharpe", ascending=False).iloc[0]
    best_maxdd = performance.sort_values("MaxDD", ascending=False).iloc[0]
    best_cagr = performance.sort_values("CAGR", ascending=False).iloc[0]

    perf_cols = ["Strategy", "CAGR", "Sharpe", "MaxDD", "Volatility", "Calmar", "Total Return", "Turnover"]
    rel_cols = ["Strategy", "CAGR Change", "Sharpe Change", "MaxDD Change"]
    diag_cols = ["Strategy", "Average Holdings", "Average Effective Positions", "Average HHI", "Average Turnover"]
    rank_cols = ["Strategy", "Rank1", "Rank2", "Rank3", "Rank4", "Rank5", "Rank6", "Rank7"]
    exposure_cols = ["Strategy", "Equity", "Commodity", "Bond"]
    frequency_cols = ["ETF", "Top3", "Framework001 (Top5)", "Top7"]

    if best_sharpe["Strategy"] == BASELINE and best_cagr["Strategy"] == BASELINE:
        recommendation = "Top5 remains the strongest overall choice."
    elif best_sharpe["Strategy"] == BASELINE:
        recommendation = "Top5 remains the best risk-adjusted choice despite another variant leading one secondary metric."
    else:
        recommendation = (
            f"{best_sharpe['Strategy']} leads Sharpe, but framework migration requires judging whether the "
            "gain is large and consistent across CAGR and drawdown."
        )

    return f"""# Research 003 — Number of Holdings in Framework001

## 1. Research Question

Framework001 currently uses monthly Top5 cross-sectional momentum selection with 126-day inverse-volatility weighting. This study tests whether changing the selected ETF count to Top3 or Top7 improves the framework.

Only the number of holdings changes. Universe, signal window, rebalance schedule, inverse-volatility window, costs, and constraints remain fixed.

## 2. Fixed Design

- Universe: Original 12 ETF universe
- Equity: SPY, QQQ, IWM, EFA
- Commodity: GLD, SLV, USO, DBA
- Bond: TLT, IEF, SHY, LQD
- Sample: `2008-02-01` to `2025-12-31`
- Cross-sectional momentum: 126 trading days
- Rebalance: monthly, month-end signal, next trading day execution
- Weighting: 126-day inverse volatility
- Transaction cost: 5 bps
- Constraints: long only, no leverage, no shorting, no MA filter

## 3. Strategies

- `Top3`: Top3 cross-sectional momentum with inverse-volatility weighting.
- `Framework001 (Top5)`: current baseline.
- `Top7`: Top7 cross-sectional momentum with inverse-volatility weighting.

## 4. Performance

{markdown_table(performance, perf_cols, {"CAGR", "MaxDD", "Volatility", "Calmar", "Total Return", "Turnover"})}

## 5. Relative Change vs Framework001

Positive MaxDD Change means shallower drawdown.

{markdown_table(relative, rel_cols, {"CAGR Change", "MaxDD Change"})}

## 6. Portfolio Diagnostics

{markdown_table(diagnostics, diag_cols, {"Average Turnover"})}

## 7. Position Weight Diagnostics

Average weight by momentum rank.

{markdown_table(weights_by_rank, rank_cols, {"Rank1", "Rank2", "Rank3", "Rank4", "Rank5", "Rank6", "Rank7"})}

## 8. Asset Class Exposure

Average daily portfolio weight.

{markdown_table(exposure, exposure_cols, {"Equity", "Commodity", "Bond"})}

## 9. ETF Selection Frequency

Selection Percent = selected rebalances / total rebalances.

{markdown_table(frequency, frequency_cols, {"Top3", "Framework001 (Top5)", "Top7"})}

## 10. Interpretation

1. **Does reducing holdings to Top3 improve CAGR?** {'Yes' if top3["CAGR"] > top5["CAGR"] else 'No'}. Top3 CAGR is `{fmt_pct(top3["CAGR"])}` versus Top5 `{fmt_pct(top5["CAGR"])}`.
2. **Does Top3 sacrifice diversification for concentration?** Yes. Top3 effective positions average `{fmt_num(diag.loc["Top3", "Average Effective Positions"])}` versus Top5 `{fmt_num(diag.loc[BASELINE, "Average Effective Positions"])}`.
3. **Does increasing holdings to Top7 reduce volatility?** {'Yes' if top7["Volatility"] < top5["Volatility"] else 'No'}. Top7 volatility is `{fmt_pct(top7["Volatility"])}` versus Top5 `{fmt_pct(top5["Volatility"])}`.
4. **Does Top7 dilute momentum enough to reduce returns?** {'Yes' if top7["CAGR"] < top5["CAGR"] else 'No'}. Top7 CAGR is `{fmt_pct(top7["CAGR"])}` versus Top5 `{fmt_pct(top5["CAGR"])}`.
5. **Which holding count produces the highest Sharpe?** `{best_sharpe["Strategy"]}` with Sharpe `{fmt_num(best_sharpe["Sharpe"])}`.
6. **Which holding count produces the shallowest MaxDD?** `{best_maxdd["Strategy"]}` with MaxDD `{fmt_pct(best_maxdd["MaxDD"])}`.
7. **Which holding count provides the best overall balance between CAGR, Sharpe, and MaxDD?** {recommendation}
8. **Should Framework001 migrate to Top3 or Top7?** A migration is justified only if the improvement is meaningful across risk-adjusted return and drawdown. Marginal or one-dimensional improvement is not enough to change the frozen framework.

## 11. Final Conclusion

This study compares only Top3, Top5, and Top7. It does not search other holding counts.

{recommendation} Framework001 should remain unchanged unless Top3 or Top7 shows a materially better and more balanced profile across CAGR, Sharpe, and MaxDD.

## 12. Output Files

- `metrics/performance.csv`
- `metrics/relative_change.csv`
- `metrics/portfolio_diagnostics.csv`
- `metrics/position_weight_diagnostics.csv`
- `metrics/asset_class_exposure.csv`
- `metrics/selection_frequency.csv`
- `outputs/monthly_holdings.csv`
- `outputs/daily_weights.csv`
- `outputs/daily_details.csv`
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    prices = core.load_prices().loc[:END_DATE].copy()
    returns = prices.pct_change(fill_method=None)
    targets, holdings = build_targets(prices)
    performance, details_by_strategy, weights_by_strategy = simulate(returns, targets)
    relative = relative_change(performance)
    diagnostics = portfolio_diagnostics(targets, details_by_strategy)
    weights_by_rank = position_weight_diagnostics(holdings)
    exposure = asset_class_exposure(weights_by_strategy)
    frequency = selection_frequency(holdings)

    performance.to_csv(METRICS_DIR / "performance.csv", index=False)
    relative.to_csv(METRICS_DIR / "relative_change.csv", index=False)
    diagnostics.to_csv(METRICS_DIR / "portfolio_diagnostics.csv", index=False)
    weights_by_rank.to_csv(METRICS_DIR / "position_weight_diagnostics.csv", index=False)
    exposure.to_csv(METRICS_DIR / "asset_class_exposure.csv", index=False)
    frequency.to_csv(METRICS_DIR / "selection_frequency.csv", index=False)
    holdings.to_csv(OUTPUTS_DIR / "monthly_holdings.csv", index=False)
    save_daily_outputs(details_by_strategy, weights_by_strategy)

    summary = generate_summary(performance, relative, diagnostics, weights_by_rank, exposure, frequency)
    SUMMARY_PATH.write_text(summary, encoding="utf-8")

    print("\nResearch 003 — Number of Holdings Complete")
    print(f"Study directory: {STUDY_DIR}")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nRelative change vs Framework001:")
    print(relative.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nPortfolio diagnostics:")
    print(diagnostics.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
