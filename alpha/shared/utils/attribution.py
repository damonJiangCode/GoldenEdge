from __future__ import annotations

import numpy as np
import pandas as pd

from shared.utils import cross_sectional as core


def build_targets(
    prices: pd.DataFrame,
    momentum_window: int,
    top_n: int,
    excluded_symbols: set[str],
) -> tuple[dict[pd.Timestamp, pd.Series], pd.DataFrame]:
    eligible = [symbol for symbol in prices.columns if symbol not in excluded_symbols]
    if len(eligible) < top_n:
        raise ValueError(f"Need at least {top_n} eligible symbols after exclusions.")

    momentum = prices / prices.shift(momentum_window) - 1
    targets = {}
    selection_rows = []
    for rebalance_date in core.month_end_dates(prices.index):
        scores = momentum.loc[rebalance_date, eligible].dropna()
        if len(scores) != len(eligible):
            continue
        location = prices.index.get_loc(rebalance_date)
        if location + 1 >= len(prices.index):
            continue

        effective_date = prices.index[location + 1]
        ranked = scores.sort_values(ascending=False)
        selected = ranked.head(top_n).index.tolist()
        target = pd.Series(0.0, index=prices.columns)
        target.loc[selected] = 1.0 / top_n
        targets[effective_date] = target
        for symbol in selected:
            selection_rows.append(
                {
                    "rebalance_date": rebalance_date,
                    "effective_date": effective_date,
                    "symbol": symbol,
                    "rank": int(ranked.index.get_loc(symbol) + 1),
                    "momentum": ranked.loc[symbol],
                    "target_weight": target.loc[symbol],
                }
            )
    return targets, pd.DataFrame(selection_rows)


def simulate_with_attribution(
    returns: pd.DataFrame,
    targets: dict[pd.Timestamp, pd.Series],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not targets:
        raise ValueError("No valid rebalance targets.")

    current_weights = pd.Series(0.0, index=returns.columns)
    portfolio_rows = []
    contribution_rows = []
    weight_rows = []
    for date, asset_returns in returns.loc[min(targets):].iterrows():
        target = targets.get(date)
        if target is not None:
            trades = (target - current_weights).abs()
            turnover = float(trades.sum())
            cost_by_asset = trades * core.TRADING_COST
            current_weights = target.copy()
        else:
            turnover = 0.0
            cost_by_asset = pd.Series(0.0, index=returns.columns)

        gross_contributions = current_weights * asset_returns
        net_contributions = gross_contributions - cost_by_asset
        gross_return = float(gross_contributions.sum())
        portfolio_rows.append(
            {
                "Date": date,
                "return": float(net_contributions.sum()),
                "gross_return": gross_return,
                "cost": float(cost_by_asset.sum()),
                "turnover": turnover,
            }
        )
        contribution_rows.append({"Date": date, **net_contributions.to_dict()})
        weight_rows.append({"Date": date, **current_weights.to_dict()})

        denominator = 1 + gross_return
        if denominator > 0:
            current_weights = current_weights * (1 + asset_returns) / denominator
        else:
            current_weights = pd.Series(0.0, index=returns.columns)

    portfolio = pd.DataFrame(portfolio_rows).set_index("Date")
    contributions = pd.DataFrame(contribution_rows).set_index("Date")
    weights = pd.DataFrame(weight_rows).set_index("Date")
    return portfolio, contributions, weights


def calculate_asset_contributions(
    returns: pd.DataFrame,
    portfolio: pd.DataFrame,
    contribution_rates: pd.DataFrame,
    weights: pd.DataFrame,
    selections: pd.DataFrame,
    analysis_index: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    portfolio = portfolio.reindex(analysis_index)
    contribution_rates = contribution_rates.reindex(analysis_index)
    weights = weights.reindex(analysis_index)
    asset_returns = returns.reindex(analysis_index)

    equity = (1 + portfolio["return"]).cumprod()
    equity_before = equity.shift(1, fill_value=1.0)
    pnl = contribution_rates.mul(equity_before, axis=0)
    total_return = float(equity.iloc[-1] - 1)
    in_sample = selections.loc[
        pd.to_datetime(selections["effective_date"]).between(analysis_index.min(), analysis_index.max())
    ]
    rebalance_count = in_sample["effective_date"].nunique()
    selection_count = in_sample.groupby("symbol").size()

    rows = []
    daily_rows = []
    for symbol in returns.columns:
        held = weights[symbol] > 1e-12
        total_contribution = float(pnl[symbol].sum())
        rows.append(
            {
                "symbol": symbol,
                "selection_count": int(selection_count.get(symbol, 0)),
                "selection_pct": selection_count.get(symbol, 0) / rebalance_count,
                "avg_weight": weights.loc[held, symbol].mean() if held.any() else 0.0,
                "avg_return_when_held": asset_returns.loc[held, symbol].mean() if held.any() else np.nan,
                "total_contribution": total_contribution,
                "contribution_pct": total_contribution / total_return,
            }
        )
        daily_rows.append(
            pd.DataFrame(
                {
                    "Date": analysis_index,
                    "symbol": symbol,
                    "weight": weights[symbol].values,
                    "asset_return": asset_returns[symbol].values,
                    "net_return_contribution": contribution_rates[symbol].values,
                    "pnl_contribution": pnl[symbol].values,
                }
            )
        )

    contribution = pd.DataFrame(rows).sort_values("total_contribution", ascending=False).reset_index(drop=True)
    daily = pd.concat(daily_rows, ignore_index=True).sort_values(["Date", "symbol"])
    if abs(contribution["total_contribution"].sum() - total_return) > 1e-10:
        raise RuntimeError("PnL attribution does not reconcile")
    return contribution, daily
