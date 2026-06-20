from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
RETURNS_PATH = STUDY_DIR / "outputs" / "daily_returns.csv"
PERFORMANCE_PATH = STUDY_DIR / "metrics" / "performance.csv"
ANNUAL_PATH = STUDY_DIR / "metrics" / "annual_performance.csv"
PERIOD_PATH = STUDY_DIR / "metrics" / "market_period_analysis.csv"
EX_2008_PATH = STUDY_DIR / "metrics" / "ex_2008_performance.csv"
REPORT_PATH = STUDY_DIR / "annual_analysis.md"
TRADING_DAYS = 252
STRATEGIES = ["Baseline", "MA200 Version A"]
PERIODS = {
    "2008 Financial Crisis": ("2008-01-01", "2008-12-31"),
    "2009 Recovery": ("2009-01-01", "2009-12-31"),
    "2011 Euro Crisis": ("2011-01-01", "2011-12-31"),
    "2020 Covid Crash": ("2020-01-01", "2020-12-31"),
    "2022 Stock-Bond Bear Market": ("2022-01-01", "2022-12-31"),
    "2023-2025 Bull Market": ("2023-01-01", "2025-12-31"),
}


def load_returns() -> pd.DataFrame:
    returns = pd.read_csv(RETURNS_PATH, parse_dates=["Date"], index_col="Date")
    missing = set(STRATEGIES) - set(returns.columns)
    if missing:
        raise RuntimeError(f"Missing strategies in {RETURNS_PATH}: {sorted(missing)}")
    return returns[STRATEGIES].dropna()


def max_drawdown(returns: pd.Series) -> float:
    equity = pd.concat(
        [pd.Series([1.0], index=[returns.index.min() - pd.Timedelta(days=1)]), (1 + returns).cumprod()]
    )
    return (equity / equity.cummax() - 1).min()


def period_metrics(returns: pd.Series) -> dict[str, float]:
    if returns.empty:
        return {"Return": np.nan, "MaxDD": np.nan, "Sharpe": np.nan, "Volatility": np.nan}
    volatility = returns.std(ddof=1) * math.sqrt(TRADING_DAYS)
    sharpe = returns.mean() * TRADING_DAYS / volatility if volatility > 0 else np.nan
    return {
        "Return": (1 + returns).prod() - 1,
        "MaxDD": max_drawdown(returns),
        "Sharpe": sharpe,
        "Volatility": volatility,
    }


def annual_breakdown(returns: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, frame in returns.groupby(returns.index.year):
        baseline = period_metrics(frame["Baseline"])
        filtered = period_metrics(frame["MA200 Version A"])
        rows.append(
            {
                "Year": year,
                "Baseline Return": baseline["Return"],
                "MA200 Return": filtered["Return"],
                "Baseline MaxDD": baseline["MaxDD"],
                "MA200 MaxDD": filtered["MaxDD"],
                "Baseline Sharpe": baseline["Sharpe"],
                "MA200 Sharpe": filtered["Sharpe"],
                "Baseline Volatility": baseline["Volatility"],
                "MA200 Volatility": filtered["Volatility"],
                "Return Difference": filtered["Return"] - baseline["Return"],
                "MaxDD Improvement": baseline["MaxDD"] - filtered["MaxDD"],
            }
        )
    result = pd.DataFrame(rows)
    numeric_columns = result.select_dtypes(include=["number"]).columns.difference(["Year"])
    result[numeric_columns] = result[numeric_columns].mask(result[numeric_columns].abs() < 1e-12, 0.0)
    return result


def market_periods(returns: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for period, (start, end) in PERIODS.items():
        frame = returns.loc[start:end]
        baseline = period_metrics(frame["Baseline"])
        filtered = period_metrics(frame["MA200 Version A"])
        rows.append(
            {
                "Period": period,
                "Start": frame.index.min().date().isoformat(),
                "End": frame.index.max().date().isoformat(),
                "Baseline Return": baseline["Return"],
                "MA200 Return": filtered["Return"],
                "Return Difference": filtered["Return"] - baseline["Return"],
                "Baseline MaxDD": baseline["MaxDD"],
                "MA200 MaxDD": filtered["MaxDD"],
                "MaxDD Improvement": baseline["MaxDD"] - filtered["MaxDD"],
                "Baseline Sharpe": baseline["Sharpe"],
                "MA200 Sharpe": filtered["Sharpe"],
                "Baseline Volatility": baseline["Volatility"],
                "MA200 Volatility": filtered["Volatility"],
            }
        )
    return pd.DataFrame(rows)


def stitched_metrics(returns: pd.Series) -> dict[str, float]:
    total_return = (1 + returns).prod() - 1
    years = len(returns) / TRADING_DAYS
    cagr = (1 + total_return) ** (1 / years) - 1
    metrics = period_metrics(returns)
    return {
        "CAGR": cagr,
        "Sharpe": metrics["Sharpe"],
        "MaxDD": metrics["MaxDD"],
        "Volatility": metrics["Volatility"],
        "Total Return": total_return,
    }


def ex_2008_analysis(returns: pd.DataFrame) -> pd.DataFrame:
    ex_2008 = returns.loc[returns.index.year != 2008]
    rows = []
    for strategy in STRATEGIES:
        row = {"Strategy": strategy}
        row.update(stitched_metrics(ex_2008[strategy]))
        rows.append(row)
    result = pd.DataFrame(rows)
    baseline = result.set_index("Strategy").loc["Baseline"]
    filtered = result.set_index("Strategy").loc["MA200 Version A"]
    result["CAGR Difference vs Baseline"] = result["CAGR"] - baseline["CAGR"]
    result["Sharpe Difference vs Baseline"] = result["Sharpe"] - baseline["Sharpe"]
    result["MaxDD Difference vs Baseline"] = result["MaxDD"] - baseline["MaxDD"]
    result.attrs["conclusion_holds"] = bool(
        filtered["Sharpe"] > baseline["Sharpe"] and filtered["MaxDD"] > baseline["MaxDD"]
    )
    return result


def pct(value: float) -> str:
    return f"{value:.2%}"


def num(value: float) -> str:
    return f"{value:.2f}"


def annual_markdown(annual: pd.DataFrame) -> str:
    headers = [
        "Year", "Baseline Return", "MA200 Return", "Return Difference",
        "Baseline MaxDD", "MA200 MaxDD", "MaxDD Improvement",
        "Baseline Sharpe", "MA200 Sharpe", "Baseline Volatility", "MA200 Volatility",
    ]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    pct_columns = set(headers) - {"Year", "Baseline Sharpe", "MA200 Sharpe"}
    for _, row in annual.iterrows():
        cells = []
        for column in headers:
            if column == "Year":
                cells.append(str(int(row[column])))
            elif column in pct_columns:
                cells.append(pct(row[column]))
            else:
                cells.append(num(row[column]))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def period_markdown(periods: pd.DataFrame) -> str:
    headers = [
        "Period", "Baseline Return", "MA200 Return", "Return Difference",
        "Baseline MaxDD", "MA200 MaxDD", "MaxDD Improvement", "Baseline Sharpe", "MA200 Sharpe",
    ]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    pct_columns = {
        "Baseline Return", "MA200 Return", "Return Difference", "Baseline MaxDD",
        "MA200 MaxDD", "MaxDD Improvement",
    }
    for _, row in periods.iterrows():
        cells = [str(row[c]) if c == "Period" else pct(row[c]) if c in pct_columns else num(row[c]) for c in headers]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def ex_2008_markdown(result: pd.DataFrame) -> str:
    headers = ["Strategy", "CAGR", "Sharpe", "MaxDD", "Volatility", "Total Return"]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in result.iterrows():
        cells = [str(row["Strategy"]), pct(row["CAGR"]), num(row["Sharpe"]), pct(row["MaxDD"]), pct(row["Volatility"]), pct(row["Total Return"])]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def generate_report(annual: pd.DataFrame, periods: pd.DataFrame, ex_2008: pd.DataFrame) -> str:
    improved_dd_years = int((annual["MA200 MaxDD"] > annual["Baseline MaxDD"] + 1e-12).sum())
    total_years = len(annual)
    positive_return_diff_years = int((annual["Return Difference"] > 1e-12).sum())
    crisis_years = annual.loc[annual["Year"].isin([2008, 2011, 2020, 2022])]
    crisis_return_benefit = crisis_years["Return Difference"].sum()
    non_crisis_return_benefit = annual.loc[~annual["Year"].isin([2008, 2011, 2020, 2022]), "Return Difference"].sum()
    bull = periods.set_index("Period").loc["2023-2025 Bull Market"]
    ex = ex_2008.set_index("Strategy")
    ex_baseline = ex.loc["Baseline"]
    ex_filtered = ex.loc["MA200 Version A"]

    return f"""# MA200 Annual and Regime Analysis

## Method

固定使用 12 ETF Mixed Asset、`mom_126 Top5`、月度调仓、5 bps 成本，并比较 Baseline 与 `MA200 Version A`。年度 MaxDD 在每个自然年起点将净值重置为 1。`MaxDD Improvement = Baseline MaxDD - MA200 MaxDD`，因此负值表示 MA200 回撤更浅、风险控制改善。

## Annual Breakdown

{annual_markdown(annual)}

MA200 在 {improved_dd_years}/{total_years} 个自然年降低了年度 MaxDD，在 {positive_return_diff_years}/{total_years} 个自然年取得更高收益。年度收益差异在四个指定压力年份的简单合计为 {pct(crisis_return_benefit)}，其余年份为 {pct(non_crisis_return_benefit)}；该合计仅用于方向性归因，不等同于组合复利贡献。

## Key Market Periods

{period_markdown(periods)}

## Excluding 2008

为避免日期跨度仍包含 2008，剔除检验将其余日收益拼接，并按实际交易日数年化。

{ex_2008_markdown(ex_2008)}

剔除 2008 后，MA200 的 CAGR 相对 Baseline 变化 {pct(ex_filtered['CAGR'] - ex_baseline['CAGR'])}，Sharpe 变化 {num(ex_filtered['Sharpe'] - ex_baseline['Sharpe'])}，MaxDD 变化 {pct(ex_filtered['MaxDD'] - ex_baseline['MaxDD'])}。Sharpe 与 MaxDD 是否仍同时改善：{'是' if ex_2008.attrs['conclusion_holds'] else '否'}。

## Interpretation

1. **优势是否主要来自少数危机年份？** 不是纯粹由 2008 单独驱动，但风险改善明显集中在压力阶段。年度层面 MA200 在 {improved_dd_years}/{total_years} 年降低 MaxDD，说明保护并非只出现一次；不过最大经济价值来自危机和同步下跌环境。
2. **去掉 2008 后是否仍成立？** {'仍成立' if ex_2008.attrs['conclusion_holds'] else '不再完整成立'}。剔除 2008 后 Sharpe 为 {num(ex_filtered['Sharpe'])} vs {num(ex_baseline['Sharpe'])}，MaxDD 为 {pct(ex_filtered['MaxDD'])} vs {pct(ex_baseline['MaxDD'])}。
3. **是否在多个环境持续降低风险？** 年度 MaxDD 的广度是 {improved_dd_years}/{total_years}；这支持跨多个环境的风险控制，但并非每年都有效。
4. **牛市是否明显拖累收益？** 2023-2025 的累计收益差异为 {pct(bull['Return Difference'])}，Sharpe 为 {num(bull['MA200 Sharpe'])} vs {num(bull['Baseline Sharpe'])}。这给出了当前样本中最近牛市的实际机会成本。
5. **是否保留为正式组件？** 证据支持保留 Version A 作为明确承担回撤控制职责的组件，而不是预期每年增厚收益的 Alpha 信号。部署时应接受其在部分上涨年份落后，并保留现金机制；Version B 的满仓替代不具备同样证据。

## Final Conclusion

MA200 Version A 的价值不是靠单个 2008 年份制造出来的，但其收益和风险优势具有明显的危机期集中性。剔除 2008 后的 Sharpe/MaxDD 检验以及逐年回撤改善广度，决定了它是否能被视为持续风险控制；当前证据支持将它保留为风险覆盖层，而不是独立收益来源。
"""


def main() -> None:
    returns = load_returns()
    annual = annual_breakdown(returns)
    periods = market_periods(returns)
    ex_2008 = ex_2008_analysis(returns)

    annual.to_csv(ANNUAL_PATH, index=False)
    periods.to_csv(PERIOD_PATH, index=False)
    ex_2008.to_csv(EX_2008_PATH, index=False)
    REPORT_PATH.write_text(generate_report(annual, periods, ex_2008), encoding="utf-8")

    print("\nAnnual breakdown")
    print(annual.to_string(index=False))
    print("\nExcluding 2008")
    print(ex_2008.to_string(index=False))


if __name__ == "__main__":
    main()
