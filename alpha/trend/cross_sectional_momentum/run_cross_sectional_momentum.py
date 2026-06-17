from __future__ import annotations

import math
import warnings
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "trend" / "cross_sectional_momentum" / "results"

ASSET_CLASSES = ["equity", "commodity", "bond"]
MOMENTUM_WINDOWS = [63, 126]
TOP_N_VALUES = [1, 3, 5]
TRADING_DAYS = 252
TRADING_COST = 0.0005
REQUIRED_COLUMNS = ["Date", "Adj Close"]
BENCHMARK_SPY = "SPY"
SYMBOL_ORDER = ["SPY", "QQQ", "IWM", "EFA", "GLD", "SLV", "USO", "DBA", "TLT", "IEF", "SHY", "LQD"]


def discover_data_files() -> list[tuple[str, Path]]:
    files = []
    for asset_class in ASSET_CLASSES:
        asset_dir = DATA_ROOT / asset_class
        if not asset_dir.exists():
            warnings.warn(f"Missing asset class directory: {asset_dir}")
            continue
        for path in sorted(asset_dir.glob("*.csv")):
            if path.stem in SYMBOL_ORDER:
                files.append((asset_class, path))
    return files


def load_price_data(path: Path, asset_class: str) -> Optional[pd.DataFrame]:
    symbol = path.stem
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        warnings.warn(f"{symbol}: failed to read {path}: {exc}")
        return None

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        warnings.warn(f"{symbol}: missing columns {missing}, skipped")
        return None

    df = df[REQUIRED_COLUMNS].copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df[symbol] = pd.to_numeric(df["Adj Close"], errors="coerce")
    df = df.dropna(subset=["Date", symbol]).sort_values("Date")
    df = df.drop_duplicates(subset=["Date"], keep="last").set_index("Date")
    df["asset_class"] = asset_class
    return df[[symbol]]


def load_prices() -> pd.DataFrame:
    frames = []
    loaded_symbols = []
    for asset_class, path in discover_data_files():
        df = load_price_data(path, asset_class)
        if df is None:
            continue
        frames.append(df)
        loaded_symbols.append(path.stem)

    missing_symbols = sorted(set(SYMBOL_ORDER) - set(loaded_symbols))
    if missing_symbols:
        warnings.warn(f"Missing requested symbols: {missing_symbols}")

    if not frames:
        raise RuntimeError("No valid price data loaded.")

    prices = pd.concat(frames, axis=1).sort_index()
    ordered_cols = [symbol for symbol in SYMBOL_ORDER if symbol in prices.columns]
    prices = prices[ordered_cols]
    prices = prices.dropna(how="any")

    if len(prices.columns) != len(SYMBOL_ORDER):
        raise RuntimeError(f"Expected {len(SYMBOL_ORDER)} symbols, got {len(prices.columns)}.")
    if len(prices) <= max(MOMENTUM_WINDOWS) + 40:
        raise RuntimeError("Not enough overlapping history across all symbols.")

    return prices


def month_end_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    date_series = pd.Series(index=index, data=index)
    return pd.DatetimeIndex(date_series.groupby(index.to_period("M")).max().values)


def max_drawdown(equity: pd.Series) -> float:
    equity = equity.dropna()
    if equity.empty:
        return np.nan
    return (equity / equity.cummax() - 1).min()


def annualized_return(equity: pd.Series) -> float:
    equity = equity.dropna()
    if len(equity) <= 1:
        return np.nan
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years <= 0:
        return np.nan
    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    if total_return <= -1:
        return np.nan
    return (1 + total_return) ** (1 / years) - 1


def annualized_volatility(returns: pd.Series) -> float:
    returns = returns.dropna()
    if len(returns) <= 1:
        return np.nan
    return returns.std(ddof=1) * math.sqrt(TRADING_DAYS)


def sharpe_ratio(returns: pd.Series) -> float:
    returns = returns.dropna()
    vol = annualized_volatility(returns)
    if pd.isna(vol) or vol == 0:
        return np.nan
    return returns.mean() * TRADING_DAYS / vol


def calmar_ratio(cagr: float, maxdd: float) -> float:
    if pd.isna(cagr) or pd.isna(maxdd) or maxdd == 0:
        return np.nan
    return cagr / abs(maxdd)


def calculate_metrics(
    label: str,
    momentum_window: str,
    strategy: str,
    returns: pd.Series,
    equity: pd.Series,
    turnover: pd.Series,
    number_of_rebalances: int,
) -> dict:
    cagr = annualized_return(equity)
    maxdd = max_drawdown(equity)
    volatility = annualized_volatility(returns)
    return {
        "label": label,
        "momentum_window": momentum_window,
        "strategy": strategy,
        "CAGR": cagr,
        "Sharpe": sharpe_ratio(returns),
        "MaxDD": maxdd,
        "Volatility": volatility,
        "Calmar": calmar_ratio(cagr, maxdd),
        "Total Return": equity.iloc[-1] - 1 if len(equity) else np.nan,
        "Turnover": turnover.sum(),
        "Number of Rebalances": number_of_rebalances,
    }


def build_strategy(
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    momentum: pd.DataFrame,
    rebalance_dates: pd.DatetimeIndex,
    window: int,
    top_n: int,
) -> tuple[pd.Series, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ranking_rows = []
    holding_rows = []

    target_weights_by_date: dict[pd.Timestamp, pd.Series] = {}
    valid_rebalances = 0

    for i, rebalance_date in enumerate(rebalance_dates):
        if rebalance_date not in momentum.index:
            continue
        scores = momentum.loc[rebalance_date].dropna()
        if len(scores) != len(prices.columns):
            warnings.warn(f"{rebalance_date.date()} mom_{window}: incomplete momentum scores, skipped")
            continue

        ranked = scores.sort_values(ascending=False)
        selected = ranked.head(top_n).index.tolist()
        new_weights = pd.Series(0.0, index=prices.columns)
        new_weights.loc[selected] = 1.0 / top_n

        rebalance_loc = prices.index.get_loc(rebalance_date)
        start_loc = rebalance_loc + 1
        if start_loc >= len(prices.index):
            continue

        effective_date = prices.index[start_loc]
        target_weights_by_date[effective_date] = new_weights
        valid_rebalances += 1

        for rank, (symbol, score) in enumerate(ranked.items(), start=1):
            ranking_rows.append(
                {
                    "Date": rebalance_date,
                    "effective_date": effective_date,
                    "momentum_window": f"mom_{window}",
                    "strategy": f"Top{top_n}",
                    "symbol": symbol,
                    "rank": rank,
                    "momentum": score,
                    "selected": symbol in selected,
                    "weight": new_weights.loc[symbol],
                }
            )
        for symbol in selected:
            holding_rows.append(
                {
                    "rebalance_date": rebalance_date,
                    "effective_date": effective_date,
                    "momentum_window": f"mom_{window}",
                    "strategy": f"Top{top_n}",
                    "symbol": symbol,
                    "rank": int(ranked.index.get_loc(symbol) + 1),
                    "momentum": ranked.loc[symbol],
                    "weight": new_weights.loc[symbol],
                }
            )

    details, weights = simulate_monthly_holdings(returns, target_weights_by_date)
    if not holding_rows:
        holdings = pd.DataFrame()
    else:
        holdings = pd.DataFrame(holding_rows)
        turnover_cost = details[["turnover", "cost"]].reset_index().rename(columns={"Date": "effective_date"})
        holdings = holdings.merge(turnover_cost, on="effective_date", how="left")
    strategy_returns = details["return"]
    ranking = pd.DataFrame(ranking_rows)
    details.attrs["number_of_rebalances"] = valid_rebalances
    return strategy_returns, details, ranking, holdings


def simulate_monthly_holdings(
    returns: pd.DataFrame,
    target_weights_by_date: dict[pd.Timestamp, pd.Series],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not target_weights_by_date:
        empty = pd.DataFrame(columns=["return", "gross_return", "cost", "turnover"])
        return empty, pd.DataFrame(columns=returns.columns)

    start_date = min(target_weights_by_date)
    active_returns = returns.loc[start_date:].copy()
    current_weights = pd.Series(0.0, index=returns.columns)
    detail_rows = []
    weight_rows = []

    for date, asset_returns in active_returns.iterrows():
        target_weights = target_weights_by_date.get(date)
        if target_weights is not None:
            current_turnover = float((target_weights - current_weights).abs().sum())
            current_cost = current_turnover * TRADING_COST
            current_weights = target_weights.copy()
        else:
            current_turnover = 0.0
            current_cost = 0.0

        gross_return = float((current_weights * asset_returns).sum())
        net_return = gross_return - current_cost
        detail_rows.append(
            {
                "Date": date,
                "return": net_return,
                "gross_return": gross_return,
                "cost": current_cost,
                "turnover": current_turnover,
            }
        )
        weight_rows.append({"Date": date, **current_weights.to_dict()})

        denominator = 1 + gross_return
        if denominator > 0:
            current_weights = current_weights * (1 + asset_returns) / denominator
        else:
            current_weights = pd.Series(0.0, index=returns.columns)

    details = pd.DataFrame(detail_rows).set_index("Date")
    weights = pd.DataFrame(weight_rows).set_index("Date")
    return details, weights


def build_equal_weight_benchmark(
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    rebalance_dates: pd.DatetimeIndex,
) -> tuple[pd.Series, pd.Series, int]:
    target_weights_by_date: dict[pd.Timestamp, pd.Series] = {}
    equal_weights = pd.Series(1.0 / len(prices.columns), index=prices.columns)
    rebalances = 0

    for rebalance_date in rebalance_dates:
        start_loc = prices.index.get_loc(rebalance_date) + 1
        if start_loc >= len(prices.index):
            continue
        effective_date = prices.index[start_loc]
        target_weights_by_date[effective_date] = equal_weights
        rebalances += 1

    details, _ = simulate_monthly_holdings(returns, target_weights_by_date)
    return details["return"], details["turnover"], rebalances


def monthly_returns(daily_returns: pd.Series) -> pd.Series:
    return (1 + daily_returns).groupby(daily_returns.index.to_period("M")).prod() - 1


def benchmark_comparison(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
    strategy_label: str,
    benchmark_label: str,
) -> dict:
    strategy_monthly = monthly_returns(strategy_returns)
    benchmark_monthly = monthly_returns(benchmark_returns)
    aligned = pd.concat([strategy_monthly, benchmark_monthly], axis=1, join="inner").dropna()
    aligned.columns = ["strategy", "benchmark"]
    excess = aligned["strategy"] - aligned["benchmark"]
    if len(excess) > 1 and excess.std(ddof=1) > 0:
        t_result = stats.ttest_1samp(excess, popmean=0.0)
        t_statistic = t_result.statistic
        p_value = t_result.pvalue
    else:
        t_statistic = np.nan
        p_value = np.nan

    return {
        "strategy_label": strategy_label,
        "benchmark": benchmark_label,
        "monthly_observations": len(excess),
        "avg_monthly_excess": excess.mean() if len(excess) else np.nan,
        "annualized_excess": (1 + excess.mean()) ** 12 - 1 if len(excess) else np.nan,
        "win_rate_vs_benchmark": (excess > 0).mean() if len(excess) else np.nan,
        "t_statistic": t_statistic,
        "p_value": p_value,
    }


def summarize_selection(ranking_history: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (momentum_window, strategy, symbol), part in ranking_history.groupby(
        ["momentum_window", "strategy", "symbol"]
    ):
        rows.append(
            {
                "momentum_window": momentum_window,
                "strategy": strategy,
                "symbol": symbol,
                "Average Rank": part["rank"].mean(),
                "Selection Count": int(part["selected"].sum()),
                "Selection Percentage": part["selected"].mean(),
            }
        )
    return pd.DataFrame(rows).sort_values(["momentum_window", "strategy", "Selection Count"], ascending=[True, True, False])


def drawdown(equity: pd.Series) -> pd.Series:
    return equity / equity.cummax() - 1


def plot_equity_curves(equity_curves: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(14, 8))
    for col in equity_curves.columns:
        linewidth = 2.2 if col in ["Benchmark_SPY", "Benchmark_EqualWeight"] else 1.4
        linestyle = "--" if col.startswith("Benchmark") else "-"
        ax.plot(equity_curves.index, equity_curves[col], label=col, linewidth=linewidth, linestyle=linestyle)
    ax.set_title("Cross-Sectional Momentum Equity Curves")
    ax.set_ylabel("Growth of $1")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "equity_curves.png", dpi=150)
    plt.close(fig)


def plot_drawdowns(equity_curves: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(14, 8))
    for col in equity_curves.columns:
        ax.plot(equity_curves.index, drawdown(equity_curves[col]), label=col, linewidth=1.3)
    ax.set_title("Cross-Sectional Momentum Drawdowns")
    ax.set_ylabel("Drawdown")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "drawdowns.png", dpi=150)
    plt.close(fig)


def plot_rolling_12m_returns(daily_returns: pd.DataFrame) -> pd.DataFrame:
    rolling = (1 + daily_returns).rolling(TRADING_DAYS).apply(np.prod, raw=True) - 1
    fig, ax = plt.subplots(figsize=(14, 8))
    for col in rolling.columns:
        ax.plot(rolling.index, rolling[col], label=col, linewidth=1.2)
    ax.axhline(0, color="black", linewidth=0.8, alpha=0.5)
    ax.set_title("Rolling 12 Month Return")
    ax.set_ylabel("Rolling 12M Return")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "rolling_12m_returns.png", dpi=150)
    plt.close(fig)
    return rolling


def fmt_pct(value: float) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.2%}"


def fmt_num(value: float) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.2f}"


def markdown_table(df: pd.DataFrame, columns: list[str], pct_columns: set[str]) -> str:
    if df.empty:
        return "_No data._"
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df[columns].iterrows():
        cells = []
        for col in columns:
            value = row[col]
            if col in pct_columns:
                cells.append(fmt_pct(value))
            elif isinstance(value, (float, np.floating)):
                cells.append(fmt_num(value))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def generate_summary(
    metrics: pd.DataFrame,
    benchmark_tests: pd.DataFrame,
    selection_summary: pd.DataFrame,
    warnings_list: list[str],
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> str:
    strategy_metrics = metrics[~metrics["strategy"].str.startswith("Benchmark")].copy()
    top_by_sharpe = strategy_metrics.sort_values("Sharpe", ascending=False).head(1)
    top_by_cagr = strategy_metrics.sort_values("CAGR", ascending=False).head(1)

    topn_summary = (
        strategy_metrics.assign(top_n=strategy_metrics["strategy"].str.replace("Top", "", regex=False).astype(int))
        .groupby("top_n")
        .agg(avg_CAGR=("CAGR", "mean"), avg_Sharpe=("Sharpe", "mean"), avg_MaxDD=("MaxDD", "mean"))
        .reset_index()
        .sort_values("avg_Sharpe", ascending=False)
    )
    window_summary = (
        strategy_metrics.groupby("momentum_window")
        .agg(avg_CAGR=("CAGR", "mean"), avg_Sharpe=("Sharpe", "mean"), avg_MaxDD=("MaxDD", "mean"))
        .reset_index()
        .sort_values("avg_Sharpe", ascending=False)
    )

    spy_tests = benchmark_tests[benchmark_tests["benchmark"] == "Benchmark_SPY"]
    ew_tests = benchmark_tests[benchmark_tests["benchmark"] == "Benchmark_EqualWeight"]
    spy_significant = spy_tests[(spy_tests["avg_monthly_excess"] > 0) & (spy_tests["p_value"] < 0.05)]
    ew_significant = ew_tests[(ew_tests["avg_monthly_excess"] > 0) & (ew_tests["p_value"] < 0.05)]

    best = top_by_sharpe.iloc[0]
    best_label = best["label"]
    best_tests = benchmark_tests[benchmark_tests["strategy_label"] == best_label]
    best_selection = selection_summary[selection_summary["strategy"] == best["strategy"]]
    best_selection = best_selection[best_selection["momentum_window"] == best["momentum_window"]]
    best_selection = best_selection.sort_values("Selection Count", ascending=False).head(12)

    benchmark_metrics = metrics[metrics["strategy"].str.startswith("Benchmark")]
    best_benchmark_sharpe = benchmark_metrics["Sharpe"].max()
    best_benchmark_cagr = benchmark_metrics["CAGR"].max()
    return_source = "更高收益" if best["CAGR"] > best_benchmark_cagr else "不是更高 CAGR"
    drawdown_source = "更低回撤" if abs(best["MaxDD"]) < abs(benchmark_metrics["MaxDD"]).min() else "回撤优势不明显"

    warnings_section = "\n".join(f"- {warning}" for warning in warnings_list) if warnings_list else "- 无数据 warning。"

    return f"""# Cross-Sectional Momentum Summary

## 1. 研究问题

如果每个月买过去表现最好的资产，未来是否能够获得高于基准的收益和风险调整收益？
这里验证的是跨资产横截面动量，不是单个资产内部的 Time-Series Momentum。

## 2. 实验设计

- Price: `Adj Close`
- Universe: 12 ETFs across equity, commodity, and bond
- Common sample: `{start_date.date()}` to `{end_date.date()}`
- Rebalance: 每个月最后一个交易日排名，下一交易日开始持仓
- Momentum windows: `mom_63`, `mom_126`
- Strategies: `Top1`, `Top3`, `Top5`
- Weighting: selected assets equal weight
- Trading cost: 5 bps applied to turnover
- Benchmarks: `SPY Buy & Hold`, `Equal Weight All Assets monthly rebalance`

## 3. 结果表

{markdown_table(metrics, ["momentum_window", "strategy", "CAGR", "Sharpe", "MaxDD", "Volatility", "Calmar", "Total Return", "Turnover", "Number of Rebalances"], {"CAGR", "MaxDD", "Volatility", "Total Return", "Turnover"})}

## 4. 总体结论

- Sharpe 最好的策略: `{best_label}`，CAGR={fmt_pct(best["CAGR"])}，Sharpe={fmt_num(best["Sharpe"])}，MaxDD={fmt_pct(best["MaxDD"])}。
- CAGR 最好的策略: `{top_by_cagr.iloc[0]["label"]}`，CAGR={fmt_pct(top_by_cagr.iloc[0]["CAGR"])}。
- Top1/Top3/Top5 中，按平均 Sharpe 排名最好的是 `Top{int(topn_summary.iloc[0]["top_n"])}`。
- 3个月 vs 6个月动量中，按平均 Sharpe 排名更好的是 `{window_summary.iloc[0]["momentum_window"]}`。
- 显著优于 SPY 的策略数量: {len(spy_significant)} / {len(spy_tests)}。
- 显著优于 Equal Weight 的策略数量: {len(ew_significant)} / {len(ew_tests)}。
- 最佳策略的优势来源: {return_source}；{drawdown_source}。

## 5. Top N 对比

{markdown_table(topn_summary, ["top_n", "avg_CAGR", "avg_Sharpe", "avg_MaxDD"], {"avg_CAGR", "avg_MaxDD"})}

## 6. Momentum Window 对比

{markdown_table(window_summary, ["momentum_window", "avg_CAGR", "avg_Sharpe", "avg_MaxDD"], {"avg_CAGR", "avg_MaxDD"})}

## 7. 是否优于 Benchmark

{markdown_table(benchmark_tests, ["strategy_label", "benchmark", "monthly_observations", "avg_monthly_excess", "annualized_excess", "win_rate_vs_benchmark", "t_statistic", "p_value"], {"avg_monthly_excess", "annualized_excess", "win_rate_vs_benchmark"})}

## 8. 哪些资产最常进入组合

下面是最佳策略 `{best_label}` 的资产入选统计：

{markdown_table(best_selection, ["symbol", "Average Rank", "Selection Count", "Selection Percentage"], {"Selection Percentage"})}

完整资产统计见 `asset_selection_summary.csv`。

## 9. 解释

- Top 资产继续上涨，只说明横截面动量方向有效；它还必须在扣除 turnover cost 后优于 benchmark，才更接近可投资策略。
- 显著优于 benchmark 这里用月度超额收益做单样本 t-test；由于月度样本仍可能存在状态依赖，结论应作为研究证据，不应当作最终投资确认。
- 如果收益提升主要来自更低回撤，策略可能更像风险切换；如果主要来自更高 CAGR，才更像纯粹的 winner continuation。
- Equal Weight 是很强的基准，因为它已经吃到了跨资产分散收益；能否超过它，比超过 SPY 更能说明横截面动量是否真的增值。

## 10. 最终回答

这个实验直接回答：“跨资产横截面动量是否能把之前发现的 Momentum Alpha 转化成一个真正的投资组合策略？”

判断标准不是单看 Top 组合是否赚钱，而是看它是否在同一期间、同一资产池、扣除成本后，稳定优于 `SPY` 和 `Equal Weight`，并且 Sharpe / MaxDD 没有明显恶化。基于当前结果，最佳策略是 `{best_label}`，但是否足够进入下一阶段，需要优先看它相对 Equal Weight 的显著性和回撤改善。

## 11. Data Warnings

{warnings_section}
"""


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    captured_warnings: list[str] = []

    def capture_warning(message, category, filename, lineno, file=None, line=None):
        captured_warnings.append(str(message))

    old_showwarning = warnings.showwarning
    warnings.showwarning = capture_warning
    try:
        prices = load_prices()
        returns = prices.pct_change(fill_method=None).fillna(0.0)
        rebalance_dates = month_end_dates(prices.index)

        strategy_returns = {}
        strategy_meta = {}
        strategy_detail_by_label = {}
        strategy_details = []
        ranking_frames = []
        holding_frames = []
        benchmark_rows = []

        benchmark_spy_returns = returns[BENCHMARK_SPY].copy()
        benchmark_ew_returns, benchmark_ew_turnover, benchmark_ew_rebalances = build_equal_weight_benchmark(
            prices, returns, rebalance_dates
        )

        for window in MOMENTUM_WINDOWS:
            momentum = prices / prices.shift(window) - 1
            valid_rebalance_dates = pd.DatetimeIndex(
                [date for date in rebalance_dates if date in momentum.index and momentum.loc[date].notna().all()]
            )
            for top_n in TOP_N_VALUES:
                label = f"mom_{window}_Top{top_n}"
                daily, details, ranking, holdings = build_strategy(
                    prices=prices,
                    returns=returns,
                    momentum=momentum,
                    rebalance_dates=valid_rebalance_dates,
                    window=window,
                    top_n=top_n,
                )
                equity = (1 + daily).cumprod()
                strategy_returns[label] = daily
                strategy_meta[label] = {"momentum_window": f"mom_{window}", "strategy": f"Top{top_n}"}
                strategy_detail_by_label[label] = details
                temp_details = details.reset_index().rename(columns={"index": "Date"})
                temp_details["label"] = label
                temp_details["momentum_window"] = f"mom_{window}"
                temp_details["strategy"] = f"Top{top_n}"
                strategy_details.append(temp_details)
                ranking_frames.append(ranking)
                holding_frames.append(holdings)

        common_start = max(series.index[0] for series in strategy_returns.values())
        common_end = prices.index[-1]
        daily_returns = pd.DataFrame(strategy_returns).loc[common_start:common_end]
        benchmark_spy_returns = benchmark_spy_returns.loc[daily_returns.index]
        benchmark_ew_returns = benchmark_ew_returns.loc[daily_returns.index]
        daily_returns["Benchmark_SPY"] = benchmark_spy_returns
        daily_returns["Benchmark_EqualWeight"] = benchmark_ew_returns
        equity_curves = (1 + daily_returns).cumprod()

        metrics_rows = []
        for label, meta in strategy_meta.items():
            aligned_returns = daily_returns[label]
            aligned_equity = equity_curves[label]
            aligned_turnover = strategy_detail_by_label[label]["turnover"].reindex(daily_returns.index).fillna(0.0)
            metrics_rows.append(
                calculate_metrics(
                    label=label,
                    momentum_window=meta["momentum_window"],
                    strategy=meta["strategy"],
                    returns=aligned_returns,
                    equity=aligned_equity,
                    turnover=aligned_turnover,
                    number_of_rebalances=len(monthly_returns(aligned_returns)),
                )
            )

        metrics_rows.append(
            calculate_metrics(
                label="Benchmark_SPY",
                momentum_window="Benchmark",
                strategy="Benchmark_SPY",
                returns=benchmark_spy_returns,
                equity=equity_curves["Benchmark_SPY"],
                turnover=pd.Series(0.0, index=benchmark_spy_returns.index),
                number_of_rebalances=0,
            )
        )
        metrics_rows.append(
            calculate_metrics(
                label="Benchmark_EqualWeight",
                momentum_window="Benchmark",
                strategy="Benchmark_EqualWeight",
                returns=benchmark_ew_returns,
                equity=equity_curves["Benchmark_EqualWeight"],
                turnover=benchmark_ew_turnover.loc[benchmark_ew_returns.index],
                number_of_rebalances=len(monthly_returns(benchmark_ew_returns)),
            )
        )

        for label, returns_series in strategy_returns.items():
            aligned_strategy = returns_series.loc[daily_returns.index]
            benchmark_rows.append(
                benchmark_comparison(aligned_strategy, benchmark_spy_returns, label, "Benchmark_SPY")
            )
            benchmark_rows.append(
                benchmark_comparison(aligned_strategy, benchmark_ew_returns, label, "Benchmark_EqualWeight")
            )

        metrics = pd.DataFrame(metrics_rows)
        benchmark_tests = pd.DataFrame(benchmark_rows)
        ranking_history = pd.concat(ranking_frames, ignore_index=True) if ranking_frames else pd.DataFrame()
        rebalance_holdings = pd.concat(holding_frames, ignore_index=True) if holding_frames else pd.DataFrame()
        if not ranking_history.empty:
            ranking_history = ranking_history[
                (pd.to_datetime(ranking_history["effective_date"]) >= common_start)
                & (pd.to_datetime(ranking_history["effective_date"]) <= common_end)
            ].reset_index(drop=True)
        if not rebalance_holdings.empty:
            rebalance_holdings = rebalance_holdings[
                (pd.to_datetime(rebalance_holdings["effective_date"]) >= common_start)
                & (pd.to_datetime(rebalance_holdings["effective_date"]) <= common_end)
            ].reset_index(drop=True)
        strategy_daily_details = (
            pd.concat(strategy_details, ignore_index=True) if strategy_details else pd.DataFrame()
        )
        if not strategy_daily_details.empty:
            strategy_daily_details = strategy_daily_details[
                (pd.to_datetime(strategy_daily_details["Date"]) >= common_start)
                & (pd.to_datetime(strategy_daily_details["Date"]) <= common_end)
            ].reset_index(drop=True)
        selection_summary = summarize_selection(ranking_history) if not ranking_history.empty else pd.DataFrame()

        rolling_12m_returns = plot_rolling_12m_returns(daily_returns)
        plot_equity_curves(equity_curves)
        plot_drawdowns(equity_curves)

        metrics.to_csv(RESULTS_DIR / "metrics.csv", index=False)
        benchmark_tests.to_csv(RESULTS_DIR / "benchmark_tests.csv", index=False)
        selection_summary.to_csv(RESULTS_DIR / "asset_selection_summary.csv", index=False)
        ranking_history.to_csv(RESULTS_DIR / "ranking_history.csv", index=False)
        rebalance_holdings.to_csv(RESULTS_DIR / "rebalance_holdings.csv", index=False)
        strategy_daily_details.to_csv(RESULTS_DIR / "strategy_daily_details.csv", index=False)
        daily_returns.to_csv(RESULTS_DIR / "daily_returns.csv")
        equity_curves.to_csv(RESULTS_DIR / "equity_curves.csv")
        rolling_12m_returns.to_csv(RESULTS_DIR / "rolling_12m_returns.csv")

        summary = generate_summary(
            metrics=metrics,
            benchmark_tests=benchmark_tests,
            selection_summary=selection_summary,
            warnings_list=captured_warnings,
            start_date=daily_returns.index[0],
            end_date=daily_returns.index[-1],
        )
        (RESULTS_DIR / "summary.md").write_text(summary, encoding="utf-8")

    finally:
        warnings.showwarning = old_showwarning

    print("\nCross-Sectional Momentum Test Complete")
    print(f"Results directory: {RESULTS_DIR}")
    print(f"Sample: {daily_returns.index[0].date()} to {daily_returns.index[-1].date()}")
    print("\nCore metrics:")
    print(
        metrics[
            [
                "momentum_window",
                "strategy",
                "CAGR",
                "Sharpe",
                "MaxDD",
                "Volatility",
                "Calmar",
                "Total Return",
                "Turnover",
                "Number of Rebalances",
            ]
        ].to_string(index=False, float_format=lambda x: f"{x:,.4f}")
    )
    print("\nBenchmark significance tests:")
    print(benchmark_tests.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    if captured_warnings:
        print("\nWarnings:")
        for warning in captured_warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
