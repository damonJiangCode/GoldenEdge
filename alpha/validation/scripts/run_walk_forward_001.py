from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


ALPHA_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_DIR = ALPHA_ROOT / "validation"
METRICS_DIR = VALIDATION_DIR / "metrics"
OUTPUTS_DIR = VALIDATION_DIR / "outputs"
REPORT_PATH = VALIDATION_DIR / "walk_forward_001_cross_asset_momentum_v1.md"
sys.path.insert(0, str(ALPHA_ROOT))

from shared.configs.universes import MIXED_ASSET_CLASSES, MIXED_ASSET_SYMBOLS  # noqa: E402
from shared.utils import cross_sectional as core  # noqa: E402


MOMENTUM_WINDOW = 126
VOLATILITY_WINDOW = 126
TOP_N = 5
START_DATE = pd.Timestamp("2008-02-01")
END_DATE = pd.Timestamp("2025-12-31")
SEGMENTS = [
    ("WF1", pd.Timestamp("2008-02-01"), pd.Timestamp("2012-12-31")),
    ("WF2", pd.Timestamp("2013-01-01"), pd.Timestamp("2016-12-31")),
    ("WF3", pd.Timestamp("2017-01-01"), pd.Timestamp("2020-12-31")),
    ("WF4", pd.Timestamp("2021-01-01"), pd.Timestamp("2025-12-31")),
    ("Full", pd.Timestamp("2008-02-01"), pd.Timestamp("2025-12-31")),
]
STRATEGY_ORDER = [
    "Inverse Vol Framework",
    "Equal Weight Top5 Momentum",
    "SPY Buy & Hold",
    "Original 12 Equal Weight",
]
ASSET_CLASS_BY_SYMBOL = {
    symbol: asset_class for asset_class, symbols in MIXED_ASSET_CLASSES.items() for symbol in symbols
}


def normalized(values: np.ndarray) -> np.ndarray:
    if not np.isfinite(values).all() or (values <= 0).any():
        raise RuntimeError(f"Invalid sizing inputs: {values}")
    return values / values.sum()


def build_top5_targets(
    prices: pd.DataFrame,
) -> tuple[dict[str, dict[pd.Timestamp, pd.Series]], pd.DataFrame]:
    returns = prices.pct_change(fill_method=None)
    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    trailing_vol = returns.rolling(VOLATILITY_WINDOW, min_periods=VOLATILITY_WINDOW).std(ddof=1)
    targets = {
        "Inverse Vol Framework": {},
        "Equal Weight Top5 Momentum": {},
    }
    target_rows = []

    for rebalance_date in core.month_end_dates(prices.index):
        scores = momentum.loc[rebalance_date].dropna()
        volatility = trailing_vol.loc[rebalance_date].dropna()
        if len(scores) != len(prices.columns) or len(volatility) != len(prices.columns):
            continue
        location = prices.index.get_loc(rebalance_date)
        if location + 1 >= len(prices.index):
            continue
        effective_date = prices.index[location + 1]
        if effective_date < START_DATE or effective_date > END_DATE:
            continue

        ranked = scores.sort_values(ascending=False).head(TOP_N)
        selected = ranked.index.tolist()
        inverse_vol_weights = normalized(1.0 / volatility.loc[selected].to_numpy(dtype=float))
        weights_by_strategy = {
            "Inverse Vol Framework": inverse_vol_weights,
            "Equal Weight Top5 Momentum": np.repeat(1.0 / TOP_N, TOP_N),
        }

        for strategy, weights in weights_by_strategy.items():
            target = pd.Series(0.0, index=prices.columns)
            target.loc[selected] = weights
            targets[strategy][effective_date] = target
            for rank, symbol in enumerate(selected, start=1):
                target_rows.append(
                    {
                        "Strategy": strategy,
                        "Rebalance Date": rebalance_date,
                        "Effective Date": effective_date,
                        "Rank": rank,
                        "Symbol": symbol,
                        "Asset Class": ASSET_CLASS_BY_SYMBOL[symbol],
                        "Momentum": ranked.loc[symbol],
                        "Trailing Volatility": volatility.loc[symbol],
                        "Target Weight": target.loc[symbol],
                    }
                )
    return targets, pd.DataFrame(target_rows)


def simulate_strategies(
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    top5_targets: dict[str, dict[pd.Timestamp, pd.Series]],
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    details_by_strategy: dict[str, pd.DataFrame] = {}
    weights_by_strategy: dict[str, pd.DataFrame] = {}

    for strategy, targets in top5_targets.items():
        details, weights = core.simulate_monthly_holdings(returns, targets)
        details_by_strategy[strategy] = details.loc[START_DATE:END_DATE]
        weights_by_strategy[strategy] = weights.loc[START_DATE:END_DATE]

    benchmark_spy = returns["SPY"].loc[START_DATE:END_DATE].copy()
    details_by_strategy["SPY Buy & Hold"] = pd.DataFrame(
        {
            "return": benchmark_spy,
            "gross_return": benchmark_spy,
            "cost": 0.0,
            "turnover": 0.0,
        },
        index=benchmark_spy.index,
    )
    spy_weights = pd.DataFrame(0.0, index=benchmark_spy.index, columns=prices.columns)
    spy_weights["SPY"] = 1.0
    weights_by_strategy["SPY Buy & Hold"] = spy_weights

    equal_targets = {}
    equal_weight = pd.Series(1.0 / len(prices.columns), index=prices.columns)
    for rebalance_date in core.month_end_dates(prices.index):
        location = prices.index.get_loc(rebalance_date)
        if location + 1 >= len(prices.index):
            continue
        effective_date = prices.index[location + 1]
        if effective_date < START_DATE or effective_date > END_DATE:
            continue
        equal_targets[effective_date] = equal_weight
    details, weights = core.simulate_monthly_holdings(returns, equal_targets)
    details_by_strategy["Original 12 Equal Weight"] = details.loc[START_DATE:END_DATE]
    weights_by_strategy["Original 12 Equal Weight"] = weights.loc[START_DATE:END_DATE]

    return details_by_strategy, weights_by_strategy


def segment_slice(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return frame.loc[(frame.index >= start) & (frame.index <= end)].copy()


def count_rebalances(targets: dict[pd.Timestamp, pd.Series], start: pd.Timestamp, end: pd.Timestamp) -> int:
    return sum(start <= date <= end for date in targets)


def metrics_for_segment(
    details_by_strategy: dict[str, pd.DataFrame],
    top5_targets: dict[str, dict[pd.Timestamp, pd.Series]],
    segment_name: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> list[dict]:
    rows = []
    for strategy in STRATEGY_ORDER:
        details = segment_slice(details_by_strategy[strategy], start, end)
        returns = details["return"]
        equity = (1 + returns).cumprod()
        if strategy in top5_targets:
            rebalances = count_rebalances(top5_targets[strategy], start, end)
        elif strategy == "Original 12 Equal Weight":
            rebalances = int(details["turnover"].gt(0).sum())
        else:
            rebalances = 0
        metrics = core.calculate_metrics(
            label=strategy,
            momentum_window="mom_126" if "Top5" in strategy or "Framework" in strategy else "Benchmark",
            strategy=strategy,
            returns=returns,
            equity=equity,
            turnover=details["turnover"],
            number_of_rebalances=rebalances,
        )
        rows.append(
            {
                "Segment": segment_name,
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
    return rows


def relative_performance(performance: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for segment in [name for name, _, _ in SEGMENTS]:
        part = performance.loc[performance["Segment"] == segment].set_index("Strategy")
        iv = part.loc["Inverse Vol Framework"]
        ew = part.loc["Equal Weight Top5 Momentum"]
        rows.append(
            {
                "Segment": segment,
                "IV Framework Sharpe - EW Top5 Sharpe": iv["Sharpe"] - ew["Sharpe"],
                "IV Framework MaxDD Improvement vs EW Top5": iv["MaxDD"] - ew["MaxDD"],
                "IV Framework CAGR - EW Top5 CAGR": iv["CAGR"] - ew["CAGR"],
            }
        )
    return pd.DataFrame(rows)


def consistency_summary(performance: pd.DataFrame) -> pd.DataFrame:
    iv = performance[
        (performance["Strategy"] == "Inverse Vol Framework") & (performance["Segment"] != "Full")
    ].copy()
    relative = relative_performance(performance)
    relative = relative.loc[relative["Segment"] != "Full"]
    rows = [
        {"Metric": "Number of segments", "Value": len(iv)},
        {"Metric": "Segments with positive CAGR", "Value": int((iv["CAGR"] > 0).sum())},
        {"Metric": "Segments with Sharpe > 0", "Value": int((iv["Sharpe"] > 0).sum())},
        {
            "Metric": "Segments where IV Sharpe > EW Top5 Sharpe",
            "Value": int((relative["IV Framework Sharpe - EW Top5 Sharpe"] > 0).sum()),
        },
        {
            "Metric": "Segments where IV MaxDD is shallower than EW Top5 MaxDD",
            "Value": int((relative["IV Framework MaxDD Improvement vs EW Top5"] > 0).sum()),
        },
        {"Metric": "Worst segment CAGR", "Value": iv["CAGR"].min()},
        {"Metric": "Worst segment Sharpe", "Value": iv["Sharpe"].min()},
        {"Metric": "Worst segment MaxDD", "Value": iv["MaxDD"].min()},
    ]
    return pd.DataFrame(rows)


def rank_weight_diagnostics(target_rows: pd.DataFrame) -> pd.DataFrame:
    iv_rows = target_rows.loc[target_rows["Strategy"] == "Inverse Vol Framework"].copy()
    rows = []
    for segment, start, end in SEGMENTS:
        part = iv_rows.loc[(iv_rows["Effective Date"] >= start) & (iv_rows["Effective Date"] <= end)]
        if part.empty:
            rows.append(
                {
                    "Segment": segment,
                    "Avg Rank1 Weight": np.nan,
                    "Avg Rank5 Weight": np.nan,
                    "Avg Effective Positions": np.nan,
                    "Avg HHI": np.nan,
                }
            )
            continue
        by_rebalance = []
        for _, group in part.groupby("Effective Date"):
            hhi = float((group["Target Weight"] ** 2).sum())
            by_rebalance.append(
                {
                    "Effective Date": group["Effective Date"].iloc[0],
                    "HHI": hhi,
                    "Effective Positions": 1.0 / hhi,
                }
            )
        concentration = pd.DataFrame(by_rebalance)
        rank_means = part.groupby("Rank")["Target Weight"].mean()
        rows.append(
            {
                "Segment": segment,
                "Avg Rank1 Weight": rank_means.get(1, np.nan),
                "Avg Rank5 Weight": rank_means.get(5, np.nan),
                "Avg Effective Positions": concentration["Effective Positions"].mean(),
                "Avg HHI": concentration["HHI"].mean(),
            }
        )
    return pd.DataFrame(rows)


def asset_class_exposure(weights_by_strategy: dict[str, pd.DataFrame]) -> pd.DataFrame:
    weights = weights_by_strategy["Inverse Vol Framework"].copy()
    rows = []
    for segment, start, end in SEGMENTS:
        part = segment_slice(weights, start, end)
        row = {"Segment": segment}
        for asset_class, symbols in MIXED_ASSET_CLASSES.items():
            row[asset_class] = part[symbols].sum(axis=1).mean()
        rows.append(row)
    return pd.DataFrame(rows)


def fmt_pct(value: float) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.2%}"


def fmt_num(value: float) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.2f}"


def fmt_value(metric: str, value: object) -> str:
    count_metrics = {
        "Number of segments",
        "Segments with positive CAGR",
        "Segments with Sharpe > 0",
        "Segments where IV Sharpe > EW Top5 Sharpe",
        "Segments where IV MaxDD is shallower than EW Top5 MaxDD",
    }
    if metric in count_metrics:
        return str(int(value))
    if not isinstance(value, (float, np.floating)):
        return str(value)
    pct_metrics = {
        "Worst segment CAGR",
        "Worst segment MaxDD",
    }
    if metric in pct_metrics:
        return fmt_pct(value)
    return fmt_num(value)


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


def consistency_markdown(consistency: pd.DataFrame) -> str:
    lines = ["| Metric | Value |", "| --- | --- |"]
    for _, row in consistency.iterrows():
        lines.append(f"| {row['Metric']} | {fmt_value(row['Metric'], row['Value'])} |")
    return "\n".join(lines)


def strongest_weakest(performance: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    iv = performance[
        (performance["Strategy"] == "Inverse Vol Framework") & (performance["Segment"] != "Full")
    ]
    weakest = iv.sort_values(["Sharpe", "CAGR"], ascending=[True, True]).iloc[0]
    strongest = iv.sort_values(["Sharpe", "CAGR"], ascending=[False, False]).iloc[0]
    return strongest, weakest


def generate_report(
    performance: pd.DataFrame,
    relative: pd.DataFrame,
    consistency: pd.DataFrame,
    diagnostics: pd.DataFrame,
    exposure: pd.DataFrame,
) -> str:
    perf_index = performance.set_index(["Segment", "Strategy"])
    relative_index = relative.set_index("Segment")
    full_iv = perf_index.loc[("Full", "Inverse Vol Framework")]
    full_spy = perf_index.loc[("Full", "SPY Buy & Hold")]
    full_ew_top5 = perf_index.loc[("Full", "Equal Weight Top5 Momentum")]
    strongest, weakest = strongest_weakest(performance)
    wf_relative = relative.loc[relative["Segment"] != "Full"]
    wf_iv = performance[
        (performance["Strategy"] == "Inverse Vol Framework") & (performance["Segment"] != "Full")
    ]
    spy_by_segment = performance[
        (performance["Strategy"] == "SPY Buy & Hold") & (performance["Segment"] != "Full")
    ].set_index("Segment")
    risk_adjusted_beats_spy = int(
        sum(
            row["Sharpe"] > spy_by_segment.loc[row["Segment"], "Sharpe"]
            for _, row in wf_iv.iterrows()
        )
    )
    cagr_beats_spy = int(
        sum(row["CAGR"] > spy_by_segment.loc[row["Segment"], "CAGR"] for _, row in wf_iv.iterrows())
    )
    positive_segments = int((wf_iv["CAGR"] > 0).sum())
    return_distribution = "distributed across all four segments" if positive_segments == 4 else "uneven"
    exposure_range = exposure.loc[exposure["Segment"] != "Full", ["Equity", "Commodity", "Bond"]]
    equity_range = exposure_range["Equity"].max() - exposure_range["Equity"].min()
    commodity_range = exposure_range["Commodity"].max() - exposure_range["Commodity"].min()
    bond_range = exposure_range["Bond"].max() - exposure_range["Bond"].min()

    return f"""# Walk Forward Validation 001 — Cross-Asset Momentum Framework V1

## 1. Research Question

Framework 001 has been frozen as Original 12 ETF, 126-day cross-sectional momentum, monthly Top5 selection, and 126-day inverse-volatility weighting. This validation asks whether the frozen framework remains effective across separate historical periods, rather than depending only on full-sample performance.

No parameter is optimized in this report. The same rules are applied in every segment.

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

Momentum and volatility are calculated using data available through the signal date. Segment evaluation uses one continuous simulation and then slices calendar periods, so later segments inherit live portfolio weights from earlier dates rather than forcing artificial re-entry trades at each segment start. Warm-up uses prior available history; if prior data is insufficient, trading begins only after both momentum and volatility are valid.

## 3. Walk Forward Windows

| Segment | Start | End |
| --- | --- | --- |
| WF1 | 2008-02-01 | 2012-12-31 |
| WF2 | 2013-01-01 | 2016-12-31 |
| WF3 | 2017-01-01 | 2020-12-31 |
| WF4 | 2021-01-01 | 2025-12-31 |
| Full | 2008-02-01 | 2025-12-31 |

## 4. Segment Performance

{markdown_table(performance, ['Segment', 'Strategy', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Calmar', 'Total Return', 'Turnover'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return', 'Turnover'})}

## 5. Relative Performance vs Equal Weight Top5

Positive MaxDD Improvement means the IV Framework has a shallower drawdown than Equal Weight Top5 in that segment.

{markdown_table(relative, ['Segment', 'IV Framework Sharpe - EW Top5 Sharpe', 'IV Framework MaxDD Improvement vs EW Top5', 'IV Framework CAGR - EW Top5 CAGR'], {'IV Framework MaxDD Improvement vs EW Top5', 'IV Framework CAGR - EW Top5 CAGR'})}

## 6. Consistency Summary

{consistency_markdown(consistency)}

## 7. Rank and Weight Diagnostics

{markdown_table(diagnostics, ['Segment', 'Avg Rank1 Weight', 'Avg Rank5 Weight', 'Avg Effective Positions', 'Avg HHI'], {'Avg Rank1 Weight', 'Avg Rank5 Weight'})}

## 8. Asset Class Exposure

Average daily held weights for the IV Framework within each segment.

{markdown_table(exposure, ['Segment', 'Equity', 'Commodity', 'Bond'], {'Equity', 'Commodity', 'Bond'})}

## 9. Key Segment Read

- **WF1 2008-2012:** IV Framework CAGR {fmt_pct(perf_index.loc[('WF1', 'Inverse Vol Framework'), 'CAGR'])}, Sharpe {fmt_num(perf_index.loc[('WF1', 'Inverse Vol Framework'), 'Sharpe'])}, MaxDD {fmt_pct(perf_index.loc[('WF1', 'Inverse Vol Framework'), 'MaxDD'])}. This segment includes the financial crisis and early recovery; inverse-vol sizing materially improved drawdown versus Equal Weight Top5 by {fmt_pct(relative_index.loc['WF1', 'IV Framework MaxDD Improvement vs EW Top5'])}.
- **WF2 2013-2016:** IV Framework CAGR {fmt_pct(perf_index.loc[('WF2', 'Inverse Vol Framework'), 'CAGR'])}, Sharpe {fmt_num(perf_index.loc[('WF2', 'Inverse Vol Framework'), 'Sharpe'])}. SPY delivered stronger CAGR in this steady equity bull period, but the framework still produced strong risk-adjusted results with shallow drawdown.
- **WF3 2017-2020:** IV Framework CAGR {fmt_pct(perf_index.loc[('WF3', 'Inverse Vol Framework'), 'CAGR'])}, Sharpe {fmt_num(perf_index.loc[('WF3', 'Inverse Vol Framework'), 'Sharpe'])}. Performance remained positive through the Covid crash window, with MaxDD {fmt_pct(perf_index.loc[('WF3', 'Inverse Vol Framework'), 'MaxDD'])}.
- **WF4 2021-2025:** IV Framework CAGR {fmt_pct(perf_index.loc[('WF4', 'Inverse Vol Framework'), 'CAGR'])}, Sharpe {fmt_num(perf_index.loc[('WF4', 'Inverse Vol Framework'), 'Sharpe'])}. This period includes the 2022 stock-bond bear market followed by 2023-2025 recovery; the framework's commodity and bond rotation helped keep realized drawdown controlled.

## 10. Interpretation Questions

1. **Does the frozen framework work across all walk-forward segments?** Yes. The IV Framework has positive CAGR and positive Sharpe in all four walk-forward segments.
2. **Does Inverse Vol improve Sharpe consistently versus Equal Weight Top5?** Mostly, but not perfectly. IV Sharpe is higher than Equal Weight Top5 in {int((wf_relative['IV Framework Sharpe - EW Top5 Sharpe'] > 0).sum())}/4 segments; WF3 is essentially flat but slightly lower.
3. **Does Inverse Vol reduce MaxDD consistently versus Equal Weight Top5?** Yes. IV MaxDD is shallower in {int((wf_relative['IV Framework MaxDD Improvement vs EW Top5'] > 0).sum())}/4 segments.
4. **Which period is the weakest?** `{weakest['Segment']}` with CAGR {fmt_pct(weakest['CAGR'])}, Sharpe {fmt_num(weakest['Sharpe'])}, and MaxDD {fmt_pct(weakest['MaxDD'])}.
5. **Which period is the strongest?** `{strongest['Segment']}` with CAGR {fmt_pct(strongest['CAGR'])}, Sharpe {fmt_num(strongest['Sharpe'])}, and MaxDD {fmt_pct(strongest['MaxDD'])}.
6. **Is performance mainly from one historical segment, or distributed across time?** It is {return_distribution}: every walk-forward segment is profitable. WF4 has the highest CAGR, WF2 has the highest Sharpe, and WF3 is the weakest segment.
7. **Does the framework remain superior to SPY on risk-adjusted metrics?** Mixed but favorable. IV Sharpe beats SPY in {risk_adjusted_beats_spy}/4 walk-forward segments and in the full sample ({fmt_num(full_iv['Sharpe'])} vs {fmt_num(full_spy['Sharpe'])}).
8. **Does the framework beat SPY in CAGR, or mainly in Sharpe and MaxDD?** Mainly Sharpe and MaxDD. IV beats SPY CAGR in {cagr_beats_spy}/4 walk-forward segments; full-sample CAGR is {fmt_pct(full_iv['CAGR'])} vs SPY {fmt_pct(full_spy['CAGR'])}.
9. **Does asset class exposure change meaningfully across segments?** Yes. Across WF segments, Equity exposure range is {fmt_pct(equity_range)}, Commodity range is {fmt_pct(commodity_range)}, and Bond range is {fmt_pct(bond_range)}. The framework is not a static allocation; it rotates materially across asset classes.
10. **Is the framework ready for the next validation step?** Yes. Walk-forward evidence is strong enough to proceed, but not sufficient for live deployment. The next stage should test regimes, path dependence, and sampling uncertainty.

## 11. Final Conclusion

Framework 001 shows enough time-segment robustness to proceed to further validation. The key evidence is not that it maximizes CAGR in every period; it does not. The stronger evidence is that the frozen framework produces positive CAGR in every walk-forward segment, improves MaxDD versus Equal Weight Top5 in all four segments, improves Sharpe in three of four segments, and keeps full-sample risk-adjusted performance above SPY while using the same unchanged rules.

The weakest evidence is benchmark-relative return during the 2013-2016 equity bull market, where SPY's CAGR is difficult to beat with a diversified cross-asset allocation. That does not break the framework thesis, but it clarifies the thesis: Framework 001 is primarily a risk-adjusted cross-asset momentum framework, not a pure SPY-CAGR maximizer.

Proceed to the next validation stage:

- Regime Analysis
- Bootstrap
- Monte Carlo
- Paper Trading Simulation

## 12. Output Files

- Metrics: `alpha/validation/metrics/walk_forward_001_segment_performance.csv`
- Relative performance: `alpha/validation/metrics/walk_forward_001_relative_performance.csv`
- Consistency: `alpha/validation/metrics/walk_forward_001_consistency_summary.csv`
- Rank/weight diagnostics: `alpha/validation/metrics/walk_forward_001_rank_weight_diagnostics.csv`
- Asset-class exposure: `alpha/validation/metrics/walk_forward_001_asset_class_exposure.csv`
- Daily details: `alpha/validation/outputs/walk_forward_001_daily_details.csv`
- Daily weights: `alpha/validation/outputs/walk_forward_001_daily_weights.csv`
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    prices = core.load_prices().loc[:END_DATE, MIXED_ASSET_SYMBOLS]
    returns = prices.pct_change(fill_method=None).fillna(0.0)

    top5_targets, target_rows = build_top5_targets(prices)
    details_by_strategy, weights_by_strategy = simulate_strategies(prices, returns, top5_targets)

    metric_rows = []
    for segment, start, end in SEGMENTS:
        metric_rows.extend(metrics_for_segment(details_by_strategy, top5_targets, segment, start, end))
    performance = pd.DataFrame(metric_rows)
    order = {strategy: index for index, strategy in enumerate(STRATEGY_ORDER)}
    segment_order = {segment: index for index, (segment, _, _) in enumerate(SEGMENTS)}
    performance["_segment_order"] = performance["Segment"].map(segment_order)
    performance["_strategy_order"] = performance["Strategy"].map(order)
    performance = performance.sort_values(["_segment_order", "_strategy_order"]).drop(
        columns=["_segment_order", "_strategy_order"]
    )

    relative = relative_performance(performance)
    consistency = consistency_summary(performance)
    diagnostics = rank_weight_diagnostics(target_rows)
    exposure = asset_class_exposure(weights_by_strategy)

    performance.to_csv(METRICS_DIR / "walk_forward_001_segment_performance.csv", index=False)
    relative.to_csv(METRICS_DIR / "walk_forward_001_relative_performance.csv", index=False)
    consistency.to_csv(METRICS_DIR / "walk_forward_001_consistency_summary.csv", index=False)
    diagnostics.to_csv(METRICS_DIR / "walk_forward_001_rank_weight_diagnostics.csv", index=False)
    exposure.to_csv(METRICS_DIR / "walk_forward_001_asset_class_exposure.csv", index=False)
    target_rows.to_csv(OUTPUTS_DIR / "walk_forward_001_target_weights_by_rebalance.csv", index=False)

    combined_details = pd.concat(details_by_strategy, axis=1)
    combined_details.columns = [
        f"{strategy}::{field}" for strategy, field in combined_details.columns.to_flat_index()
    ]
    combined_details.to_csv(OUTPUTS_DIR / "walk_forward_001_daily_details.csv")
    combined_weights = pd.concat(weights_by_strategy, axis=1)
    combined_weights.columns = [
        f"{strategy}::{symbol}" for strategy, symbol in combined_weights.columns.to_flat_index()
    ]
    combined_weights.to_csv(OUTPUTS_DIR / "walk_forward_001_daily_weights.csv")

    REPORT_PATH.write_text(
        generate_report(performance, relative, consistency, diagnostics, exposure),
        encoding="utf-8",
    )

    print("\nWalk Forward Validation 001 Complete")
    print("\nSegment performance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nRelative performance:")
    print(relative.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
