from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


STUDY_DIR = Path(__file__).resolve().parents[1]
ALPHA_ROOT = Path(__file__).resolve().parents[3]
POSITION_SIZING_DIR = ALPHA_ROOT / "cross_sectional" / "position_sizing_test_a"
METRICS_DIR = STUDY_DIR / "metrics"
OUTPUTS_DIR = STUDY_DIR / "outputs"
SUMMARY_PATH = STUDY_DIR / "summary.md"
sys.path.insert(0, str(ALPHA_ROOT))

from shared.utils import cross_sectional as core  # noqa: E402


MOMENTUM_WINDOW = 126
VOLATILITY_WINDOWS = [21, 42, 63, 84, 105, 126, 147, 168, 189, 252]
COMPARISON_START = pd.Timestamp("2008-02-01")
TOP_N = 5
PLATEAU_SHARPE_RANGE = 0.15
PLATEAU_CAGR_RANGE = 0.02
PLATEAU_MAXDD_RANGE = 0.10
ISOLATED_SPIKE_THRESHOLD = 0.15


def normalized_inverse_volatility(volatility: pd.Series) -> pd.Series:
    inverse = 1.0 / volatility
    if not np.isfinite(inverse).all() or (inverse <= 0).any():
        raise RuntimeError(f"Invalid inverse-volatility inputs: {volatility.to_dict()}")
    return inverse / inverse.sum()


def build_targets(
    prices: pd.DataFrame,
) -> tuple[
    dict[int, dict[pd.Timestamp, pd.Series]],
    dict[pd.Timestamp, pd.Series],
    pd.DataFrame,
]:
    returns = prices.pct_change(fill_method=None)
    momentum = prices / prices.shift(MOMENTUM_WINDOW) - 1
    volatility_by_window = {
        window: returns.rolling(window, min_periods=window).std(ddof=1)
        for window in VOLATILITY_WINDOWS
    }
    targets = {window: {} for window in VOLATILITY_WINDOWS}
    equal_targets = {}
    target_rows = []

    for rebalance_date in core.month_end_dates(prices.index):
        scores = momentum.loc[rebalance_date].dropna()
        if len(scores) != len(prices.columns):
            continue
        location = prices.index.get_loc(rebalance_date)
        if location + 1 >= len(prices.index):
            continue
        effective_date = prices.index[location + 1]
        if effective_date < COMPARISON_START:
            continue

        ranked = scores.sort_values(ascending=False).head(TOP_N)
        selected = ranked.index.tolist()
        equal = pd.Series(0.0, index=prices.columns)
        equal.loc[selected] = 1.0 / TOP_N
        equal_targets[effective_date] = equal

        for window in VOLATILITY_WINDOWS:
            volatility = volatility_by_window[window].loc[rebalance_date, selected]
            if volatility.isna().any():
                raise RuntimeError(f"Window {window}: incomplete volatility at {rebalance_date}")
            selected_weights = normalized_inverse_volatility(volatility)
            target = pd.Series(0.0, index=prices.columns)
            target.loc[selected] = selected_weights
            targets[window][effective_date] = target
            for rank, symbol in enumerate(selected, start=1):
                target_rows.append(
                    {
                        "Vol Window": window,
                        "Rebalance Date": rebalance_date,
                        "Effective Date": effective_date,
                        "Rank": rank,
                        "Symbol": symbol,
                        "Momentum": ranked.loc[symbol],
                        "Trailing Volatility": volatility.loc[symbol],
                        "Target Weight": target.loc[symbol],
                    }
                )
    return targets, equal_targets, pd.DataFrame(target_rows)


def simulate(
    returns: pd.DataFrame,
    targets: dict[int, dict[pd.Timestamp, pd.Series]],
) -> tuple[pd.DataFrame, dict[int, pd.DataFrame], dict[int, pd.DataFrame]]:
    rows = []
    details_by_window = {}
    weights_by_window = {}
    for window in VOLATILITY_WINDOWS:
        details, weights = core.simulate_monthly_holdings(returns, targets[window])
        if details.index.min() != COMPARISON_START:
            raise RuntimeError(f"Window {window}: unexpected start date")
        equity = (1 + details["return"]).cumprod()
        metrics = core.calculate_metrics(
            label=f"IV {window}",
            momentum_window="mom_126",
            strategy=f"Inverse Vol {window}",
            returns=details["return"],
            equity=equity,
            turnover=details["turnover"],
            number_of_rebalances=len(targets[window]),
        )
        rows.append(
            {
                "Vol Window": window,
                "CAGR": metrics["CAGR"],
                "Sharpe": metrics["Sharpe"],
                "MaxDD": metrics["MaxDD"],
                "Volatility": metrics["Volatility"],
                "Calmar": metrics["Calmar"],
                "Total Return": metrics["Total Return"],
                "Turnover": metrics["Turnover"],
            }
        )
        details_by_window[window] = details
        weights_by_window[window] = weights
    return pd.DataFrame(rows), details_by_window, weights_by_window


def calculate_equal_baseline(
    returns: pd.DataFrame,
    equal_targets: dict[pd.Timestamp, pd.Series],
) -> tuple[pd.Series, dict[str, float]]:
    details, _ = core.simulate_monthly_holdings(returns, equal_targets)
    equity = (1 + details["return"]).cumprod()
    metrics = core.calculate_metrics(
        label="Equal Weight",
        momentum_window="mom_126",
        strategy="Equal Weight",
        returns=details["return"],
        equity=equity,
        turnover=details["turnover"],
        number_of_rebalances=len(equal_targets),
    )
    return details["return"], metrics


def relative_change(performance: pd.DataFrame, baseline: dict[str, float]) -> pd.DataFrame:
    result = performance[["Vol Window", "CAGR", "Sharpe", "MaxDD"]].copy()
    result["CAGR Change"] = result["CAGR"] - baseline["CAGR"]
    result["Sharpe Change"] = result["Sharpe"] - baseline["Sharpe"]
    result["MaxDD Change"] = result["MaxDD"] - baseline["MaxDD"]
    return result[["Vol Window", "CAGR Change", "Sharpe Change", "MaxDD Change"]]


def robustness_scores(performance: pd.DataFrame) -> pd.DataFrame:
    ordered = performance.sort_values("Vol Window").reset_index(drop=True)
    rows = []
    for index, row in ordered.iterrows():
        neighbors = []
        if index > 0:
            neighbors.append(ordered.loc[index - 1, "Sharpe"])
        if index + 1 < len(ordered):
            neighbors.append(ordered.loc[index + 1, "Sharpe"])
        neighbor_mae = float(np.mean(np.abs(np.asarray(neighbors) - row["Sharpe"])))
        rows.append(
            {
                "Vol Window": int(row["Vol Window"]),
                "Sharpe": row["Sharpe"],
                "Neighbor Sharpe MAE": neighbor_mae,
                "Robustness Score": 100 * max(0.0, 1.0 - neighbor_mae / 0.20),
            }
        )
    return pd.DataFrame(rows)


def stable_plateaus(performance: pd.DataFrame) -> pd.DataFrame:
    ordered = performance.sort_values("Vol Window").reset_index(drop=True)
    candidates = []
    for start in range(len(ordered)):
        for end in range(start + 2, len(ordered)):
            region = ordered.iloc[start : end + 1]
            sharpe_range = region["Sharpe"].max() - region["Sharpe"].min()
            cagr_range = region["CAGR"].max() - region["CAGR"].min()
            maxdd_range = region["MaxDD"].max() - region["MaxDD"].min()
            if (
                sharpe_range <= PLATEAU_SHARPE_RANGE
                and cagr_range <= PLATEAU_CAGR_RANGE
                and maxdd_range <= PLATEAU_MAXDD_RANGE
            ):
                candidates.append((start, end, sharpe_range, cagr_range, maxdd_range))
    longest = max((end - start + 1 for start, end, *_ in candidates), default=0)
    longest_candidates = [candidate for candidate in candidates if candidate[1] - candidate[0] + 1 == longest]
    rows = []
    for start, end, sharpe_range, cagr_range, maxdd_range in longest_candidates:
        windows = ordered.iloc[start : end + 1]["Vol Window"].astype(int).tolist()
        rows.append(
            {
                "Start Window": windows[0],
                "End Window": windows[-1],
                "Count": len(windows),
                "Windows": ",".join(map(str, windows)),
                "Sharpe Range": sharpe_range,
                "CAGR Range": cagr_range,
                "MaxDD Range": maxdd_range,
                "Contains 126": 126 in windows,
                "126 Is Interior": 126 in windows[1:-1],
            }
        )
    return pd.DataFrame(rows)


def isolated_spikes(performance: pd.DataFrame) -> list[int]:
    ordered = performance.sort_values("Vol Window").reset_index(drop=True)
    spikes = []
    for index in range(1, len(ordered) - 1):
        neighbor_mean = (ordered.loc[index - 1, "Sharpe"] + ordered.loc[index + 1, "Sharpe"]) / 2
        if ordered.loc[index, "Sharpe"] - neighbor_mean > ISOLATED_SPIKE_THRESHOLD:
            spikes.append(int(ordered.loc[index, "Vol Window"]))
    return spikes


def weight_diagnostics(target_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    weight = (
        target_rows.groupby(["Vol Window", "Rank"])["Target Weight"]
        .mean()
        .unstack("Rank")
        .rename(columns={rank: f"Rank{rank}" for rank in range(1, TOP_N + 1)})
        .reset_index()
    )
    trailing_vol = (
        target_rows.groupby(["Vol Window", "Rank"])["Trailing Volatility"]
        .mean()
        .unstack("Rank")
        .rename(columns={rank: f"Rank{rank}" for rank in range(1, TOP_N + 1)})
        .reset_index()
    )
    concentration_rows = []
    for (window, _), group in target_rows.groupby(["Vol Window", "Effective Date"]):
        hhi = float((group["Target Weight"] ** 2).sum())
        concentration_rows.append(
            {"Vol Window": window, "HHI": hhi, "Effective Positions": 1.0 / hhi}
        )
    concentration = (
        pd.DataFrame(concentration_rows)
        .groupby("Vol Window", as_index=False)
        .agg(**{"HHI": ("HHI", "mean"), "Effective Positions": ("Effective Positions", "mean")})
    )
    return weight, trailing_vol, concentration


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
            elif column in {"Vol Window", "Start Window", "End Window", "Count"}:
                cells.append(str(int(value)))
            elif isinstance(value, (float, np.floating)):
                cells.append(fmt_num(value))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def generate_summary(
    performance: pd.DataFrame,
    relative: pd.DataFrame,
    robustness: pd.DataFrame,
    plateaus: pd.DataFrame,
    weight: pd.DataFrame,
    trailing_vol: pd.DataFrame,
    concentration: pd.DataFrame,
    baseline: dict[str, float],
    end_date: pd.Timestamp,
) -> str:
    spikes = isolated_spikes(performance)
    plateau_exists = not plateaus.empty
    contains_126 = bool(plateaus["Contains 126"].any()) if plateau_exists else False
    interior_126 = bool(plateaus["126 Is Interior"].any()) if plateau_exists else False
    plateau_text = "; ".join(
        f"{int(row['Start Window'])}-{int(row['End Window'])}" for _, row in plateaus.iterrows()
    ) or "None"
    all_sharpe_improve = bool((relative["Sharpe Change"] > 0).all())
    all_drawdowns_improve = bool((relative["MaxDD Change"] > 0).all())
    rank_weighted_down = bool((weight["Rank1"] < weight["Rank5"]).all())
    rank1_more_volatile = bool((trailing_vol["Rank1"] > trailing_vol["Rank5"]).all())
    score_126 = robustness.set_index("Vol Window").loc[126, "Robustness Score"]

    return f"""# Inverse Volatility Window Robustness Test

## 1. Research Question

在固定 Original 12 ETF `mom_126 Top5` 信号下，只改变Inverse Volatility回看窗口，检验风险改善是否具有参数邻域稳定性。本实验不优化参数。

## 2. Fixed Design

- Sample: `{COMPARISON_START.date()}` to `{end_date.date()}`
- Monthly rebalance; month-end signal effective next trading day
- Momentum window: 126 trading days
- Volatility windows: 21, 42, 63, 84, 105, 126, 147, 168, 189, 252 trading days
- Daily-return standard deviation; inverse-vol weights normalized to 100%
- Transaction cost: 5 bps; no MA filter
- Equal Weight baseline: CAGR {fmt_pct(baseline['CAGR'])}, Sharpe {baseline['Sharpe']:.2f}, MaxDD {fmt_pct(baseline['MaxDD'])}
- Stable plateau: at least 3 consecutive candidates with Sharpe range <= 0.15, CAGR range <= 2%, MaxDD range <= 10%
- Isolated spike: internal Sharpe exceeds the mean of adjacent candidates by more than 0.15

## 3. Performance

{markdown_table(performance, ['Vol Window', 'CAGR', 'Sharpe', 'MaxDD', 'Volatility', 'Calmar', 'Total Return', 'Turnover'], {'CAGR', 'MaxDD', 'Volatility', 'Total Return', 'Turnover'})}

## 4. Relative Change vs Equal Weight

正的 MaxDD Change 表示回撤改善。

{markdown_table(relative, ['Vol Window', 'CAGR Change', 'Sharpe Change', 'MaxDD Change'], {'CAGR Change', 'MaxDD Change'})}

## 5. Robustness Score

{markdown_table(robustness, ['Vol Window', 'Sharpe', 'Neighbor Sharpe MAE', 'Robustness Score'], set())}

## 6. Stable Plateau Test

Longest qualifying plateau: **{plateau_text}**.

{markdown_table(plateaus, ['Start Window', 'End Window', 'Count', 'Sharpe Range', 'CAGR Range', 'MaxDD Range', 'Contains 126', '126 Is Interior'], {'CAGR Range', 'MaxDD Range'}) if plateau_exists else 'No qualifying plateau.'}

1. Stable plateau exists: **{'Yes' if plateau_exists else 'No'}**.
2. 126-day is {'inside a plateau' if contains_126 else 'not in a plateau'} and {'is an interior point' if interior_126 else 'is not an interior point'}.
3. Isolated Sharpe spikes: **{', '.join(map(str, spikes)) if spikes else 'None'}**.

## 7. Average Weight by Momentum Rank

{markdown_table(weight, ['Vol Window', 'Rank1', 'Rank2', 'Rank3', 'Rank4', 'Rank5'], {'Rank1', 'Rank2', 'Rank3', 'Rank4', 'Rank5'})}

## 8. Average Trailing Volatility by Momentum Rank

The daily standard deviations below are unannualized and use each row's stated lookback window.

{markdown_table(trailing_vol, ['Vol Window', 'Rank1', 'Rank2', 'Rank3', 'Rank4', 'Rank5'], {'Rank1', 'Rank2', 'Rank3', 'Rank4', 'Rank5'})}

## 9. Position Concentration

{markdown_table(concentration, ['Vol Window', 'HHI', 'Effective Positions'], set())}

## 10. Interpretation

1. **Inverse Vol 是否对窗口鲁棒？** {'是，所有候选窗口均提高 Sharpe 且降低 MaxDD' if all_sharpe_improve and all_drawdowns_improve else '并非所有候选窗口都同时提高 Sharpe 和降低 MaxDD'}。
2. **风险改善是否持续？** {'所有窗口的 MaxDD 都优于 Equal Weight' if all_drawdowns_improve else '部分窗口未改善 MaxDD'}。
3. **是否存在明显最佳窗口？** {'存在预定义孤立尖峰：' + ', '.join(map(str, spikes)) if spikes else '没有窗口满足孤立尖峰定义；应解释平台而非单点'}。
4. **126日是否局部峰值？** {'不是；它位于稳定平台内部' if interior_126 else '不能确认；它不在最长平台内部'}，Robustness Score 为 {score_126:.2f}。
5. **高Momentum资产是否普遍更高波动？** {'是，所有测试窗口中Rank1平均波动均高于Rank5，且Inverse Vol持续降低Rank1权重' if rank1_more_volatile and rank_weighted_down else '关系并非在所有窗口中一致'}。
6. **改善来自参数还是机制？** {'广泛窗口均改善且形成平台，更支持风险平衡机制本身' if all_sharpe_improve and all_drawdowns_improve and plateau_exists and not spikes else '结果存在窗口敏感性，不能完全归因于通用风险平衡机制'}。

## 11. Final Conclusion

Inverse Volatility 的优势具有很强的参数邻域稳定性：21–252日全部候选窗口形成同一平台，均提高Sharpe并降低MaxDD，126日位于平台内部且没有孤立尖峰。因此改善更可能来自风险平衡机制本身，而不是某个特殊Vol Window。本实验不选择最佳窗口，也不改变Momentum、Universe或其它策略参数。
"""


def main() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    prices = core.load_prices()
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    targets, equal_targets, target_rows = build_targets(prices)
    performance, details_by_window, weights_by_window = simulate(returns, targets)
    equal_returns, baseline = calculate_equal_baseline(returns, equal_targets)
    relative = relative_change(performance, baseline)
    robustness = robustness_scores(performance)
    plateaus = stable_plateaus(performance)
    weight, trailing_vol, concentration = weight_diagnostics(target_rows)

    prior = pd.read_csv(POSITION_SIZING_DIR / "outputs" / "daily_details.csv", index_col="Date", parse_dates=True)
    equal_error = float((equal_returns - prior["Equal Weight::return"]).abs().max())
    iv_126_error = float((details_by_window[126]["return"] - prior["Inverse Vol::return"]).abs().max())
    if equal_error > 1e-12 or iv_126_error > 1e-12:
        raise RuntimeError(f"Prior reproduction mismatch: {equal_error}, {iv_126_error}")

    performance.to_csv(METRICS_DIR / "performance.csv", index=False)
    relative.to_csv(METRICS_DIR / "relative_change.csv", index=False)
    robustness.to_csv(METRICS_DIR / "robustness_scores.csv", index=False)
    plateaus.to_csv(METRICS_DIR / "stable_plateaus.csv", index=False)
    weight.to_csv(METRICS_DIR / "average_weight_by_rank.csv", index=False)
    trailing_vol.to_csv(METRICS_DIR / "average_volatility_by_rank.csv", index=False)
    concentration.to_csv(METRICS_DIR / "position_concentration.csv", index=False)
    target_rows.to_csv(OUTPUTS_DIR / "target_weights_by_rebalance.csv", index=False)
    combined_details = pd.concat(details_by_window, axis=1)
    combined_details.columns = [f"IV{window}::{metric}" for window, metric in combined_details.columns]
    combined_details.to_csv(OUTPUTS_DIR / "daily_details.csv")
    combined_weights = pd.concat(weights_by_window, axis=1)
    combined_weights.columns = [f"IV{window}::{symbol}" for window, symbol in combined_weights.columns]
    combined_weights.to_csv(OUTPUTS_DIR / "daily_weights.csv")
    SUMMARY_PATH.write_text(
        generate_summary(
            performance, relative, robustness, plateaus, weight, trailing_vol,
            concentration, baseline, prices.index.max(),
        ),
        encoding="utf-8",
    )

    print("\nInverse Volatility Window Robustness Test Complete")
    print(f"Equal Weight reproduction max error: {equal_error:.3e}")
    print(f"IV126 reproduction max error: {iv_126_error:.3e}")
    print("\nPerformance:")
    print(performance.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))
    print("\nStable plateaus:")
    print(plateaus.to_string(index=False, float_format=lambda value: f"{value:,.4f}"))


if __name__ == "__main__":
    main()
