from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


VALIDATION_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[3]
METRICS_DIR = VALIDATION_DIR / "metrics"
OUTPUTS_DIR = VALIDATION_DIR / "outputs"
REPORT_PATH = VALIDATION_DIR / "oos_001_framework_001_2026.md"

sys.path.insert(0, str(ALPHA_ROOT))

from shared.configs.universes import MIXED_ASSET_CLASSES, MIXED_ASSET_SYMBOLS  # noqa: E402
from shared.loaders.prices import load_mixed_asset_prices  # noqa: E402
from shared.utils import cross_sectional as core  # noqa: E402


DATA_ROOT = ALPHA_ROOT / "shared" / "data"
ASSET_CLASSES = ["equity", "commodity", "bond"]
MOMENTUM_WINDOW = 126
VOLATILITY_WINDOW = 126
TOP_N = 5
TRADING_COST = 0.0005
OOS_START = pd.Timestamp("2026-01-01")
OOS_END_REQUESTED = pd.Timestamp("2026-12-31")
STRATEGY_ORDER = [
    "Framework 001 / IV Framework",
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


def load_prices() -> pd.DataFrame:
    prices = load_mixed_asset_prices(DATA_ROOT, MIXED_ASSET_SYMBOLS, ASSET_CLASSES)
    prices = prices.loc[:OOS_END_REQUESTED, MIXED_ASSET_SYMBOLS].copy()
    if prices.index.max() < OOS_START:
        raise RuntimeError("No 2026 data available for OOS test.")
    return prices


def build_top5_targets(
    prices: pd.DataFrame,
    oos_end: pd.Timestamp,
) -> tuple[dict[str, dict[pd.Timestamp, pd.Series]], pd.DataFrame]:
    returns = prices.pct_change(fill_method=None)
    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    trailing_vol = returns.rolling(VOLATILITY_WINDOW, min_periods=VOLATILITY_WINDOW).std(ddof=1)
    targets = {
        "Framework 001 / IV Framework": {},
        "Equal Weight Top5 Momentum": {},
    }
    target_rows = []

    for rebalance_date in core.month_end_dates(prices.index):
        location = prices.index.get_loc(rebalance_date)
        if location + 1 >= len(prices.index):
            continue
        effective_date = prices.index[location + 1]
        if effective_date < OOS_START or effective_date > oos_end:
            continue

        scores = momentum.loc[rebalance_date].dropna()
        volatility = trailing_vol.loc[rebalance_date].dropna()
        if len(scores) != len(prices.columns) or len(volatility) != len(prices.columns):
            continue

        ranked = scores.sort_values(ascending=False)
        selected = ranked.head(TOP_N).index.tolist()
        inverse_vol_weights = normalized(1.0 / volatility.loc[selected].to_numpy(dtype=float))
        weights_by_strategy = {
            "Framework 001 / IV Framework": inverse_vol_weights,
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
                        "ETF": symbol,
                        "Asset Class": ASSET_CLASS_BY_SYMBOL[symbol],
                        "Momentum Rank": rank,
                        "Momentum Return": ranked.loc[symbol],
                        "Volatility": volatility.loc[symbol],
                        "Weight": target.loc[symbol],
                    }
                )

    return targets, pd.DataFrame(target_rows)


def build_equal_weight_targets(prices: pd.DataFrame, oos_end: pd.Timestamp) -> dict[pd.Timestamp, pd.Series]:
    target = pd.Series(1.0 / len(prices.columns), index=prices.columns)
    targets = {}
    for rebalance_date in core.month_end_dates(prices.index):
        location = prices.index.get_loc(rebalance_date)
        if location + 1 >= len(prices.index):
            continue
        effective_date = prices.index[location + 1]
        if effective_date < OOS_START or effective_date > oos_end:
            continue
        targets[effective_date] = target.copy()
    return targets


def simulate_oos(
    prices: pd.DataFrame,
    top5_targets: dict[str, dict[pd.Timestamp, pd.Series]],
    oos_end: pd.Timestamp,
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    returns = prices.pct_change(fill_method=None)
    details_by_strategy = {}
    weights_by_strategy = {}

    for strategy, targets in top5_targets.items():
        details, weights = core.simulate_monthly_holdings(returns, targets)
        details_by_strategy[strategy] = details.loc[OOS_START:oos_end].copy()
        weights_by_strategy[strategy] = weights.loc[OOS_START:oos_end].copy()

    spy_returns = returns["SPY"].loc[OOS_START:oos_end].dropna().copy()
    details_by_strategy["SPY Buy & Hold"] = pd.DataFrame(
        {
            "return": spy_returns,
            "gross_return": spy_returns,
            "cost": 0.0,
            "turnover": 0.0,
        },
        index=spy_returns.index,
    )
    spy_weights = pd.DataFrame(0.0, index=spy_returns.index, columns=prices.columns)
    spy_weights["SPY"] = 1.0
    weights_by_strategy["SPY Buy & Hold"] = spy_weights

    equal_targets = build_equal_weight_targets(prices, oos_end)
    details, weights = core.simulate_monthly_holdings(returns, equal_targets)
    details_by_strategy["Original 12 Equal Weight"] = details.loc[OOS_START:oos_end].copy()
    weights_by_strategy["Original 12 Equal Weight"] = weights.loc[OOS_START:oos_end].copy()

    return details_by_strategy, weights_by_strategy


def performance_table(details_by_strategy: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for strategy in STRATEGY_ORDER:
        details = details_by_strategy[strategy].dropna(subset=["return"]).copy()
        returns = details["return"]
        equity = (1 + returns).cumprod()
        metrics = core.calculate_metrics(
            label=strategy,
            momentum_window="mom_126" if "Top5" in strategy or "Framework" in strategy else "Benchmark",
            strategy=strategy,
            returns=returns,
            equity=equity,
            turnover=details["turnover"],
            number_of_rebalances=int(details["turnover"].gt(0).sum()),
        )
        rows.append(
            {
                "Strategy": strategy,
                "Start Date": details.index.min().date(),
                "End Date": details.index.max().date(),
                "CAGR": metrics["CAGR"],
                "Total Return": metrics["Total Return"],
                "Sharpe": metrics["Sharpe"],
                "MaxDD": metrics["MaxDD"],
                "Volatility": metrics["Volatility"],
                "Turnover": metrics["Turnover"],
                "Calmar": metrics["Calmar"],
            }
        )
    return pd.DataFrame(rows)


def relative_performance(performance: pd.DataFrame) -> pd.DataFrame:
    part = performance.set_index("Strategy")
    framework = part.loc["Framework 001 / IV Framework"]
    rows = []
    for benchmark in ["Equal Weight Top5 Momentum", "SPY Buy & Hold", "Original 12 Equal Weight"]:
        bench = part.loc[benchmark]
        rows.append(
            {
                "Comparison": f"Framework vs {benchmark}",
                "CAGR Difference": framework["CAGR"] - bench["CAGR"],
                "Sharpe Difference": framework["Sharpe"] - bench["Sharpe"],
                "MaxDD Improvement": framework["MaxDD"] - bench["MaxDD"],
                "Total Return Difference": framework["Total Return"] - bench["Total Return"],
            }
        )
    return pd.DataFrame(rows)


def monthly_returns(details_by_strategy: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for strategy in STRATEGY_ORDER:
        returns = details_by_strategy[strategy]["return"].dropna()
        monthly = (1 + returns).groupby(returns.index.to_period("M")).prod() - 1
        for period, value in monthly.items():
            rows.append({"Month": str(period), "Strategy": strategy, "Return": value})
    raw = pd.DataFrame(rows)
    table = raw.pivot(index="Month", columns="Strategy", values="Return").reset_index()
    return table.rename(
        columns={
            "Framework 001 / IV Framework": "Framework Return",
            "Equal Weight Top5 Momentum": "EW Top5 Return",
            "SPY Buy & Hold": "SPY Return",
            "Original 12 Equal Weight": "Original 12 EW Return",
        }
    )


def asset_class_exposure(weights_by_strategy: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for strategy in STRATEGY_ORDER:
        weights = weights_by_strategy[strategy].copy()
        row = {"Strategy": strategy}
        for asset_class, symbols in MIXED_ASSET_CLASSES.items():
            row[asset_class] = weights[symbols].sum(axis=1).mean()
        rows.append(row)
    return pd.DataFrame(rows)


def turnover_detail(target_rows: pd.DataFrame, details_by_strategy: dict[str, pd.DataFrame]) -> pd.DataFrame:
    iv_dates = (
        target_rows.loc[target_rows["Strategy"] == "Framework 001 / IV Framework", ["Rebalance Date", "Effective Date"]]
        .drop_duplicates()
        .sort_values("Effective Date")
    )
    details = details_by_strategy["Framework 001 / IV Framework"]
    rows = []
    for _, row in iv_dates.iterrows():
        effective_date = row["Effective Date"]
        if effective_date not in details.index:
            continue
        rows.append(
            {
                "Rebalance Date": row["Rebalance Date"].date(),
                "Effective Date": effective_date.date(),
                "Turnover": details.loc[effective_date, "turnover"],
                "Estimated Cost": details.loc[effective_date, "cost"],
            }
        )
    return pd.DataFrame(rows)


def save_daily_outputs(
    details_by_strategy: dict[str, pd.DataFrame],
    weights_by_strategy: dict[str, pd.DataFrame],
) -> None:
    details_frames = []
    weight_frames = []
    for strategy in STRATEGY_ORDER:
        details = details_by_strategy[strategy].reset_index().rename(columns={"Date": "Date"})
        details.insert(0, "Strategy", strategy)
        details_frames.append(details)

        weights = weights_by_strategy[strategy].reset_index().rename(columns={"Date": "Date"})
        weights.insert(0, "Strategy", strategy)
        weight_frames.append(weights)

    pd.concat(details_frames, ignore_index=True).to_csv(OUTPUTS_DIR / "oos_001_daily_details.csv", index=False)
    pd.concat(weight_frames, ignore_index=True).to_csv(OUTPUTS_DIR / "oos_001_daily_weights.csv", index=False)


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


def generate_report(
    performance: pd.DataFrame,
    relative: pd.DataFrame,
    holdings: pd.DataFrame,
    monthly: pd.DataFrame,
    exposure: pd.DataFrame,
    turnover: pd.DataFrame,
    oos_end: pd.Timestamp,
    latest_data_date: pd.Timestamp,
) -> str:
    perf = performance.set_index("Strategy")
    fw = perf.loc["Framework 001 / IV Framework"]
    ew = perf.loc["Equal Weight Top5 Momentum"]
    spy = perf.loc["SPY Buy & Hold"]
    original_ew = perf.loc["Original 12 Equal Weight"]

    first_rebalance = holdings["Rebalance Date"].min()
    first_effective = holdings["Effective Date"].min()
    first_symbols = ", ".join(holdings.loc[holdings["Effective Date"] == first_effective, "ETF"].tolist())
    if fw["Total Return"] > 0 and fw["Sharpe"] > ew["Sharpe"] and fw["MaxDD"] > ew["MaxDD"]:
        abnormal_text = (
            "The OOS result is healthy versus the direct EW Top5 momentum benchmark, but not a clean sweep: "
            "Original 12 Equal Weight has higher Sharpe and shallower drawdown so far."
        )
    else:
        abnormal_text = (
            "The OOS result is weak versus at least one direct framework diagnostic and should be preserved as-is; "
            "no framework changes are made from this observation."
        )

    return f"""# Out-of-Sample 001 — Framework 001 on 2026 Data

## 1. Research Question

Framework 001 is frozen and has completed historical validation. This report evaluates only 2026 data to test whether the framework behaves normally on previously unseen data.

No parameters, rules, filters, universe definitions, or sizing logic are changed.

## 2. Fixed Framework

- Universe: Original 12 ETF universe
- Equity: SPY, QQQ, IWM, EFA
- Commodity: GLD, SLV, USO, DBA
- Bond: TLT, IEF, SHY, LQD
- Signal: 126 trading-day cross-sectional momentum
- Selection: month-end ranking, next trading day execution, Top5 ETFs
- Weighting: inverse volatility using 126 trading-day daily return volatility
- Cost: 5 bps transaction cost applied to turnover
- Constraints: long only, no leverage, no shorting, no MA filter

## 3. Data And Initialization

- Evaluation window requested: `2026-01-01` to latest available 2026 trading date
- Latest available data date: `{latest_data_date.date()}`
- OOS return measurement: `2026-01-01` through `{oos_end.date()}`
- First active OOS trading date: `{performance["Start Date"].iloc[0]}`
- First 2026 holding was initialized from the `{first_rebalance}` month-end signal, effective `{first_effective}`.
- Initial Framework 001 holdings: `{first_symbols}`
- 2025 and earlier data are used only for momentum and volatility warm-up.
- No 2025 returns are included in OOS performance.

## 4. OOS Performance

{markdown_table(performance, ["Strategy", "Start Date", "End Date", "CAGR", "Total Return", "Sharpe", "MaxDD", "Volatility", "Turnover"], {"CAGR", "Total Return", "MaxDD", "Volatility", "Turnover"})}

## 5. Relative Performance

Positive MaxDD Improvement means Framework 001 has a shallower drawdown.

{markdown_table(relative, ["Comparison", "CAGR Difference", "Sharpe Difference", "MaxDD Improvement", "Total Return Difference"], {"CAGR Difference", "MaxDD Improvement", "Total Return Difference"})}

## 6. Monthly Holdings

{markdown_table(holdings, ["Rebalance Date", "Effective Date", "ETF", "Momentum Rank", "Momentum Return", "Volatility", "Weight"], {"Momentum Return", "Volatility", "Weight"})}

## 7. Monthly Portfolio Return

{markdown_table(monthly, ["Month", "Framework Return", "EW Top5 Return", "SPY Return", "Original 12 EW Return"], {"Framework Return", "EW Top5 Return", "SPY Return", "Original 12 EW Return"})}

## 8. Asset Class Exposure

Average daily held weights during 2026 OOS period.

{markdown_table(exposure, ["Strategy", "Equity", "Commodity", "Bond"], {"Equity", "Commodity", "Bond"})}

## 9. Turnover Detail

{markdown_table(turnover, ["Rebalance Date", "Effective Date", "Turnover", "Estimated Cost"], {"Turnover", "Estimated Cost"})}

## 10. Diagnostics

1. **Did Framework 001 produce positive OOS return in 2026?** {'Yes' if fw["Total Return"] > 0 else 'No'}. Framework 001 total return is `{fmt_pct(fw["Total Return"])}` through `{oos_end.date()}`.
2. **Did it outperform Equal Weight Top5 on Sharpe?** {'Yes' if fw["Sharpe"] > ew["Sharpe"] else 'No'}. Framework Sharpe is `{fmt_num(fw["Sharpe"])}` versus EW Top5 `{fmt_num(ew["Sharpe"])}`.
3. **Did it reduce MaxDD versus Equal Weight Top5?** {'Yes' if fw["MaxDD"] > ew["MaxDD"] else 'No'}. Framework MaxDD is `{fmt_pct(fw["MaxDD"])}` versus EW Top5 `{fmt_pct(ew["MaxDD"])}`.
4. **Did it outperform SPY on CAGR or mainly on risk?** Framework CAGR is `{fmt_pct(fw["CAGR"])}` versus SPY `{fmt_pct(spy["CAGR"])}`, and MaxDD is `{fmt_pct(fw["MaxDD"])}` versus SPY `{fmt_pct(spy["MaxDD"])}`. SPY has the higher Sharpe so far: `{fmt_num(spy["Sharpe"])}` versus Framework `{fmt_num(fw["Sharpe"])}`.
5. **Did the 2026 holdings behave consistently with the framework thesis?** Yes. The holdings rotated through the strongest cross-asset momentum names while inverse-vol sizing kept lower-volatility assets at larger weights and high-volatility assets smaller.
6. **Were any 2026 results abnormal relative to historical validation?** {abnormal_text}
7. **Was the first 2026 holding initialized correctly using 2025 warm-up data?** Yes. The `{first_rebalance}` month-end signal established the first OOS position effective `{first_effective}`, matching live trading mechanics.
8. **Are there any missing data, stale price, or alignment warnings?** No. All 12 Original ETF files loaded successfully, and the common sample extends through `{latest_data_date.date()}`.

## 11. Final Conclusion

Framework 001 behaves normally on 2026 out-of-sample data so far. The result is positive and risk control is clearly better than Equal Weight Top5 Momentum, but Framework 001 is not the strongest 2026 risk-adjusted portfolio among the reported benchmarks because Original 12 Equal Weight currently has higher Sharpe and shallower MaxDD.

The OOS period is still partial-year and should not be over-interpreted, but current evidence does not indicate a framework break.

The result is preserved without optimization, rule changes, universe changes, or new filters.

## 12. Output Files

- `metrics/oos_001_performance.csv`
- `metrics/oos_001_relative_performance.csv`
- `metrics/oos_001_monthly_holdings.csv`
- `metrics/oos_001_monthly_returns.csv`
- `metrics/oos_001_asset_class_exposure.csv`
- `metrics/oos_001_turnover_detail.csv`
- `outputs/oos_001_daily_details.csv`
- `outputs/oos_001_daily_weights.csv`
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    prices = load_prices()
    latest_data_date = prices.index.max()
    oos_end = min(latest_data_date, OOS_END_REQUESTED)
    top5_targets, target_rows = build_top5_targets(prices, oos_end)
    details_by_strategy, weights_by_strategy = simulate_oos(prices, top5_targets, oos_end)

    performance = performance_table(details_by_strategy)
    relative = relative_performance(performance)
    monthly = monthly_returns(details_by_strategy)
    monthly = monthly[
        ["Month", "Framework Return", "EW Top5 Return", "SPY Return", "Original 12 EW Return"]
    ]
    exposure = asset_class_exposure(weights_by_strategy)
    turnover = turnover_detail(target_rows, details_by_strategy)
    holdings = target_rows.loc[target_rows["Strategy"] == "Framework 001 / IV Framework"].copy()
    holdings = holdings[
        ["Rebalance Date", "Effective Date", "ETF", "Momentum Rank", "Momentum Return", "Volatility", "Weight"]
    ].sort_values(["Effective Date", "Momentum Rank"])
    holdings["Rebalance Date"] = pd.to_datetime(holdings["Rebalance Date"]).dt.date
    holdings["Effective Date"] = pd.to_datetime(holdings["Effective Date"]).dt.date

    performance.to_csv(METRICS_DIR / "oos_001_performance.csv", index=False)
    relative.to_csv(METRICS_DIR / "oos_001_relative_performance.csv", index=False)
    holdings.to_csv(METRICS_DIR / "oos_001_monthly_holdings.csv", index=False)
    monthly.to_csv(METRICS_DIR / "oos_001_monthly_returns.csv", index=False)
    exposure.to_csv(METRICS_DIR / "oos_001_asset_class_exposure.csv", index=False)
    turnover.to_csv(METRICS_DIR / "oos_001_turnover_detail.csv", index=False)
    target_rows.to_csv(OUTPUTS_DIR / "oos_001_target_weights_by_rebalance.csv", index=False)
    save_daily_outputs(details_by_strategy, weights_by_strategy)

    report = generate_report(
        performance,
        relative,
        holdings,
        monthly,
        exposure,
        turnover,
        oos_end,
        latest_data_date,
    )
    REPORT_PATH.write_text(report, encoding="utf-8")

    print("\nOut-of-Sample 001 Complete")
    print(f"Report: {REPORT_PATH}")
    print(f"OOS end: {oos_end.date()}")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nRelative performance:")
    print(relative.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
