from pathlib import Path
from typing import Optional, Set
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "trend" / "ma" / "results"

MA_WINDOW = 200
TRADING_COST = 0.0005
TRADING_DAYS = 252
REQUIRED_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]


def discover_data_files() -> list[tuple[str, Path]]:
    files = []
    for asset_class in ["equity", "commodity", "bond"]:
        asset_dir = DATA_ROOT / asset_class
        if not asset_dir.exists():
            warnings.warn(f"Missing asset class directory: {asset_dir}")
            continue
        for path in sorted(asset_dir.glob("*.csv")):
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
    df["price"] = pd.to_numeric(df["Adj Close"], errors="coerce")
    df = df.dropna(subset=["Date", "price"]).sort_values("Date").reset_index(drop=True)
    df = df.drop_duplicates(subset=["Date"], keep="last").reset_index(drop=True)

    if len(df) < MA_WINDOW:
        warnings.warn(f"{symbol}: only {len(df)} rows, fewer than {MA_WINDOW}, skipped")
        return None

    df["symbol"] = symbol
    df["asset_class"] = asset_class
    return df


def add_ma200_strategy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ma200"] = df["price"].rolling(MA_WINDOW, min_periods=MA_WINDOW).mean()
    df["signal"] = (df["price"] > df["ma200"]).astype(int)
    df.loc[df["ma200"].isna(), "signal"] = 0
    df["position"] = df["signal"].shift(1).fillna(0)

    df["asset_return"] = df["price"].pct_change(fill_method=None).fillna(0)
    df["turnover"] = (df["position"] - df["position"].shift(1).fillna(0)).abs()
    df["cost"] = df["turnover"] * TRADING_COST
    df["strategy_return"] = df["position"] * df["asset_return"] - df["cost"]
    df["benchmark_return"] = df["asset_return"]

    df["strategy_equity"] = (1 + df["strategy_return"]).cumprod()
    df["benchmark_equity"] = (1 + df["benchmark_return"]).cumprod()
    df["strategy_drawdown"] = df["strategy_equity"] / df["strategy_equity"].cummax() - 1
    df["benchmark_drawdown"] = df["benchmark_equity"] / df["benchmark_equity"].cummax() - 1
    return df


def annualized_return(equity: pd.Series) -> float:
    equity = equity.dropna()
    if len(equity) <= 1:
        return np.nan
    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    years = len(equity) / TRADING_DAYS
    if years <= 0 or total_return <= -1:
        return np.nan
    return (1 + total_return) ** (1 / years) - 1


def sharpe_ratio(returns: pd.Series) -> float:
    returns = returns.dropna()
    if len(returns) <= 1 or returns.std() == 0:
        return np.nan
    return np.sqrt(TRADING_DAYS) * returns.mean() / returns.std()


def max_drawdown(equity: pd.Series) -> float:
    equity = equity.dropna()
    if equity.empty:
        return np.nan
    return (equity / equity.cummax() - 1).min()


def average_holding_days(position: pd.Series) -> float:
    runs = []
    current = 0
    for value in position.astype(int):
        if value == 1:
            current += 1
        elif current > 0:
            runs.append(current)
            current = 0
    if current > 0:
        runs.append(current)
    return float(np.mean(runs)) if runs else 0.0


def calculate_metrics(df: pd.DataFrame) -> dict:
    strategy_maxdd = max_drawdown(df["strategy_equity"])
    benchmark_maxdd = max_drawdown(df["benchmark_equity"])
    strategy_cagr = annualized_return(df["strategy_equity"])
    benchmark_cagr = annualized_return(df["benchmark_equity"])
    strategy_sharpe = sharpe_ratio(df["strategy_return"])
    benchmark_sharpe = sharpe_ratio(df["benchmark_return"])

    return {
        "symbol": df["symbol"].iloc[0],
        "asset_class": df["asset_class"].iloc[0],
        "start_date": df["Date"].iloc[0].date(),
        "end_date": df["Date"].iloc[-1].date(),
        "rows": len(df),
        "strategy_total_return": df["strategy_equity"].iloc[-1] - 1,
        "benchmark_total_return": df["benchmark_equity"].iloc[-1] - 1,
        "strategy_cagr": strategy_cagr,
        "benchmark_cagr": benchmark_cagr,
        "strategy_sharpe": strategy_sharpe,
        "benchmark_sharpe": benchmark_sharpe,
        "strategy_max_drawdown": strategy_maxdd,
        "benchmark_max_drawdown": benchmark_maxdd,
        "strategy_exposure": df["position"].mean(),
        "trade_count": int(df["turnover"].sum()),
        "avg_holding_days": average_holding_days(df["position"]),
        "cagr_diff": strategy_cagr - benchmark_cagr,
        "sharpe_diff": strategy_sharpe - benchmark_sharpe,
        "maxdd_improvement": abs(benchmark_maxdd) - abs(strategy_maxdd),
    }


def calculate_yearly_returns(df: pd.DataFrame) -> pd.DataFrame:
    temp = df.copy()
    temp["year"] = temp["Date"].dt.year

    rows = []
    for year, part in temp.groupby("year"):
        strategy_return = (1 + part["strategy_return"]).prod() - 1
        benchmark_return = (1 + part["benchmark_return"]).prod() - 1
        strategy_equity = (1 + part["strategy_return"]).cumprod()
        benchmark_equity = (1 + part["benchmark_return"]).cumprod()
        rows.append(
            {
                "symbol": part["symbol"].iloc[0],
                "asset_class": part["asset_class"].iloc[0],
                "year": year,
                "strategy_return": strategy_return,
                "benchmark_return": benchmark_return,
                "strategy_excess_return": strategy_return - benchmark_return,
                "strategy_max_drawdown_this_year": max_drawdown(strategy_equity),
                "benchmark_max_drawdown_this_year": max_drawdown(benchmark_equity),
                "trade_count": int(part["turnover"].sum()),
                "exposure": part["position"].mean(),
            }
        )
    return pd.DataFrame(rows)


def summarize_by_asset_class(metrics: pd.DataFrame) -> pd.DataFrame:
    summary = metrics.groupby("asset_class").agg(
        symbols_count=("symbol", "count"),
        avg_strategy_cagr=("strategy_cagr", "mean"),
        avg_benchmark_cagr=("benchmark_cagr", "mean"),
        avg_strategy_sharpe=("strategy_sharpe", "mean"),
        avg_benchmark_sharpe=("benchmark_sharpe", "mean"),
        avg_strategy_max_drawdown=("strategy_max_drawdown", "mean"),
        avg_benchmark_max_drawdown=("benchmark_max_drawdown", "mean"),
        avg_cagr_diff=("cagr_diff", "mean"),
        avg_sharpe_diff=("sharpe_diff", "mean"),
        avg_maxdd_improvement=("maxdd_improvement", "mean"),
        percent_symbols_sharpe_improved=("sharpe_diff", lambda x: (x > 0).mean()),
        percent_symbols_maxdd_improved=("maxdd_improvement", lambda x: (x > 0).mean()),
        percent_symbols_cagr_improved=("cagr_diff", lambda x: (x > 0).mean()),
    )
    return summary.reset_index()


def plot_equity_curves(results: dict[str, pd.DataFrame]) -> None:
    symbols = list(results.keys())
    ncols = 3
    nrows = int(np.ceil(len(symbols) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(16, 4 * nrows), sharex=False)
    axes = np.array(axes).reshape(-1)

    for ax, symbol in zip(axes, symbols):
        df = results[symbol]
        ax.plot(df["Date"], df["strategy_equity"], label="MA200")
        ax.plot(df["Date"], df["benchmark_equity"], label="BuyHold", linestyle="--")
        ax.set_title(f"{symbol} Equity")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

    for ax in axes[len(symbols):]:
        ax.axis("off")

    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "equity_curves.png", dpi=150)
    plt.close(fig)


def plot_drawdowns(results: dict[str, pd.DataFrame]) -> None:
    symbols = list(results.keys())
    ncols = 3
    nrows = int(np.ceil(len(symbols) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(16, 4 * nrows), sharex=False)
    axes = np.array(axes).reshape(-1)

    for ax, symbol in zip(axes, symbols):
        df = results[symbol]
        ax.plot(df["Date"], df["strategy_drawdown"], label="MA200")
        ax.plot(df["Date"], df["benchmark_drawdown"], label="BuyHold", linestyle="--")
        ax.set_title(f"{symbol} Drawdown")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

    for ax in axes[len(symbols):]:
        ax.axis("off")

    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "drawdowns.png", dpi=150)
    plt.close(fig)


def fmt_pct(value: float) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.2%}"


def fmt_num(value: float) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.2f}"


def markdown_table(df: pd.DataFrame, columns: list[str], pct_columns: Optional[Set[str]] = None) -> str:
    pct_columns = pct_columns or set()
    lines = ["| " + " | ".join(columns) + " |"]
    lines.append("|" + "|".join(["---"] * len(columns)) + "|")
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


def write_summary(metrics: pd.DataFrame, asset_summary: pd.DataFrame, warnings_list: list[str]) -> None:
    maxdd_rate = (metrics["maxdd_improvement"] > 0).mean()
    sharpe_rate = (metrics["sharpe_diff"] > 0).mean()
    cagr_rate = (metrics["cagr_diff"] > 0).mean()
    best_class = asset_summary.sort_values(
        ["avg_maxdd_improvement", "avg_sharpe_diff"], ascending=False
    ).iloc[0]["asset_class"]
    worst_class = asset_summary.sort_values(
        ["avg_maxdd_improvement", "avg_sharpe_diff"], ascending=True
    ).iloc[0]["asset_class"]

    lines = []
    lines.append("# MA200 Trend Filter Research Summary\n")
    lines.append("## 1. 研究问题\n")
    lines.append("MA200 趋势过滤是否能在不同资产类别中改善风险收益特征？\n")

    lines.append("## 2. Alpha 假设\n")
    lines.append("- 如果价格高于长期均线，说明资产可能处于强势趋势。")
    lines.append("- 如果价格低于长期均线，说明资产可能处于弱势状态。")
    lines.append("- 因此，只在价格高于 MA200 时持有，可能降低熊市回撤。\n")

    lines.append("## 3. 实验规则\n")
    lines.append("- MA200: 200 日简单移动平均")
    lines.append("- 价格: `Adj Close`")
    lines.append("- 防未来函数: `position = signal.shift(1)`")
    lines.append("- 仓位: `100%` or `0%`")
    lines.append("- 不做空")
    lines.append("- 不加杠杆")
    lines.append("- 成本: 每次仓位变化扣 `0.05%`\n")

    lines.append("## 4. 总体结论\n")
    lines.append(f"- MaxDD 改善比例: {fmt_pct(maxdd_rate)} ({int((metrics['maxdd_improvement'] > 0).sum())}/{len(metrics)})")
    lines.append(f"- Sharpe 提高比例: {fmt_pct(sharpe_rate)} ({int((metrics['sharpe_diff'] > 0).sum())}/{len(metrics)})")
    lines.append(f"- CAGR 提高比例: {fmt_pct(cagr_rate)} ({int((metrics['cagr_diff'] > 0).sum())}/{len(metrics)})")
    lines.append(f"- 效果最好资产类别: `{best_class}`")
    lines.append(f"- 效果最差资产类别: `{worst_class}`")
    if maxdd_rate >= 0.75 and cagr_rate < 0.5:
        lines.append("- 总体判断: MA200 普遍更像风险过滤器，而不是收益增强 Alpha。\n")
    else:
        lines.append("- 总体判断: MA200 的效果需要按资产类别拆开看，不能直接视为普适 Alpha。\n")

    lines.append("## 5. 分资产类别结论\n")
    pct_cols = {
        "avg_strategy_cagr",
        "avg_benchmark_cagr",
        "avg_strategy_max_drawdown",
        "avg_benchmark_max_drawdown",
        "avg_cagr_diff",
        "avg_maxdd_improvement",
        "percent_symbols_sharpe_improved",
        "percent_symbols_maxdd_improved",
        "percent_symbols_cagr_improved",
    }
    lines.append(markdown_table(asset_summary, list(asset_summary.columns), pct_cols))
    lines.append("")
    for _, row in asset_summary.iterrows():
        cls = row["asset_class"]
        lines.append(f"### {cls.title()}")
        lines.append(
            f"- Avg CAGR diff: {fmt_pct(row['avg_cagr_diff'])}; "
            f"Avg Sharpe diff: {fmt_num(row['avg_sharpe_diff'])}; "
            f"Avg MaxDD improvement: {fmt_pct(row['avg_maxdd_improvement'])}."
        )
        if row["percent_symbols_maxdd_improved"] == 1 and row["percent_symbols_cagr_improved"] < 0.5:
            lines.append("- 主要价值是降低回撤，收益改善不足。")
        elif row["percent_symbols_cagr_improved"] >= 0.5 and row["percent_symbols_sharpe_improved"] >= 0.5:
            lines.append("- 同时有一定收益和风险调整改善。")
        else:
            lines.append("- 效果不稳定，需要更细的资产级别分析。")
    lines.append("")

    lines.append("## 6. 研究判断\n")
    lines.append("- MA200 是否像 Alpha: 不强。多数情况下它不稳定提高 CAGR。")
    lines.append("- MA200 是否更像 Risk Filter: 是。核心价值是降低 MaxDD 和降低风险暴露。")
    lines.append("- 是否值得作为后续策略的风险控制模块: 值得，尤其适合先作为跨资产组合的风险开关测试。\n")

    lines.append("## 7. 下一步建议\n")
    lines.append("- 测试 MA100/150/200/250 鲁棒性。")
    lines.append("- 测试其他 trend proxy: momentum, Donchian, 52-week high。")
    lines.append("- 继续做跨资产趋势研究，并重点看组合层面的回撤、Sharpe 和换手。")
    lines.append("- 增加现金收益或短债替代空仓的版本，但要和纯空仓版本分开记录。\n")

    lines.append("## 8. Symbol Metrics\n")
    symbol_cols = [
        "symbol",
        "asset_class",
        "strategy_cagr",
        "benchmark_cagr",
        "strategy_sharpe",
        "benchmark_sharpe",
        "strategy_max_drawdown",
        "benchmark_max_drawdown",
        "cagr_diff",
        "sharpe_diff",
        "maxdd_improvement",
    ]
    lines.append(
        markdown_table(
            metrics.sort_values(["asset_class", "symbol"]),
            symbol_cols,
            {
                "strategy_cagr",
                "benchmark_cagr",
                "strategy_max_drawdown",
                "benchmark_max_drawdown",
                "cagr_diff",
                "maxdd_improvement",
            },
        )
    )

    if warnings_list:
        lines.append("\n## 9. Warnings\n")
        for warning in warnings_list:
            lines.append(f"- {warning}")

    (RESULTS_DIR / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    warnings_list = []
    results = {}
    metrics_rows = []
    yearly_frames = []

    for asset_class, path in discover_data_files():
        symbol = path.stem
        df = load_price_data(path, asset_class)
        if df is None:
            warnings_list.append(f"{symbol}: skipped; see terminal warnings")
            continue
        result = add_ma200_strategy(df)
        results[symbol] = result
        metrics_rows.append(calculate_metrics(result))
        yearly_frames.append(calculate_yearly_returns(result))

    if not metrics_rows:
        raise RuntimeError("No valid symbols processed.")

    metrics = pd.DataFrame(metrics_rows).sort_values(["asset_class", "symbol"]).reset_index(drop=True)
    yearly_returns = pd.concat(yearly_frames, ignore_index=True).sort_values(
        ["asset_class", "symbol", "year"]
    )
    asset_summary = summarize_by_asset_class(metrics)

    metrics.to_csv(RESULTS_DIR / "metrics.csv", index=False)
    yearly_returns.to_csv(RESULTS_DIR / "yearly_returns.csv", index=False)
    asset_summary.to_csv(RESULTS_DIR / "asset_class_summary.csv", index=False)

    plot_equity_curves(results)
    plot_drawdowns(results)
    write_summary(metrics, asset_summary, warnings_list)

    print("\nMA200 core summary:")
    print(
        metrics[
            [
                "symbol",
                "asset_class",
                "strategy_cagr",
                "benchmark_cagr",
                "strategy_sharpe",
                "benchmark_sharpe",
                "strategy_max_drawdown",
                "benchmark_max_drawdown",
                "cagr_diff",
                "sharpe_diff",
                "maxdd_improvement",
            ]
        ].to_string(index=False)
    )
    print(f"\nResults saved to: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
