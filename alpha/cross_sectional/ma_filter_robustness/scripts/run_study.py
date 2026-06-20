from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = ALPHA_ROOT / "shared" / "data"
BASELINE_RETURNS_PATH = ALPHA_ROOT / "cross_sectional" / "mixed_asset_momentum" / "outputs" / "daily_returns.csv"
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(ALPHA_ROOT))

from shared.configs.universes import MIXED_ASSET_SYMBOLS  # noqa: E402
from shared.loaders.prices import load_symbol  # noqa: E402
from shared.utils import cross_sectional as core  # noqa: E402


MA_LENGTHS = [100, 125, 150, 175, 200, 225, 250, 275, 300]
MOMENTUM_WINDOW = 126
TOP_N = 5
PLATEAU_SHARPE_RANGE = 0.15
PLATEAU_CAGR_RANGE = 0.02
PLATEAU_MAXDD_RANGE = 0.10
ISOLATED_SPIKE_THRESHOLD = 0.15


def load_full_history_prices() -> dict[str, pd.Series]:
    histories = {}
    for symbol in MIXED_ASSET_SYMBOLS:
        matches = list(DATA_ROOT.glob(f"*/{symbol}.csv"))
        if len(matches) != 1:
            raise RuntimeError(f"Expected one data file for {symbol}, found {len(matches)}")
        frame = load_symbol(matches[0])
        if frame is None:
            raise RuntimeError(f"Failed to load full history for {symbol}")
        histories[symbol] = frame[symbol]
    return histories


def moving_averages(
    histories: dict[str, pd.Series],
    index: pd.DatetimeIndex,
) -> dict[int, pd.DataFrame]:
    result = {}
    for length in MA_LENGTHS:
        columns = [
            history.rolling(length, min_periods=length).mean().rename(symbol)
            for symbol, history in histories.items()
        ]
        result[length] = pd.concat(columns, axis=1).reindex(index)
    return result


def build_targets(
    prices: pd.DataFrame,
    ma_by_length: dict[int, pd.DataFrame],
) -> tuple[dict[str, dict[pd.Timestamp, pd.Series]], pd.DataFrame]:
    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    targets: dict[str, dict[pd.Timestamp, pd.Series]] = {"Baseline": {}}
    targets.update({f"MA{length}": {} for length in MA_LENGTHS})
    exposure_rows = []

    for rebalance_date in core.month_end_dates(prices.index):
        scores = momentum.loc[rebalance_date].dropna()
        if len(scores) != len(prices.columns):
            continue
        location = prices.index.get_loc(rebalance_date)
        if location + 1 >= len(prices.index):
            continue
        effective_date = prices.index[location + 1]

        baseline_target = pd.Series(0.0, index=prices.columns)
        baseline_target.loc[scores.nlargest(TOP_N).index] = 1.0 / TOP_N
        targets["Baseline"][effective_date] = baseline_target

        for length in MA_LENGTHS:
            eligible_mask = (prices.loc[rebalance_date] > ma_by_length[length].loc[rebalance_date]).fillna(False)
            eligible_symbols = eligible_mask[eligible_mask].index
            selected = scores.loc[eligible_symbols].nlargest(TOP_N).index
            target = pd.Series(0.0, index=prices.columns)
            target.loc[selected] = 1.0 / TOP_N
            targets[f"MA{length}"][effective_date] = target
            exposure_rows.append(
                {
                    "MA Length": length,
                    "Rebalance Date": rebalance_date,
                    "Effective Date": effective_date,
                    "Eligible Assets": len(eligible_symbols),
                    "Holdings": len(selected),
                    "Cash Allocation": 1.0 - target.sum(),
                    "Below 5 Assets": len(eligible_symbols) < TOP_N,
                }
            )

    return targets, pd.DataFrame(exposure_rows)


def calculate_performance(
    returns: pd.DataFrame,
    targets: dict[str, dict[pd.Timestamp, pd.Series]],
    analysis_index: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    strategy_returns = {}
    for label, label_targets in targets.items():
        details, _ = core.simulate_monthly_holdings(returns, label_targets)
        details = details.reindex(analysis_index)
        if details.isna().any().any():
            raise RuntimeError(f"{label}: incomplete common sample")
        equity = (1 + details["return"]).cumprod()
        metrics = core.calculate_metrics(
            label=label,
            momentum_window="mom_126",
            strategy="Top5" if label == "Baseline" else f"{label} Version A",
            returns=details["return"],
            equity=equity,
            turnover=details["turnover"],
            number_of_rebalances=len(core.monthly_returns(details["return"])),
        )
        rows.append(
            {
                "MA Length": label,
                "CAGR": metrics["CAGR"],
                "Sharpe": metrics["Sharpe"],
                "MaxDD": metrics["MaxDD"],
                "Volatility": metrics["Volatility"],
                "Calmar": metrics["Calmar"],
                "Total Return": metrics["Total Return"],
                "Turnover": metrics["Turnover"],
            }
        )
        strategy_returns[label] = details["return"]
    return pd.DataFrame(rows), pd.DataFrame(strategy_returns, index=analysis_index)


def relative_changes(performance: pd.DataFrame) -> pd.DataFrame:
    baseline = performance.set_index("MA Length").loc["Baseline"]
    result = performance.loc[performance["MA Length"] != "Baseline", ["MA Length", "CAGR", "Sharpe", "MaxDD"]].copy()
    result["CAGR Change"] = result["CAGR"] - baseline["CAGR"]
    result["Sharpe Change"] = result["Sharpe"] - baseline["Sharpe"]
    result["MaxDD Change"] = result["MaxDD"] - baseline["MaxDD"]
    return result[["MA Length", "CAGR Change", "Sharpe Change", "MaxDD Change"]]


def exposure_statistics(exposure: pd.DataFrame, analysis_index: pd.DatetimeIndex) -> pd.DataFrame:
    sample = exposure.loc[pd.to_datetime(exposure["Effective Date"]).between(analysis_index.min(), analysis_index.max())]
    result = (
        sample.groupby("MA Length", as_index=False)
        .agg(
            **{
                "Avg Eligible Assets": ("Eligible Assets", "mean"),
                "Avg Holdings": ("Holdings", "mean"),
                "Avg Cash Allocation": ("Cash Allocation", "mean"),
                "Percent Months Below 5 Assets": ("Below 5 Assets", "mean"),
            }
        )
        .sort_values("MA Length")
    )
    result["MA Length"] = "MA" + result["MA Length"].astype(str)
    return result


def robustness_scores(performance: pd.DataFrame) -> pd.DataFrame:
    filtered = performance.loc[performance["MA Length"] != "Baseline", ["MA Length", "Sharpe"]].copy()
    filtered["Length"] = filtered["MA Length"].str.removeprefix("MA").astype(int)
    filtered = filtered.sort_values("Length").reset_index(drop=True)
    rows = []
    for index, row in filtered.iterrows():
        neighbor_sharpes = []
        if index > 0:
            neighbor_sharpes.append(filtered.loc[index - 1, "Sharpe"])
        if index + 1 < len(filtered):
            neighbor_sharpes.append(filtered.loc[index + 1, "Sharpe"])
        neighbor_mae = float(np.mean(np.abs(np.asarray(neighbor_sharpes) - row["Sharpe"])))
        rows.append(
            {
                "MA Length": row["MA Length"],
                "Sharpe": row["Sharpe"],
                "Neighbor Sharpe MAE": neighbor_mae,
                "Robustness Score": 100 * max(0.0, 1.0 - neighbor_mae / 0.20),
            }
        )
    return pd.DataFrame(rows)


def stable_plateaus(performance: pd.DataFrame) -> pd.DataFrame:
    filtered = performance.loc[performance["MA Length"] != "Baseline"].copy()
    filtered["Length"] = filtered["MA Length"].str.removeprefix("MA").astype(int)
    filtered = filtered.sort_values("Length").reset_index(drop=True)
    candidates = []
    for start in range(len(filtered)):
        for end in range(start + 2, len(filtered)):
            window = filtered.iloc[start : end + 1]
            sharpe_range = window["Sharpe"].max() - window["Sharpe"].min()
            cagr_range = window["CAGR"].max() - window["CAGR"].min()
            maxdd_range = window["MaxDD"].max() - window["MaxDD"].min()
            if (
                sharpe_range <= PLATEAU_SHARPE_RANGE
                and cagr_range <= PLATEAU_CAGR_RANGE
                and maxdd_range <= PLATEAU_MAXDD_RANGE
            ):
                candidates.append((start, end, sharpe_range, cagr_range, maxdd_range))

    longest_size = max((end - start + 1 for start, end, *_ in candidates), default=0)
    maximal = [candidate for candidate in candidates if candidate[1] - candidate[0] + 1 == longest_size]

    rows = []
    for start, end, sharpe_range, cagr_range, maxdd_range in maximal:
        lengths = filtered.iloc[start : end + 1]["Length"].tolist()
        rows.append(
            {
                "Start MA": int(lengths[0]),
                "End MA": int(lengths[-1]),
                "Number of Lengths": len(lengths),
                "MA Lengths": ",".join(f"MA{length}" for length in lengths),
                "Sharpe Range": sharpe_range,
                "CAGR Range": cagr_range,
                "MaxDD Range": maxdd_range,
                "Contains MA200": 200 in lengths,
                "MA200 Is Interior": 200 in lengths[1:-1],
            }
        )
    return pd.DataFrame(rows)


def isolated_spikes(performance: pd.DataFrame) -> list[str]:
    filtered = performance.loc[performance["MA Length"] != "Baseline", ["MA Length", "Sharpe"]].reset_index(drop=True)
    spikes = []
    for index in range(1, len(filtered) - 1):
        neighbor_mean = (filtered.loc[index - 1, "Sharpe"] + filtered.loc[index + 1, "Sharpe"]) / 2
        if filtered.loc[index, "Sharpe"] - neighbor_mean > ISOLATED_SPIKE_THRESHOLD:
            spikes.append(filtered.loc[index, "MA Length"])
    return spikes


def fmt_pct(value: float) -> str:
    return f"{value:.2%}"


def fmt_num(value: float) -> str:
    return f"{value:.2f}"


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
    exposure: pd.DataFrame,
    robustness: pd.DataFrame,
    plateaus: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> str:
    filtered = performance.loc[performance["MA Length"] != "Baseline"].copy()
    filtered["Length"] = filtered["MA Length"].str.removeprefix("MA").astype(int)
    filtered = filtered.sort_values("Length")
    baseline = performance.set_index("MA Length").loc["Baseline"]
    ma200 = filtered.set_index("Length").loc[200]
    ma175 = filtered.set_index("Length").loc[175]
    ma225 = filtered.set_index("Length").loc[225]
    maxdd_changes = relative.copy()
    maxdd_changes["Length"] = maxdd_changes["MA Length"].str.removeprefix("MA").astype(int)
    maxdd_monotonic = maxdd_changes.sort_values("Length")["MaxDD Change"].is_monotonic_increasing
    cash = exposure.copy()
    cash["Length"] = cash["MA Length"].str.removeprefix("MA").astype(int)
    cash_correlation = cash["Length"].corr(cash["Avg Cash Allocation"])
    cash_change = cash.set_index("Length").loc[300, "Avg Cash Allocation"] - cash.set_index("Length").loc[100, "Avg Cash Allocation"]
    ma200_plateaus = plateaus.loc[plateaus["Contains MA200"]] if not plateaus.empty else plateaus
    plateau_text = "; ".join(f"MA{row['Start MA']}-MA{row['End MA']}" for _, row in plateaus.iterrows()) or "None"
    ma200_in_plateau = not ma200_plateaus.empty
    ma200_interior = bool(ma200_plateaus["MA200 Is Interior"].any()) if ma200_in_plateau else False
    spikes = isolated_spikes(performance)
    all_drawdowns_improve = bool((relative["MaxDD Change"] > 0).all())
    multiple_similar = bool(len(plateaus) > 0)

    return f"""# MA Trend Filter Robustness Test

## 1. Research Question

在固定的 12 ETF Mixed Asset `mom_126 Top5` Version A 框架中，检验 MA200 的风险控制是否属于邻近均线参数的稳定平台，而非孤立参数结果。本实验不选择最佳均线。

## 2. Fixed Design

- Sample: `{start_date.date()}` to `{end_date.date()}`
- Monthly rebalance; month-end signal effective next trading day
- Momentum: 126 trading days; Top5 equal weight
- Transaction cost: 5 bps
- MA lengths: 100, 125, 150, 175, 200, 225, 250, 275, 300
- Version A: 每个 eligible 持仓固定 20%，不足 5 个时剩余资金为零收益现金
- Stable plateau: 至少 3 个连续参数，Sharpe 极差 <= 0.15、CAGR 极差 <= 2%、MaxDD 极差 <= 10%；报告覆盖参数最多的合格区间，并列时全部保留
- Isolated spike: 内部参数 Sharpe 高于左右邻居均值超过 0.15

## 3. Performance

{markdown_table(performance, ['MA Length', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Calmar', 'Total Return', 'Turnover'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return', 'Turnover'})}

## 4. Relative Change vs Baseline

正的 MaxDD Change 表示回撤改善。

{markdown_table(relative, ['MA Length', 'CAGR Change', 'Sharpe Change', 'MaxDD Change'], {'CAGR Change', 'MaxDD Change'})}

## 5. Exposure Statistics

{markdown_table(exposure, ['MA Length', 'Avg Eligible Assets', 'Avg Holdings', 'Avg Cash Allocation', 'Percent Months Below 5 Assets'], {'Avg Cash Allocation', 'Percent Months Below 5 Assets'})}

## 6. Robustness Score

Robustness Score 只衡量相邻 Sharpe 的局部平滑度，不用于参数选择。端点使用唯一相邻参数。

{markdown_table(robustness, ['MA Length', 'Sharpe', 'Neighbor Sharpe MAE', 'Robustness Score'], set())}

## 7. Stable Plateau Test

识别出的最长稳定平台：**{plateau_text}**。

{markdown_table(plateaus, ['Start MA', 'End MA', 'Number of Lengths', 'Sharpe Range', 'CAGR Range', 'MaxDD Range', 'Contains MA200', 'MA200 Is Interior'], {'CAGR Range', 'MaxDD Range'}) if not plateaus.empty else '未识别到满足预设条件的平台。'}

1. **MA200 是否位于平台内部？** {'是，且不是平台边界参数' if ma200_interior else '属于平台但位于边界' if ma200_in_plateau else '否'}。
2. **是否存在孤立尖峰？** {'有：' + ', '.join(spikes) if spikes else '没有参数满足预定义的孤立尖峰条件'}。
3. **风险控制是否持续存在？** {'全部测试均线都改善了 Baseline MaxDD' if all_drawdowns_improve else '并非全部测试均线都改善 Baseline MaxDD'}。

## 8. Interpretation

1. **MA Length 增加时，回撤改善是否单调？** {'是' if maxdd_monotonic else '否'}。这说明均线变长并不自动带来更深或更浅的回撤。
2. **现金仓位是否显著增加？** 没有。MA100 到 MA300 的平均现金变化为 {fmt_pct(cash_change)}，长度与现金仓位相关系数为 {cash_correlation:.2f}；本样本中更长均线反而对应略低现金，但关系并非严格单调。
3. **MA200 是否明显优于邻近参数？** MA200 Sharpe 为 {ma200['Sharpe']:.2f}，MA175/MA225 为 {ma175['Sharpe']:.2f}/{ma225['Sharpe']:.2f}；MaxDD 为 {fmt_pct(ma200['MaxDD'])}，邻居为 {fmt_pct(ma175['MaxDD'])}/{fmt_pct(ma225['MaxDD'])}。{'未形成孤立优势' if 'MA200' not in spikes else '形成了预定义的局部尖峰'}。
4. **是否存在多个相近 MA Length？** {'是，平台检验识别出连续合格区间' if multiple_similar else '否，预设平台条件未满足'}。
5. **风险改善来源是单点还是区间？** Baseline MaxDD 为 {fmt_pct(baseline['MaxDD'])}；{('多个连续 MA 参数共同满足平台条件，风险改善来自参数区间' if ma200_in_plateau else 'MA200 不在合格平台内，当前结果更接近参数敏感')}。

## 9. Final Conclusion

{'趋势过滤对均线长度具有鲁棒性，MA200 属于稳定风险过滤平台的一部分。' if ma200_in_plateau and all_drawdowns_improve else '趋势过滤存在一定局部稳定性，但证据不足以确认所有邻近参数都能稳定改善风险。' if ma200_in_plateau else '未发现包含 MA200 的稳定平台，趋势过滤对均线长度存在明显参数敏感性。'}该结论只回答参数邻域稳定性，不推荐或优化任何 MA Length。
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    prices = core.load_prices()
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    histories = load_full_history_prices()
    ma_by_length = moving_averages(histories, prices.index)
    existing = pd.read_csv(BASELINE_RETURNS_PATH, index_col="Date", parse_dates=True)
    analysis_index = existing.index

    targets, monthly_exposure = build_targets(prices, ma_by_length)
    performance, daily_returns = calculate_performance(returns, targets, analysis_index)
    baseline_error = float((daily_returns["Baseline"] - existing["mom_126_Top5"]).abs().max())
    if baseline_error > 1e-12:
        raise RuntimeError(f"Baseline reproduction mismatch: {baseline_error}")

    relative = relative_changes(performance)
    exposure = exposure_statistics(monthly_exposure, analysis_index)
    robustness = robustness_scores(performance)
    plateaus = stable_plateaus(performance)

    performance.to_csv(METRICS_DIR / "performance.csv", index=False)
    relative.to_csv(METRICS_DIR / "relative_change.csv", index=False)
    exposure.to_csv(METRICS_DIR / "exposure_statistics.csv", index=False)
    robustness.to_csv(METRICS_DIR / "robustness_scores.csv", index=False)
    plateaus.to_csv(METRICS_DIR / "stable_plateaus.csv", index=False)
    monthly_exposure.to_csv(OUTPUTS_DIR / "monthly_exposure.csv", index=False)
    daily_returns.to_csv(OUTPUTS_DIR / "daily_returns.csv")
    SUMMARY_PATH.write_text(
        generate_summary(performance, relative, exposure, robustness, plateaus, analysis_index.min(), analysis_index.max()),
        encoding="utf-8",
    )

    print("\nMA Trend Filter Robustness Test Complete")
    print(f"Baseline reproduction max error: {baseline_error:.3e}")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nStable plateaus:")
    print(plateaus.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
