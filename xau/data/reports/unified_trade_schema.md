# Unified Trade Schema

Date: 2026-06-04

Purpose: define one trade-level schema for `VB`, `MR`, and `TF` so later regime analysis can compare strategy factors using the same fields.

## Scope

This schema is for research outputs, not broker execution logs.

The first target is:

```text
VB -> volatility_breakout_v1 -> XAUUSD H4
```

Later targets:

```text
MR -> mean_reversion variants
TF -> trend_following / trend_pullback variants
```

## Output Layout

Recommended path:

```text
xau/data/trades/<strategy>/<engine_version>/<timeframe>/trades_YEAR.csv
xau/data/trades/<strategy>/<engine_version>/<timeframe>/trades_all.csv
```

Example:

```text
xau/data/trades/VB/volatility_breakout_v1/H4/trades_2025.csv
xau/data/trades/VB/volatility_breakout_v1/H4/trades_all.csv
```

## Required Fields

These fields must exist for every strategy.

| Field | Type | Description |
| --- | --- | --- |
| `trade_id` | string | Stable id, recommended format: `<strategy>_<engine>_<year>_<index>` |
| `strategy` | string | Strategy factor name: `VB`, `MR`, or `TF` |
| `engine_version` | string | Concrete engine, for example `volatility_breakout_v1` |
| `symbol` | string | Trading symbol, for example `XAUUSD` |
| `timeframe` | string | Strategy timeframe, for example `H4` |
| `side` | string | `long` or `short` |
| `signal_time_utc` | datetime | Time when signal was generated |
| `entry_time_utc` | datetime | Actual entry time |
| `exit_time_utc` | datetime | Actual exit time |
| `entry_price` | float | Filled entry price after spread/slippage modeling |
| `exit_price` | float | Filled exit price after spread/slippage modeling |
| `initial_sl` | float | Initial stop loss at entry |
| `final_sl` | float | Last stop loss before exit |
| `exit_reason` | string | `SL`, `TRAIL`, `DONCHIAN_EXIT`, `EARLY_EXIT`, or strategy-specific value |
| `gross_pnl` | float | PnL before commission/swap |
| `commission` | float | Total commission for the trade |
| `swap` | float | Total swap for the trade |
| `net_pnl` | float | Final net PnL |
| `initial_risk_price` | float | Absolute price distance between entry and initial SL |
| `initial_risk_money` | float | Money risk represented by initial SL |
| `r_multiple` | float | `net_pnl / initial_risk_money` |
| `holding_bars` | int | Number of strategy timeframe bars held |
| `holding_hours` | float | Holding duration in hours |

## Recommended Entry Snapshot Fields

These fields should be captured from data available at or before entry.

| Field | Type | Description |
| --- | --- | --- |
| `entry_atr` | float | ATR at entry |
| `entry_atr_ratio` | float | ATR / slow ATR baseline at entry |
| `entry_spread_points` | float | Spread at entry |
| `entry_adx` | float | Strategy timeframe ADX if available |
| `entry_h1_adx` | float | H1 ADX if used by the engine |
| `entry_h1_adx_slope` | float | H1 ADX change or slope before entry |
| `entry_ema_fast` | float | Fast EMA at entry if available |
| `entry_ema_slow` | float | Slow EMA at entry if available |
| `entry_ema_slope` | float | EMA slope before entry if available |
| `entry_donchian_high` | float | Donchian upper level used for signal |
| `entry_donchian_low` | float | Donchian lower level used for signal |
| `entry_donchian_width_atr` | float | Donchian width normalized by ATR |
| `entry_bb_width_atr` | float | Bollinger width normalized by ATR if available |
| `entry_close_to_ema_atr` | float | Distance from close to EMA normalized by ATR |
| `entry_range_efficiency` | float | Directional efficiency before entry |

## Regime Fields

These fields are derived labels or buckets used for analysis. They must be generated only from information available before `entry_time_utc`.

| Field | Type | Description |
| --- | --- | --- |
| `regime_trend_strength` | string | Example buckets: `low`, `medium`, `high` |
| `regime_volatility` | string | Example buckets: `compressed`, `normal`, `expanded`, `extreme` |
| `regime_direction` | string | `uptrend`, `downtrend`, `range`, `unclear` |
| `regime_strategy_fit` | string | `VB_fit`, `MR_fit`, `TF_fit`, or `no_fit` |
| `adx_bucket` | string | ADX bucket used in analysis |
| `atr_ratio_bucket` | string | ATR ratio bucket used in analysis |
| `spread_bucket` | string | Spread bucket used in analysis |
| `session_utc` | string | Entry session bucket |
| `weekday` | int | UTC weekday, Monday = 0 |

## Derived Outcome Fields

These fields are not used as live features. They are allowed only for post-trade analysis.

| Field | Type | Description |
| --- | --- | --- |
| `is_win` | bool | `net_pnl > 0` |
| `return_pct_on_initial_balance` | float | Trade return relative to report initial balance |
| `max_favorable_excursion_r` | float | Best favorable excursion in R, if available |
| `max_adverse_excursion_r` | float | Worst adverse excursion in R, if available |
| `post_entry_holding_bucket` | string | Post-trade holding bucket, not a live feature |

## Hard Rules

- No future data may be used in entry snapshot or regime fields.
- `holding_bars`, `is_win`, `MFE`, `MAE`, and realized PnL are analysis labels, not live regime features.
- `strategy`, `engine_version`, and `timeframe` must be explicit on every row.
- Time fields must be UTC.
- If a strategy does not use a field, leave it empty rather than changing the column set.
- All strategies must export the same columns before being used by regime analysis.

## First Implementation Target

For `VB / volatility_breakout_v1 / H4`, existing report fields can map as:

| Existing Report Field | Unified Field |
| --- | --- |
| `side` | `side` |
| `signal_time` | `signal_time_utc` |
| `entry_time` | `entry_time_utc` |
| `exit_time` | `exit_time_utc` |
| `entry_price` | `entry_price` |
| `exit_price` | `exit_price` |
| `sl` | `final_sl` |
| `entry_atr` | `entry_atr` |
| `entry_atr_ratio` | `entry_atr_ratio` |
| `entry_h1_adx` | `entry_h1_adx` |
| `exit_reason` | `exit_reason` |
| `gross_pnl` | `gross_pnl` |
| `swap_total` | `swap` |
| `entry_commission + exit_commission` | `commission` |
| `net_pnl` | `net_pnl` |
| `holding_bars` | `holding_bars` |

Missing fields to add for VB export:

- `trade_id`
- `strategy`
- `engine_version`
- `symbol`
- `timeframe`
- `initial_sl`
- `initial_risk_price`
- `initial_risk_money`
- `r_multiple`
- `holding_hours`
- regime bucket fields
