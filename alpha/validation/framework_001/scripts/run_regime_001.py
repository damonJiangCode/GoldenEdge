from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


ALPHA_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_DIR = ALPHA_ROOT / "validation"
METRICS_DIR = VALIDATION_DIR / "metrics"
OUTPUTS_DIR = VALIDATION_DIR / "outputs"
REPORT_PATH = VALIDATION_DIR / "regime_001_cross_asset_momentum_v1.md"
sys.path.insert(0, str(ALPHA_ROOT))

from shared.configs.universes import MIXED_ASSET_CLASSES, MIXED_ASSET_SYMBOLS  # noqa: E402
from shared.utils import cross_sectional as core  # noqa: E402


MOMENTUM_WINDOW = 126
VOLATILITY_WINDOW = 126
TOP_N = 5
START_DATE = pd.Timestamp("2008-02-01")
END_DATE = pd.Timestamp("2025-12-31")
STRATEGY_ORDER = [
    "Inverse Vol Framework",
    "Equal Weight Top5 Momentum",
    "SPY Buy & Hold",
    "Original 12 Equal Weight",
]
REGIME_ORDER = {
    "SPY Trend Regime": ["SPY Bull Regime", "SPY Bear Regime"],
    "SPY Return Regime": [
        "Strong Equity Regime",
        "Neutral Equity Regime",
        "Weak Equity Regime",
    ],
    "Commodity Regime": [
        "Commodity Bull Regime",
        "Commodity Neutral Regime",
        "Commodity Bear Regime",
    ],
    "Bond Stress Regime": ["Bond Bull Regime", "Bond Neutral Regime", "Bond Bear Regime"],
    "Realized Volatility Regime": [
        "Low Volatility Regime",
        "Medium Volatility Regime",
        "High Volatility Regime",
    ],
}
ASSET_CLASS_BY_SYMBOL = {
    symbol: asset_class for asset_class, symbols in MIXED_ASSET_CLASSES.items() for symbol in symbols
}
DATA_ROOT = ALPHA_ROOT / "shared" / "data"


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


def build_regime_labels(prices: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    full_prices = prices.copy()
    returns = full_prices.pct_change(fill_method=None)
    labels = pd.DataFrame(index=full_prices.loc[START_DATE:END_DATE].index)

    spy_sma200 = full_prices["SPY"].rolling(200, min_periods=200).mean()
    labels["SPY Trend Regime"] = np.where(
        full_prices.loc[labels.index, "SPY"] > spy_sma200.reindex(labels.index),
        "SPY Bull Regime",
        "SPY Bear Regime",
    )
    labels.loc[spy_sma200.reindex(labels.index).isna(), "SPY Trend Regime"] = np.nan

    spy_126 = full_prices["SPY"] / full_prices["SPY"].shift(126) - 1
    spy_126 = spy_126.reindex(labels.index)
    labels["SPY Return Regime"] = "Neutral Equity Regime"
    labels.loc[spy_126 > 0.10, "SPY Return Regime"] = "Strong Equity Regime"
    labels.loc[spy_126 < -0.10, "SPY Return Regime"] = "Weak Equity Regime"
    labels.loc[spy_126.isna(), "SPY Return Regime"] = np.nan

    dbc_126 = full_prices["DBC"] / full_prices["DBC"].shift(126) - 1
    dbc_126 = dbc_126.reindex(labels.index)
    labels["Commodity Regime"] = "Commodity Neutral Regime"
    labels.loc[dbc_126 > 0.10, "Commodity Regime"] = "Commodity Bull Regime"
    labels.loc[dbc_126 < -0.10, "Commodity Regime"] = "Commodity Bear Regime"
    labels.loc[dbc_126.isna(), "Commodity Regime"] = np.nan

    tlt_126 = full_prices["TLT"] / full_prices["TLT"].shift(126) - 1
    tlt_126 = tlt_126.reindex(labels.index)
    labels["Bond Stress Regime"] = "Bond Neutral Regime"
    labels.loc[tlt_126 > 0.10, "Bond Stress Regime"] = "Bond Bull Regime"
    labels.loc[tlt_126 < -0.10, "Bond Stress Regime"] = "Bond Bear Regime"
    labels.loc[tlt_126.isna(), "Bond Stress Regime"] = np.nan

    spy_realized_vol = returns["SPY"].rolling(63, min_periods=63).std(ddof=1) * np.sqrt(core.TRADING_DAYS)
    sample_spy_realized_vol = spy_realized_vol.reindex(labels.index)
    low_threshold = float(sample_spy_realized_vol.dropna().quantile(1 / 3))
    high_threshold = float(sample_spy_realized_vol.dropna().quantile(2 / 3))
    labels["Realized Volatility Regime"] = "Medium Volatility Regime"
    labels.loc[sample_spy_realized_vol <= low_threshold, "Realized Volatility Regime"] = "Low Volatility Regime"
    labels.loc[sample_spy_realized_vol > high_threshold, "Realized Volatility Regime"] = "High Volatility Regime"
    labels.loc[sample_spy_realized_vol.isna(), "Realized Volatility Regime"] = np.nan

    thresholds = {
        "SPY 63d realized volatility low tercile": low_threshold,
        "SPY 63d realized volatility high tercile": high_threshold,
    }
    return labels, thresholds


def load_regime_proxy_prices(base_prices: pd.DataFrame) -> pd.DataFrame:
    prices = base_prices.copy()
    dbc_path = DATA_ROOT / "commodity" / "DBC.csv"
    if not dbc_path.exists():
        raise RuntimeError(f"Missing DBC proxy data for Commodity Regime: {dbc_path}")
    dbc = pd.read_csv(dbc_path, usecols=["Date", "Adj Close"])
    dbc["Date"] = pd.to_datetime(dbc["Date"], errors="coerce")
    dbc["DBC"] = pd.to_numeric(dbc["Adj Close"], errors="coerce")
    dbc = dbc.dropna(subset=["Date", "DBC"]).sort_values("Date").drop_duplicates("Date", keep="last")
    dbc = dbc.set_index("Date")["DBC"]
    prices["DBC"] = dbc.reindex(prices.index).ffill()
    if prices["DBC"].isna().any():
        first_missing = prices.index[prices["DBC"].isna()][0].date()
        raise RuntimeError(f"DBC proxy is unavailable on required date: {first_missing}")
    return prices


def regime_metrics(returns: pd.Series) -> dict[str, float]:
    returns = returns.dropna()
    days = len(returns)
    if days == 0:
        return {
            "Days": 0,
            "CAGR": np.nan,
            "Sharpe": np.nan,
            "MaxDD": np.nan,
            "Volatility": np.nan,
            "Total Return": np.nan,
        }
    equity = (1 + returns).cumprod()
    total_return = equity.iloc[-1] - 1
    cagr = (1 + total_return) ** (core.TRADING_DAYS / days) - 1 if total_return > -1 else np.nan
    volatility = returns.std(ddof=1) * np.sqrt(core.TRADING_DAYS) if days > 1 else np.nan
    sharpe = returns.mean() * core.TRADING_DAYS / volatility if volatility and not pd.isna(volatility) else np.nan
    return {
        "Days": days,
        "CAGR": cagr,
        "Sharpe": sharpe,
        "MaxDD": core.max_drawdown(equity),
        "Volatility": volatility,
        "Total Return": total_return,
    }


def regime_performance(
    labels: pd.DataFrame,
    details_by_strategy: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    rows = []
    for regime_set, regimes in REGIME_ORDER.items():
        regime_series = labels[regime_set].dropna()
        for regime in regimes:
            regime_dates = regime_series.index[regime_series == regime]
            for strategy in STRATEGY_ORDER:
                daily = details_by_strategy[strategy]["return"].reindex(regime_dates).dropna()
                row = {"Regime Set": regime_set, "Regime": regime, "Strategy": strategy}
                row.update(regime_metrics(daily))
                rows.append(row)
    return pd.DataFrame(rows)


def relative_performance(performance: pd.DataFrame, benchmark: str, suffix: str) -> pd.DataFrame:
    rows = []
    grouped = performance.set_index(["Regime Set", "Regime", "Strategy"])
    for regime_set, regimes in REGIME_ORDER.items():
        for regime in regimes:
            iv = grouped.loc[(regime_set, regime, "Inverse Vol Framework")]
            bench = grouped.loc[(regime_set, regime, benchmark)]
            rows.append(
                {
                    "Regime Set": regime_set,
                    "Regime": regime,
                    f"IV Sharpe - {suffix} Sharpe": iv["Sharpe"] - bench["Sharpe"],
                    f"IV MaxDD Improvement vs {suffix}": iv["MaxDD"] - bench["MaxDD"],
                    f"IV CAGR - {suffix} CAGR": iv["CAGR"] - bench["CAGR"],
                }
            )
    return pd.DataFrame(rows)


def asset_class_exposure(labels: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    rows = []
    weights = weights["Inverse Vol Framework"].copy()
    for regime_set, regimes in REGIME_ORDER.items():
        regime_series = labels[regime_set].dropna()
        for regime in regimes:
            regime_dates = regime_series.index[regime_series == regime]
            part = weights.reindex(regime_dates).dropna(how="all")
            row = {"Regime Set": regime_set, "Regime": regime}
            for asset_class, symbols in MIXED_ASSET_CLASSES.items():
                row[f"{asset_class} Weight"] = part[symbols].sum(axis=1).mean()
            rows.append(row)
    return pd.DataFrame(rows)


def etf_exposure(labels: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    rows = []
    weights = weights["Inverse Vol Framework"].copy()
    for regime_set, regimes in REGIME_ORDER.items():
        regime_series = labels[regime_set].dropna()
        for regime in regimes:
            regime_dates = regime_series.index[regime_series == regime]
            part = weights.reindex(regime_dates).dropna(how="all")
            averages = part[MIXED_ASSET_SYMBOLS].mean()
            for symbol in MIXED_ASSET_SYMBOLS:
                rows.append(
                    {
                        "Regime Set": regime_set,
                        "Regime": regime,
                        "ETF": symbol,
                        "Asset Class": ASSET_CLASS_BY_SYMBOL[symbol],
                        "Average Weight": averages.loc[symbol],
                    }
                )
    return pd.DataFrame(rows)


def regime_contribution(labels: pd.DataFrame, details: pd.DataFrame) -> pd.DataFrame:
    daily = details["Inverse Vol Framework"]["return"]
    total_sum_return = daily.sum()
    rows = []
    for regime_set, regimes in REGIME_ORDER.items():
        regime_series = labels[regime_set].dropna()
        for regime in regimes:
            regime_dates = regime_series.index[regime_series == regime]
            contribution = daily.reindex(regime_dates).dropna().sum()
            rows.append(
                {
                    "Regime Set": regime_set,
                    "Regime": regime,
                    "Contribution To Total Return": contribution,
                    "Contribution Percent": contribution / total_sum_return if total_sum_return != 0 else np.nan,
                }
            )
    return pd.DataFrame(rows)


def top_etfs(etf_exposures: pd.DataFrame, regime_set: str, regime: str, n: int = 5) -> str:
    part = etf_exposures[
        (etf_exposures["Regime Set"] == regime_set) & (etf_exposures["Regime"] == regime)
    ].sort_values("Average Weight", ascending=False)
    return ", ".join(
        f"{row['ETF']} {fmt_pct(row['Average Weight'])}" for _, row in part.head(n).iterrows()
    )


def best_and_worst_regimes(performance: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    iv = performance.loc[performance["Strategy"] == "Inverse Vol Framework"].copy()
    best = iv.sort_values(["Sharpe", "CAGR"], ascending=[False, False]).head(5)
    worst = iv.sort_values(["Sharpe", "CAGR"], ascending=[True, True]).head(5)
    return best, worst


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


def compact_performance(performance: pd.DataFrame, regime_set: str) -> pd.DataFrame:
    return performance.loc[performance["Regime Set"] == regime_set].copy()


def generate_report(
    performance: pd.DataFrame,
    relative_ew: pd.DataFrame,
    relative_spy: pd.DataFrame,
    class_exposure: pd.DataFrame,
    etf_exposures: pd.DataFrame,
    contribution: pd.DataFrame,
    thresholds: dict[str, float],
) -> str:
    perf_index = performance.set_index(["Regime Set", "Regime", "Strategy"])
    rel_ew_index = relative_ew.set_index(["Regime Set", "Regime"])
    rel_spy_index = relative_spy.set_index(["Regime Set", "Regime"])
    contrib_sorted = contribution.sort_values("Contribution To Total Return", ascending=False)
    best, worst = best_and_worst_regimes(performance)
    high_vol = perf_index.loc[("Realized Volatility Regime", "High Volatility Regime", "Inverse Vol Framework")]
    high_vol_ew = rel_ew_index.loc[("Realized Volatility Regime", "High Volatility Regime")]
    spy_bear = perf_index.loc[("SPY Trend Regime", "SPY Bear Regime", "Inverse Vol Framework")]
    spy_bear_vs_spy = rel_spy_index.loc[("SPY Trend Regime", "SPY Bear Regime")]
    commodity_bull = perf_index.loc[("Commodity Regime", "Commodity Bull Regime", "Inverse Vol Framework")]
    bond_bear = perf_index.loc[("Bond Stress Regime", "Bond Bear Regime", "Inverse Vol Framework")]
    strong_equity = perf_index.loc[("SPY Return Regime", "Strong Equity Regime", "Inverse Vol Framework")]
    weak_equity = perf_index.loc[("SPY Return Regime", "Weak Equity Regime", "Inverse Vol Framework")]

    best_table = best[["Regime Set", "Regime", "Days", "CAGR", "Sharpe", "MaxDD", "Total Return"]]
    worst_table = worst[["Regime Set", "Regime", "Days", "CAGR", "Sharpe", "MaxDD", "Total Return"]]
    top_contrib = contrib_sorted.head(6)

    return f"""# Regime Analysis 001 — Cross-Asset Momentum Framework V1

## 1. Research Question

Framework 001 has passed Walk Forward Validation. This report asks how the frozen framework behaves across objective market regimes: where it earns returns, where it is weak, which asset classes carry it, and whether the result depends on one market state.

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

## 3. Regime Definitions

All regimes are rule-based and calculated from data available at each date. This analysis uses daily regime labels from `{START_DATE.date()}` to `{END_DATE.date()}`.

- **SPY Trend Regime:** SPY Adj Close above or below/equal to SPY SMA200.
- **SPY Return Regime:** trailing 126-day SPY return above +10%, below -10%, or neutral.
- **Commodity Regime:** trailing 126-day DBC return above +10%, below -10%, or neutral. DBC is used only as an external Commodity regime proxy; it is not part of the Original 12 ETF trading universe.
- **Bond Stress Regime:** trailing 126-day TLT return above +10%, below -10%, or neutral.
- **Realized Volatility Regime:** full-sample terciles of trailing 63-day SPY realized volatility. Low threshold = {fmt_pct(thresholds['SPY 63d realized volatility low tercile'])}; high threshold = {fmt_pct(thresholds['SPY 63d realized volatility high tercile'])}.

Performance is calculated by compressing the daily returns belonging to each regime state. CAGR is annualized by the number of regime days, not by calendar span. This makes the table answer: when this state occurs, how does the strategy behave?

## 4. Regime Performance

### SPY Trend Regime

{markdown_table(compact_performance(performance, 'SPY Trend Regime'), ['Regime Set', 'Regime', 'Strategy', 'Days', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Total Return'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return'})}

### SPY Return Regime

{markdown_table(compact_performance(performance, 'SPY Return Regime'), ['Regime Set', 'Regime', 'Strategy', 'Days', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Total Return'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return'})}

### Commodity Regime

{markdown_table(compact_performance(performance, 'Commodity Regime'), ['Regime Set', 'Regime', 'Strategy', 'Days', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Total Return'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return'})}

### Bond Stress Regime

{markdown_table(compact_performance(performance, 'Bond Stress Regime'), ['Regime Set', 'Regime', 'Strategy', 'Days', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Total Return'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return'})}

### Realized Volatility Regime

{markdown_table(compact_performance(performance, 'Realized Volatility Regime'), ['Regime Set', 'Regime', 'Strategy', 'Days', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Total Return'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return'})}

## 5. Relative Performance vs Equal Weight Top5

Positive MaxDD Improvement means IV has shallower drawdown.

{markdown_table(relative_ew, ['Regime Set', 'Regime', 'IV Sharpe - EW Sharpe', 'IV MaxDD Improvement vs EW', 'IV CAGR - EW CAGR'], {'IV MaxDD Improvement vs EW', 'IV CAGR - EW CAGR'})}

## 6. Relative Performance vs SPY

Positive MaxDD Improvement means IV has shallower drawdown.

{markdown_table(relative_spy, ['Regime Set', 'Regime', 'IV Sharpe - SPY Sharpe', 'IV MaxDD Improvement vs SPY', 'IV CAGR - SPY CAGR'], {'IV MaxDD Improvement vs SPY', 'IV CAGR - SPY CAGR'})}

## 7. Asset Class Exposure by Regime

Framework 001 average daily weights.

{markdown_table(class_exposure, ['Regime Set', 'Regime', 'Equity Weight', 'Commodity Weight', 'Bond Weight'], {'Equity Weight', 'Commodity Weight', 'Bond Weight'})}

## 8. ETF Exposure by Regime

Full ETF exposure is saved to CSV. The highest average weights in selected key regimes:

| Regime Set | Regime | Top ETF Weights |
| --- | --- | --- |
| SPY Trend Regime | SPY Bear Regime | {top_etfs(etf_exposures, 'SPY Trend Regime', 'SPY Bear Regime')} |
| SPY Return Regime | Weak Equity Regime | {top_etfs(etf_exposures, 'SPY Return Regime', 'Weak Equity Regime')} |
| Commodity Regime | Commodity Bull Regime | {top_etfs(etf_exposures, 'Commodity Regime', 'Commodity Bull Regime')} |
| Bond Stress Regime | Bond Bear Regime | {top_etfs(etf_exposures, 'Bond Stress Regime', 'Bond Bear Regime')} |
| Realized Volatility Regime | High Volatility Regime | {top_etfs(etf_exposures, 'Realized Volatility Regime', 'High Volatility Regime')} |

## 9. Regime Contribution

Contribution uses additive daily net return contribution: the sum of IV Framework daily returns in each regime divided by the full-sample sum of IV Framework daily returns. It is not a compounded wealth attribution, but it is additive across regimes within each regime set.

{markdown_table(contribution, ['Regime Set', 'Regime', 'Contribution To Total Return', 'Contribution Percent'], {'Contribution To Total Return', 'Contribution Percent'})}

Top contribution states:

{markdown_table(top_contrib, ['Regime Set', 'Regime', 'Contribution To Total Return', 'Contribution Percent'], {'Contribution To Total Return', 'Contribution Percent'})}

## 10. Best and Weakest Regimes

Best IV Framework regimes by Sharpe:

{markdown_table(best_table, ['Regime Set', 'Regime', 'Days', 'CAGR', 'Sharpe', 'MaxDD', 'Total Return'], {'CAGR', 'MaxDD', 'Total Return'})}

Weakest IV Framework regimes by Sharpe:

{markdown_table(worst_table, ['Regime Set', 'Regime', 'Days', 'CAGR', 'Sharpe', 'MaxDD', 'Total Return'], {'CAGR', 'MaxDD', 'Total Return'})}

## 11. Interpretation Questions

1. **In which regimes does Framework 001 perform best?** The strongest states are risk-on but not one-dimensional: Bond Bull, Medium Volatility, Commodity Bull, and SPY Bull / Strong Equity regimes all rank well. The best single Sharpe state is `{best.iloc[0]['Regime Set']} / {best.iloc[0]['Regime']}` with Sharpe {fmt_num(best.iloc[0]['Sharpe'])}.
2. **In which regimes is it weakest?** The weakest states are `{worst.iloc[0]['Regime Set']} / {worst.iloc[0]['Regime']}` and other stress states where major sleeves are simultaneously under pressure. Weak Equity has CAGR {fmt_pct(weak_equity['CAGR'])} and Sharpe {fmt_num(weak_equity['Sharpe'])}.
3. **Does Framework 001 depend mainly on equity bull markets?** For absolute net contribution, yes, SPY Bull / Strong Equity states are the dominant return contributors. But the framework is not simply SPY beta: Commodity Bull and Bond Bull states also show strong Sharpe, and bear-state losses are much smaller than SPY. In SPY Bull, Equity exposure averages {fmt_pct(class_exposure.set_index(['Regime Set', 'Regime']).loc[('SPY Trend Regime', 'SPY Bull Regime'), 'Equity Weight'])}; the framework still keeps meaningful Commodity/Bond exposure.
4. **Does it protect capital during SPY bear regimes?** Yes relative to SPY and Equal Weight Top5. In SPY Bear, IV MaxDD is {fmt_pct(spy_bear['MaxDD'])}; MaxDD improvement versus SPY is {fmt_pct(spy_bear_vs_spy['IV MaxDD Improvement vs SPY'])}. Absolute CAGR is {fmt_pct(spy_bear['CAGR'])}, so it is defensive but not immune.
5. **Does it benefit from commodity bull regimes?** Yes. Commodity Bull CAGR is {fmt_pct(commodity_bull['CAGR'])}, Sharpe {fmt_num(commodity_bull['Sharpe'])}. Commodity sleeve exposure rises to {fmt_pct(class_exposure.set_index(['Regime Set', 'Regime']).loc[('Commodity Regime', 'Commodity Bull Regime'), 'Commodity Weight'])}, while the top individual weights remain mixed across Equity and Commodity: {top_etfs(etf_exposures, 'Commodity Regime', 'Commodity Bull Regime')}.
6. **How does it behave during bond bear regimes?** Bond Bear is manageable but not the best environment: CAGR {fmt_pct(bond_bear['CAGR'])}, Sharpe {fmt_num(bond_bear['Sharpe'])}, MaxDD {fmt_pct(bond_bear['MaxDD'])}. The framework reduces reliance on Bonds and leans more into Equity/Commodity winners.
7. **Does inverse-vol weighting add the most value during high-volatility regimes?** Yes. In High Volatility, IV Sharpe minus Equal Weight Sharpe is {fmt_num(high_vol_ew['IV Sharpe - EW Sharpe'])}, and MaxDD improvement is {fmt_pct(high_vol_ew['IV MaxDD Improvement vs EW'])}. This is where sizing discipline is most visibly useful.
8. **Which asset classes dominate in each regime?** SPY Bull and Strong Equity states have higher Equity exposure; Commodity Bull shifts more weight to Commodity; SPY Bear, Weak Equity, and Bond Bull states show higher Bond exposure. The allocation is regime-adaptive rather than static.
9. **Which ETFs are most important in each regime?** In stress and weak-equity states, SHY and IEF are central, with GLD often present as an additional diversifier. In Commodity Bull, DBA and other Commodity sleeve members gain more weight but Equity winners can still remain among the largest positions. In Equity Bull states, SPY/QQQ/IWM/EFA participate more heavily.
10. **Does regime analysis support the framework thesis?** Yes, with nuance. The framework has a reasonable regime profile: it earns most absolute return during favorable risk-asset regimes, but it materially controls drawdown in adverse regimes and rotates exposure across Equity, Commodity, and Bond sleeves.

## 12. Final Conclusion

Framework 001 has a reasonable regime profile. Its absolute return is not evenly distributed: SPY Bull and Strong Equity states are the largest contributors. The important validation result is that performance is not explained by raw equity beta alone. Commodity Bull, Bond Bull, Medium Volatility, and High Volatility states also show useful behavior, while SPY Bear and Weak Equity losses are materially shallower than SPY and Equal Weight Top5.

The evidence supports the framework thesis: Cross-Asset Momentum plus Inverse Volatility behaves like a regime-adaptive allocation system with strong participation in risk-on markets and meaningful risk control in stress markets. It still does not maximize SPY CAGR in strong equity markets, and it is not crisis-proof. But the regime behavior is coherent enough to proceed to deeper validation.

Next validation candidates:

- Bootstrap
- Monte Carlo
- Paper Trading Simulation

## 13. Output Files

- Regime labels: `alpha/validation/outputs/regime_001_labels.csv`
- Regime performance: `alpha/validation/metrics/regime_001_performance.csv`
- Relative vs Equal Weight Top5: `alpha/validation/metrics/regime_001_relative_vs_equal_weight.csv`
- Relative vs SPY: `alpha/validation/metrics/regime_001_relative_vs_spy.csv`
- Asset-class exposure: `alpha/validation/metrics/regime_001_asset_class_exposure.csv`
- ETF exposure: `alpha/validation/metrics/regime_001_etf_exposure.csv`
- Regime contribution: `alpha/validation/metrics/regime_001_contribution.csv`
- Daily details: `alpha/validation/outputs/regime_001_daily_details.csv`
- Daily weights: `alpha/validation/outputs/regime_001_daily_weights.csv`
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    prices = core.load_prices().loc[:END_DATE, MIXED_ASSET_SYMBOLS]
    regime_prices = load_regime_proxy_prices(prices)
    returns = prices.pct_change(fill_method=None).fillna(0.0)

    top5_targets, target_rows = build_top5_targets(prices)
    details_by_strategy, weights_by_strategy = simulate_strategies(prices, returns, top5_targets)
    labels, thresholds = build_regime_labels(regime_prices)

    performance = regime_performance(labels, details_by_strategy)
    relative_ew = relative_performance(performance, "Equal Weight Top5 Momentum", "EW")
    relative_spy = relative_performance(performance, "SPY Buy & Hold", "SPY")
    class_exposure = asset_class_exposure(labels, weights_by_strategy)
    etf_exposures = etf_exposure(labels, weights_by_strategy)

    combined_details = pd.concat(details_by_strategy, axis=1)
    combined_details.columns = [
        f"{strategy}::{field}" for strategy, field in combined_details.columns.to_flat_index()
    ]
    combined_weights = pd.concat(weights_by_strategy, axis=1)
    combined_weights.columns = [
        f"{strategy}::{symbol}" for strategy, symbol in combined_weights.columns.to_flat_index()
    ]
    contribution = regime_contribution(labels, details_by_strategy)

    labels.to_csv(OUTPUTS_DIR / "regime_001_labels.csv")
    performance.to_csv(METRICS_DIR / "regime_001_performance.csv", index=False)
    relative_ew.to_csv(METRICS_DIR / "regime_001_relative_vs_equal_weight.csv", index=False)
    relative_spy.to_csv(METRICS_DIR / "regime_001_relative_vs_spy.csv", index=False)
    class_exposure.to_csv(METRICS_DIR / "regime_001_asset_class_exposure.csv", index=False)
    etf_exposures.to_csv(METRICS_DIR / "regime_001_etf_exposure.csv", index=False)
    contribution.to_csv(METRICS_DIR / "regime_001_contribution.csv", index=False)
    target_rows.to_csv(OUTPUTS_DIR / "regime_001_target_weights_by_rebalance.csv", index=False)
    combined_details.to_csv(OUTPUTS_DIR / "regime_001_daily_details.csv")
    combined_weights.to_csv(OUTPUTS_DIR / "regime_001_daily_weights.csv")

    REPORT_PATH.write_text(
        generate_report(
            performance,
            relative_ew,
            relative_spy,
            class_exposure,
            etf_exposures,
            contribution,
            thresholds,
        ),
        encoding="utf-8",
    )

    print("\nRegime Analysis 001 Complete")
    print("\nBest IV regimes:")
    best, worst = best_and_worst_regimes(performance)
    print(best[["Regime Set", "Regime", "Days", "CAGR", "Sharpe", "MaxDD"]].to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nWeakest IV regimes:")
    print(worst[["Regime Set", "Regime", "Days", "CAGR", "Sharpe", "MaxDD"]].to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nHigh-vol relative vs EW:")
    high = relative_ew[
        (relative_ew["Regime Set"] == "Realized Volatility Regime")
        & (relative_ew["Regime"] == "High Volatility Regime")
    ]
    print(high.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
