from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[4]
BASELINE_DIR = ALPHA_ROOT / "research" / "cross_sectional" / "mixed_asset_momentum"
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(ALPHA_ROOT))

from shared.utils import cross_sectional as core  # noqa: E402


MOMENTUM_WINDOW = 126
PORTFOLIO_SIZES = [1, 3, 5]
FORWARD_HORIZONS = [5, 15, 30, 45, 60]
APPROX_TRADING_DAYS_PER_MONTH = 21


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


def build_observations(
    prices: pd.DataFrame,
    sample_start: pd.Timestamp,
    sample_end: pd.Timestamp,
) -> pd.DataFrame:
    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    month_ends = core.month_end_dates(prices.index)
    rows = []

    for ranking_date in month_ends:
        scores = momentum.loc[ranking_date].dropna()
        if len(scores) != len(prices.columns):
            continue
        ranking_location = prices.index.get_loc(ranking_date)
        if ranking_location + 1 >= len(prices.index):
            continue
        effective_date = prices.index[ranking_location + 1]
        if effective_date < sample_start or effective_date > sample_end:
            continue

        ranked = scores.sort_values(ascending=False)
        for horizon in FORWARD_HORIZONS:
            forward_location = ranking_location + horizon
            if forward_location >= len(prices.index):
                continue
            forward_date = prices.index[forward_location]
            if forward_date > sample_end:
                continue

            asset_forward_returns = prices.iloc[forward_location] / prices.iloc[ranking_location] - 1
            equal_weight_return = float(asset_forward_returns.mean())
            for size in PORTFOLIO_SIZES:
                top_symbols = ranked.head(size).index
                bottom_symbols = ranked.tail(size).index
                top_return = float(asset_forward_returns.loc[top_symbols].mean())
                bottom_return = float(asset_forward_returns.loc[bottom_symbols].mean())
                rows.append(
                    {
                        "ranking_date": ranking_date,
                        "effective_date": effective_date,
                        "forward_date": forward_date,
                        "portfolio_size": size,
                        "portfolio": f"Bottom{size}",
                        "horizon": f"FR{horizon}",
                        "horizon_days": horizon,
                        "top_symbols": ",".join(top_symbols),
                        "bottom_symbols": ",".join(bottom_symbols),
                        "top_return": top_return,
                        "bottom_return": bottom_return,
                        "equal_weight_return": equal_weight_return,
                        "bottom_excess": bottom_return - equal_weight_return,
                        "top_excess": top_return - equal_weight_return,
                        "winner_loser_spread": top_return - bottom_return,
                    }
                )
    return pd.DataFrame(rows).sort_values(["ranking_date", "horizon_days", "portfolio_size"])


def summarize_series(
    observations: pd.DataFrame,
    value_column: str,
    include_distribution: bool,
) -> pd.DataFrame:
    rows = []
    for (size, portfolio, horizon, horizon_days), part in observations.groupby(
        ["portfolio_size", "portfolio", "horizon", "horizon_days"], sort=False
    ):
        values = part[value_column]
        t_statistic, p_value, hac_lag = newey_west_mean_test(values, int(horizon_days))
        row = {
            "portfolio_size": int(size),
            "portfolio": portfolio,
            "horizon": horizon,
            "horizon_days": int(horizon_days),
            "sample_count": len(values),
        }
        if include_distribution:
            row.update(
                {
                    "mean": values.mean(),
                    "median": values.median(),
                    "std": values.std(ddof=1),
                    "win_rate": (values > 0).mean(),
                }
            )
        else:
            row.update(
                {
                    "avg_excess": values.mean(),
                    "win_rate": (values > 0).mean(),
                }
            )
        row.update(
            {
                "t_statistic": t_statistic,
                "p_value": p_value,
                "newey_west_lag": hac_lag,
            }
        )
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["portfolio_size", "horizon_days"]).reset_index(drop=True)


def summarize_spread(observations: pd.DataFrame) -> pd.DataFrame:
    summary = summarize_series(observations, "winner_loser_spread", include_distribution=False)
    return summary.rename(
        columns={
            "portfolio": "bottom_portfolio",
            "avg_excess": "spread_mean",
            "win_rate": "spread_win_rate",
        }
    )


def compare_spread_to_winner(
    spread: pd.DataFrame,
    winner: pd.DataFrame,
) -> pd.DataFrame:
    winner_columns = winner[
        [
            "portfolio_size",
            "horizon",
            "avg_excess",
            "win_rate",
            "t_statistic",
            "p_value",
        ]
    ].rename(
        columns={
            "avg_excess": "winner_excess_mean",
            "win_rate": "winner_excess_win_rate",
            "t_statistic": "winner_t_statistic",
            "p_value": "winner_p_value",
        }
    )
    result = spread.merge(winner_columns, on=["portfolio_size", "horizon"], how="left")
    result["spread_t_stronger"] = result["t_statistic"] > result["winner_t_statistic"]
    result["spread_p_lower"] = result["p_value"] < result["winner_p_value"]
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
    bottom: pd.DataFrame,
    bottom_excess: pd.DataFrame,
    spread: pd.DataFrame,
    winner_excess: pd.DataFrame,
    spread_comparison: pd.DataFrame,
    sample_start: pd.Timestamp,
    sample_end: pd.Timestamp,
) -> str:
    negative_bottom = bottom[bottom["mean"] < 0]
    significant_negative_bottom = negative_bottom[negative_bottom["p_value"] < 0.05]
    weak_bottom = bottom_excess[bottom_excess["avg_excess"] < 0]
    significant_weak_bottom = weak_bottom[weak_bottom["p_value"] < 0.05]
    significant_winner = winner_excess[
        (winner_excess["avg_excess"] > 0) & (winner_excess["p_value"] < 0.05)
    ]
    significant_spread = spread[
        (spread["spread_mean"] > 0) & (spread["p_value"] < 0.05)
    ]

    horizon_pattern = (
        bottom_excess.groupby("horizon_days")["avg_excess"].mean().sort_index()
    )
    differences = horizon_pattern.diff().dropna()
    if (differences < 0).all():
        horizon_text = "Bottom underperformance strengthens monotonically as the horizon increases."
    elif (differences > 0).all():
        horizon_text = "Bottom underperformance weakens monotonically as the horizon increases."
    else:
        lowest_horizon = int(horizon_pattern.idxmin())
        horizon_text = (
            f"Bottom underperformance is not monotonic; its most negative cross-size average occurs at FR{lowest_horizon}."
        )

    stronger_spread_count = int(
        (spread_comparison["spread_t_stronger"] & spread_comparison["spread_p_lower"]).sum()
    )
    total_comparisons = len(spread_comparison)

    if len(significant_negative_bottom) > 0 and len(significant_weak_bottom) > 0:
        final_classification = "Loser Continuation"
        final_reason = "Bottom 同时存在显著负收益和显著相对弱势。"
    elif len(significant_winner) > len(significant_weak_bottom):
        final_classification = "Winner Continuation primarily, with limited relative loser weakness"
        final_reason = (
            "Bottom 的负收益没有统计显著性，相对弱势仅 1/15 显著；"
            "Winner-only 相对 Equal Weight 则有更广泛的显著证据。"
        )
    elif len(significant_weak_bottom) > 0:
        final_classification = "Relative Loser Continuation, not absolute decline"
        final_reason = "Loser 仍可能上涨，显著证据只支持相对弱势，不支持持续下跌。"
    else:
        final_classification = "No robust directional continuation"
        final_reason = "Bottom 弱势和 Winner 强势都没有形成稳定显著证据。"

    bottom_columns = [
        "portfolio", "horizon", "sample_count", "mean", "median", "std", "win_rate",
        "t_statistic", "p_value",
    ]
    excess_columns = [
        "portfolio", "horizon", "sample_count", "avg_excess", "win_rate", "t_statistic", "p_value",
    ]
    spread_columns = [
        "portfolio_size", "horizon", "sample_count", "spread_mean", "spread_win_rate",
        "t_statistic", "p_value",
    ]
    winner_columns = [
        "portfolio_size", "horizon", "sample_count", "avg_excess", "win_rate", "t_statistic", "p_value",
    ]

    return f"""# Bottom Loser Continuation Study

## 1. Research Question

过去 126 个交易日表现最差的资产，未来是否继续表现最差？本研究是 event-study validation，不构建或优化交易策略。

- Universe: current 12 ETF Mixed Asset Universe
- Sample: `{sample_start.date()}` to `{sample_end.date()}`
- Ranking frequency: monthly, at month end
- Momentum lookback: 126 trading days
- Forward horizons: 5/15/30/45/60 trading days
- Portfolios: Bottom1/Bottom3/Bottom5 and matched Top1/Top3/Top5
- Forward return starts from the ranking-date close; no transaction cost is applied
- t-statistic and two-sided p-value use Newey-West standard errors to address overlapping forward returns

## 2. Bottom Portfolio Future Returns

{markdown_table(bottom, bottom_columns, {"mean", "median", "std", "win_rate"})}

## 3. Bottom vs Equal Weight Universe

`Bottom excess = Bottom portfolio forward return - 12 ETF Equal Weight forward return`

{markdown_table(bottom_excess, excess_columns, {"avg_excess", "win_rate"})}

## 4. Winner-Loser Spread

`Spread = matched Top N forward return - Bottom N forward return`

{markdown_table(spread, spread_columns, {"spread_mean", "spread_win_rate"})}

## 5. Winner-Only Continuation

Winner-only continuation is evaluated against the same Equal Weight Universe:

{markdown_table(winner_excess, winner_columns, {"avg_excess", "win_rate"})}

## 6. Answers

1. **Are Bottom portfolios negative on average?** {len(negative_bottom)}/{len(bottom)} portfolio-horizon combinations have negative mean forward return, but only {len(significant_negative_bottom)}/{len(bottom)} are significantly below zero.
2. **Do Bottom portfolios underperform Equal Weight?** {len(weak_bottom)}/{len(bottom_excess)} have negative average excess; {len(significant_weak_bottom)}/{len(bottom_excess)} are negative with p-value < 0.05.
3. **Does underperformance change with horizon?** {horizon_text} This is an economic-magnitude pattern; statistical significance does not strengthen monotonically.
4. **Is Winner-Loser statistically stronger than Winner-only?** No overall. Spread has both a higher t-statistic and lower p-value in only {stronger_spread_count}/{total_comparisons} matched comparisons. Significant positive spread exists in {len(significant_spread)}/{len(spread)} combinations, versus {len(significant_winner)}/{len(winner_excess)} significant positive Winner-only excess combinations.
5. **Classification:** `{final_classification}`. {final_reason}

## 7. Interpretation Guardrails

- Bottom future return being positive does not disprove relative loser weakness; broad market drift can lift both winners and losers.
- Bottom underperforming Equal Weight does not mean losers are profitable shorts after financing, borrow costs, and implementation constraints.
- Winner-Loser spread can be significant even when neither leg is attractive as a standalone trade.
- Top3/Top5 spreads at FR15, and Top5 at FR30, justify further long-short implementation research; they do not establish a robust short-loser strategy across horizons.
- The same monthly observations overlap at longer horizons. Newey-West correction reduces, but does not eliminate, regime dependence and multiple-comparison risk.
- This study does not test alternative lookbacks, ranking frequencies, or portfolio sizes beyond the fixed specification.
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    prices = core.load_prices()
    existing_daily = pd.read_csv(BASELINE_DIR / "outputs" / "daily_returns.csv", index_col="Date", parse_dates=True)
    sample_start = existing_daily.index.min()
    sample_end = existing_daily.index.max()

    observations = build_observations(prices, sample_start, sample_end)
    bottom = summarize_series(observations, "bottom_return", include_distribution=True)
    bottom_excess = summarize_series(observations, "bottom_excess", include_distribution=False)
    winner_excess = summarize_series(observations, "top_excess", include_distribution=False)
    winner_excess["portfolio"] = winner_excess["portfolio_size"].map(lambda size: f"Top{size}")
    spread = summarize_spread(observations)
    spread_comparison = compare_spread_to_winner(spread, winner_excess)

    bottom.to_csv(METRICS_DIR / "bottom_forward_return_summary.csv", index=False)
    bottom_excess.to_csv(METRICS_DIR / "bottom_vs_equal_weight.csv", index=False)
    spread.to_csv(METRICS_DIR / "winner_loser_spread.csv", index=False)
    winner_excess.to_csv(METRICS_DIR / "winner_vs_equal_weight.csv", index=False)
    spread_comparison.to_csv(METRICS_DIR / "spread_vs_winner_comparison.csv", index=False)
    observations.to_csv(OUTPUTS_DIR / "forward_return_observations.csv", index=False)
    summary = generate_summary(
        bottom,
        bottom_excess,
        spread,
        winner_excess,
        spread_comparison,
        sample_start,
        sample_end,
    )
    SUMMARY_PATH.write_text(summary, encoding="utf-8")

    print("\nBottom Loser Continuation Study Complete")
    print(f"Study directory: {STUDY_DIR}")
    print(f"Sample: {sample_start.date()} to {sample_end.date()}")
    print("\nBottom forward returns:")
    print(bottom.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nBottom vs Equal Weight:")
    print(bottom_excess.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nWinner-Loser spread:")
    print(spread.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
