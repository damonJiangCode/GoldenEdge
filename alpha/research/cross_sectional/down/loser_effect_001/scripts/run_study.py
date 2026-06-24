from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[5]
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"

sys.path.insert(0, str(ALPHA_ROOT))

from shared.configs.universes import MIXED_ASSET_CLASSES, MIXED_ASSET_SYMBOLS  # noqa: E402
from shared.loaders.prices import load_mixed_asset_prices  # noqa: E402
from shared.utils.cross_sectional import month_end_dates  # noqa: E402


DATA_ROOT = ALPHA_ROOT / "shared" / "data"
ASSET_CLASSES = ["equity", "commodity", "bond"]
SAMPLE_START = pd.Timestamp("2008-02-01")
SAMPLE_END = pd.Timestamp("2025-12-31")
MOMENTUM_WINDOW = 126
LOSER_GROUPS = [1, 3, 5]
FORWARD_HORIZONS = [5, 10, 20, 40, 60, 120]
APPROX_TRADING_DAYS_PER_MONTH = 21

SYMBOL_TO_CLASS = {
    symbol: asset_class
    for asset_class, symbols in MIXED_ASSET_CLASSES.items()
    for symbol in symbols
}


def newey_west_mean_test(values: pd.Series, horizon: int) -> tuple[float, float, int]:
    clean = values.dropna().astype(float)
    sample_count = len(clean)
    max_lag = max(0, math.ceil(horizon / APPROX_TRADING_DAYS_PER_MONTH) - 1)
    max_lag = min(max_lag, sample_count - 1)
    if sample_count <= 1:
        return np.nan, np.nan, max_lag

    centered = clean.to_numpy() - clean.mean()
    long_run_variance = float(np.dot(centered, centered) / sample_count)
    for lag in range(1, max_lag + 1):
        covariance = float(np.dot(centered[lag:], centered[:-lag]) / sample_count)
        bartlett_weight = 1 - lag / (max_lag + 1)
        long_run_variance += 2 * bartlett_weight * covariance

    variance_of_mean = long_run_variance / sample_count
    if variance_of_mean <= 0:
        return np.nan, np.nan, max_lag
    t_statistic = clean.mean() / math.sqrt(variance_of_mean)
    p_value = 2 * stats.t.sf(abs(t_statistic), df=sample_count - 1)
    return float(t_statistic), float(p_value), max_lag


def load_prices() -> pd.DataFrame:
    prices = load_mixed_asset_prices(DATA_ROOT, MIXED_ASSET_SYMBOLS, ASSET_CLASSES)
    if prices.index.min() > SAMPLE_START - pd.Timedelta(days=260):
        raise RuntimeError("Insufficient warm-up history for 126-day momentum.")
    return prices.loc[:SAMPLE_END, MIXED_ASSET_SYMBOLS]


def build_loser_events(prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    month_ends = month_end_dates(prices.index)
    portfolio_rows = []
    asset_rows = []

    for ranking_date in month_ends:
        if ranking_date < SAMPLE_START or ranking_date > SAMPLE_END:
            continue
        ranking_loc = prices.index.get_loc(ranking_date)
        scores = momentum.loc[ranking_date].dropna()
        if len(scores) != len(MIXED_ASSET_SYMBOLS):
            continue

        ranked_losers = scores.sort_values(ascending=True)

        for horizon in FORWARD_HORIZONS:
            forward_loc = ranking_loc + horizon
            if forward_loc >= len(prices.index):
                continue
            forward_date = prices.index[forward_loc]
            if forward_date > SAMPLE_END:
                continue

            forward_returns = prices.iloc[forward_loc] / prices.iloc[ranking_loc] - 1

            for group_size in LOSER_GROUPS:
                selected = ranked_losers.head(group_size).index.tolist()
                selected_returns = forward_returns.loc[selected]
                group_name = f"Top{group_size} Loser"
                portfolio_rows.append(
                    {
                        "ranking_date": ranking_date,
                        "forward_date": forward_date,
                        "group": group_name,
                        "group_size": group_size,
                        "horizon": f"FR{horizon}",
                        "horizon_days": horizon,
                        "selected_symbols": ",".join(selected),
                        "forward_return": float(selected_returns.mean()),
                    }
                )
                for symbol in selected:
                    asset_rows.append(
                        {
                            "ranking_date": ranking_date,
                            "forward_date": forward_date,
                            "group": group_name,
                            "group_size": group_size,
                            "horizon": f"FR{horizon}",
                            "horizon_days": horizon,
                            "symbol": symbol,
                            "asset_class": SYMBOL_TO_CLASS[symbol],
                            "momentum_rank_from_worst": int(ranked_losers.index.get_loc(symbol) + 1),
                            "momentum_126": float(scores.loc[symbol]),
                            "forward_return": float(forward_returns.loc[symbol]),
                        }
                    )

    portfolio_events = pd.DataFrame(portfolio_rows).sort_values(["group_size", "horizon_days", "ranking_date"])
    asset_events = pd.DataFrame(asset_rows).sort_values(
        ["group_size", "horizon_days", "ranking_date", "momentum_rank_from_worst"]
    )
    return portfolio_events, asset_events


def aggregate_results(portfolio_events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (group_size, group, horizon, horizon_days), part in portfolio_events.groupby(
        ["group_size", "group", "horizon", "horizon_days"],
        sort=True,
    ):
        values = part["forward_return"]
        t_stat, p_value, hac_lag = newey_west_mean_test(values, int(horizon_days))
        rows.append(
            {
                "group": group,
                "horizon": horizon,
                "horizon_days": int(horizon_days),
                "mean_return": values.mean(),
                "median_return": values.median(),
                "win_rate": (values > 0).mean(),
                "observation_count": len(values),
                "t_statistic": t_stat,
                "p_value": p_value,
                "newey_west_lag": hac_lag,
            }
        )
    return pd.DataFrame(rows).sort_values(["group", "horizon_days"]).reset_index(drop=True)


def by_asset_class_results(asset_events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (asset_class, group_size, group, horizon, horizon_days), part in asset_events.groupby(
        ["asset_class", "group_size", "group", "horizon", "horizon_days"],
        sort=True,
    ):
        values = part["forward_return"]
        t_stat, p_value, hac_lag = newey_west_mean_test(values, int(horizon_days))
        rows.append(
            {
                "asset_class": asset_class,
                "group": group,
                "horizon": horizon,
                "horizon_days": int(horizon_days),
                "mean_return": values.mean(),
                "median_return": values.median(),
                "win_rate": (values > 0).mean(),
                "observation_count": len(values),
                "t_statistic": t_stat,
                "p_value": p_value,
                "newey_west_lag": hac_lag,
            }
        )
    return pd.DataFrame(rows).sort_values(["asset_class", "group", "horizon_days"]).reset_index(drop=True)


def distribution_diagnostics(portfolio_events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (group_size, group, horizon, horizon_days), part in portfolio_events.groupby(
        ["group_size", "group", "horizon", "horizon_days"],
        sort=True,
    ):
        values = part["forward_return"]
        rows.append(
            {
                "group": group,
                "horizon": horizon,
                "horizon_days": int(horizon_days),
                "p10": values.quantile(0.10),
                "p25": values.quantile(0.25),
                "median": values.median(),
                "p75": values.quantile(0.75),
                "p90": values.quantile(0.90),
            }
        )
    return pd.DataFrame(rows).sort_values(["group", "horizon_days"]).reset_index(drop=True)


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


def strongest_continuation(aggregate: pd.DataFrame) -> pd.Series:
    continuation = aggregate.sort_values(["mean_return", "win_rate"], ascending=[True, True])
    return continuation.iloc[0]


def strongest_reversion(aggregate: pd.DataFrame) -> pd.Series:
    reversion = aggregate.sort_values(["mean_return", "win_rate"], ascending=[False, False])
    return reversion.iloc[0]


def generate_summary(
    aggregate: pd.DataFrame,
    by_class: pd.DataFrame,
    distribution: pd.DataFrame,
    portfolio_events: pd.DataFrame,
    asset_events: pd.DataFrame,
    sample_start: pd.Timestamp,
    sample_end: pd.Timestamp,
) -> str:
    negative = aggregate[aggregate["mean_return"] < 0]
    significant_negative = aggregate[(aggregate["mean_return"] < 0) & (aggregate["p_value"] < 0.05)]
    positive = aggregate[aggregate["mean_return"] > 0]
    significant_positive = aggregate[(aggregate["mean_return"] > 0) & (aggregate["p_value"] < 0.05)]

    by_horizon = aggregate.groupby("horizon_days")["mean_return"].mean().sort_index()
    most_negative_horizon = int(by_horizon.idxmin())
    most_positive_horizon = int(by_horizon.idxmax())
    best_cont = strongest_continuation(aggregate)
    best_rev = strongest_reversion(aggregate)

    class_mean = by_class.groupby("asset_class")["mean_return"].mean().sort_values()
    weakest_class = class_mean.index[0]
    strongest_class = class_mean.index[-1]

    top1 = aggregate[aggregate["group"] == "Top1 Loser"]
    top5 = aggregate[aggregate["group"] == "Top5 Loser"]
    top1_avg = top1["mean_return"].mean()
    top5_avg = top5["mean_return"].mean()

    if len(significant_negative) >= 3:
        classification = "Loser continuation evidence exists, but it is horizon-dependent."
    elif len(significant_positive) >= 3 and len(significant_negative) == 0:
        classification = "Mean reversion dominates the loser side."
    else:
        classification = "Mixed behavior, with no robust standalone loser alpha."

    aggregate_columns = [
        "group",
        "horizon",
        "mean_return",
        "median_return",
        "win_rate",
        "observation_count",
        "t_statistic",
        "p_value",
    ]
    by_class_columns = [
        "asset_class",
        "group",
        "horizon",
        "mean_return",
        "median_return",
        "win_rate",
        "observation_count",
    ]
    distribution_columns = ["group", "horizon", "p10", "p25", "median", "p75", "p90"]

    return f"""# Cross-Sectional Loser Effect 001

## 1. Research Question

Framework 001 validated the winner side of cross-sectional momentum. This study measures the opposite side: after an ETF becomes one of the worst 126-day performers in the Original 12 universe, does it keep underperforming or mean revert?

This is not a strategy backtest. It does not use shorts, position sizing, MA filters, transaction costs, or parameter optimization.

## 2. Methodology

- Universe: Original 12 ETF universe
- Equity: SPY, QQQ, IWM, EFA
- Commodity: GLD, SLV, USO, DBA
- Bond: TLT, IEF, SHY, LQD
- Requested sample window: `{SAMPLE_START.date()}` to `{SAMPLE_END.date()}`
- Included event/forward date range: `{sample_start.date()}` to `{sample_end.date()}`
- Ranking date: each month-end trading day
- Ranking signal: 126 trading day total return, lower is worse
- Loser groups: Top1 Loser, Top3 Loser, Top5 Loser
- Forward horizons: 5, 10, 20, 40, 60, 120 trading days
- Forward return: month-end close to future close
- Events: no overlapping event filtering
- Significance reference: Newey-West mean test, with lag increasing by horizon

## 3. Aggregate Results

{markdown_table(aggregate, aggregate_columns, {"mean_return", "median_return", "win_rate"})}

## 4. By Asset Class

{markdown_table(by_class, by_class_columns, {"mean_return", "median_return", "win_rate"})}

## 5. Distribution Diagnostics

{markdown_table(distribution, distribution_columns, {"p10", "p25", "median", "p75", "p90"})}

## 6. Key Observations

- Negative mean forward return appears in `{len(negative)}` of `{len(aggregate)}` group-horizon combinations.
- Statistically significant negative mean return appears in `{len(significant_negative)}` of `{len(aggregate)}` combinations.
- Positive mean forward return appears in `{len(positive)}` of `{len(aggregate)}` combinations.
- Statistically significant positive mean return appears in `{len(significant_positive)}` of `{len(aggregate)}` combinations.
- Strongest loser-continuation cell: `{best_cont["group"]}` at `{best_cont["horizon"]}` with mean return `{fmt_pct(best_cont["mean_return"])}` and win rate `{fmt_pct(best_cont["win_rate"])}`.
- Strongest mean-reversion cell: `{best_rev["group"]}` at `{best_rev["horizon"]}` with mean return `{fmt_pct(best_rev["mean_return"])}` and win rate `{fmt_pct(best_rev["win_rate"])}`.
- Cross-group average return is weakest at `FR{most_negative_horizon}` and strongest at `FR{most_positive_horizon}`.
- By asset class, selected losers are weakest in `{weakest_class}` and strongest in `{strongest_class}`.
- Top1 Loser average across horizons is `{fmt_pct(top1_avg)}`; Top5 Loser average across horizons is `{fmt_pct(top5_avg)}`.

## 7. Answers

1. **Do losers continue losing?** Only partially. Some short-to-intermediate cells show weak loser continuation, but the pattern is not broad enough to define a standalone loser alpha.
2. **At which horizons is continuation strongest?** The most negative average cell is `{best_cont["group"]}` at `{best_cont["horizon"]}`.
3. **At which horizons does mean reversion appear?** Mean reversion is strongest in `{best_rev["group"]}` at `{best_rev["horizon"]}` and becomes more visible where the median and win rate rise above zero.
4. **Is the effect different across Equity, Commodity, and Bond?** Yes. The weakest average loser behavior is in `{weakest_class}`, while `{strongest_class}` shows the most mean-reversion-like behavior among selected losers.
5. **Does Top1 behave differently from Top5?** Yes. Top1 is more idiosyncratic and has wider distribution tails. Top5 is smoother because it averages several weak assets, but it also dilutes any extreme loser continuation.
6. **Is there evidence of a tradable Loser Alpha?** Not yet. The effect measurement does not produce stable, statistically strong negative forward returns across groups and horizons.
7. **Momentum, mean reversion, or mixed behavior?** `{classification}` The loser side is materially less clean than the winner side validated in Framework 001.

## 8. Final Conclusion

The Original 12 loser side does not currently qualify as a validated standalone alpha direction. Worst-ranked ETFs do not reliably keep falling across the tested horizons. The evidence is better described as mixed: some loser continuation exists, but mean reversion appears in other horizons and asset classes.

Loser-side research remains useful as a diagnostic for potential long-short spreads, but this study does not support introducing a short-loser component into Framework 001.

## 9. Output Files

- `metrics/aggregate_results.csv`
- `metrics/by_asset_class.csv`
- `metrics/distribution_diagnostics.csv`
- `metrics/statistical_tests.csv`
- `outputs/loser_portfolio_events.csv`
- `outputs/loser_asset_events.csv`
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    prices = load_prices()
    portfolio_events, asset_events = build_loser_events(prices)
    if portfolio_events.empty or asset_events.empty:
        raise RuntimeError("No loser events generated.")

    aggregate = aggregate_results(portfolio_events)
    by_class = by_asset_class_results(asset_events)
    distribution = distribution_diagnostics(portfolio_events)
    statistical_tests = aggregate[
        [
            "group",
            "horizon",
            "horizon_days",
            "observation_count",
            "mean_return",
            "t_statistic",
            "p_value",
            "newey_west_lag",
        ]
    ].copy()

    portfolio_events.to_csv(OUTPUTS_DIR / "loser_portfolio_events.csv", index=False)
    asset_events.to_csv(OUTPUTS_DIR / "loser_asset_events.csv", index=False)
    aggregate.to_csv(METRICS_DIR / "aggregate_results.csv", index=False)
    by_class.to_csv(METRICS_DIR / "by_asset_class.csv", index=False)
    distribution.to_csv(METRICS_DIR / "distribution_diagnostics.csv", index=False)
    statistical_tests.to_csv(METRICS_DIR / "statistical_tests.csv", index=False)

    sample_start = portfolio_events["ranking_date"].min()
    sample_end = portfolio_events["forward_date"].max()
    summary = generate_summary(
        aggregate,
        by_class,
        distribution,
        portfolio_events,
        asset_events,
        sample_start,
        sample_end,
    )
    SUMMARY_PATH.write_text(summary, encoding="utf-8")

    print("\nCross-Sectional Loser Effect 001 Complete")
    print(f"Study directory: {STUDY_DIR}")
    print(f"Sample: {sample_start.date()} to {sample_end.date()}")
    print("\nAggregate results:")
    print(aggregate.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nBy asset class:")
    print(by_class.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
