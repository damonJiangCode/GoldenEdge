# mean_reversion_v1 M15 Report Summary

Source: `/Users/damon/Documents/GoldenEdge/xau/data/reports/mr/v1/M15/report_*.json`

## Executive Summary

- Coverage: `2015-2025` (11 annual reports).
- Positive years: `11/11`.
- Average / median annual return: `66.33%` / `64.20%`.
- Best year: `2025` at `193.24%`.
- Worst year: `2017` at `11.97%`.
- Average / worst annual max drawdown: `2.04%` / `4.87%`.
- Pooled trades: `22140`; pooled net PnL: `7296.41`; pooled PF: `5.690`.
- Reports ending with an open position: `1/11`; combined year-end open-position effect: `0.16`.

## Aggregate Metrics

| Metric | Value |
|---|---:|
| Simple sum return % | 729.66 |
| Hypothetical compounded return % | 16913.74 |
| Average annual PF | 5.75 |
| Sum report net PnL | 7296.57 |
| Sum closed-trade net PnL | 7296.41 |
| Year-end open-position effect | 0.16 |
| Pooled win rate % | 8.04 |
| Pooled expectancy / trade | 0.33 |
| Median trade PnL | -0.06 |
| Average winning trade | 4.97 |
| Average losing trade abs | 0.08 |
| Average win / average loss | 65.08 |
| Best trade | 78.68 |
| Worst trade | -55.08 |
| Average holding bars | 3.00 |
| Median holding bars | 2.00 |
| Maximum holding bars | 315.00 |
| Total commission | 1107.00 |
| Total swap | 0.00 |
| Average R multiple | 0.02 |
| Sum R multiple | 341.34 |

## Annual Performance

| Year | Trades | Win % | Report Net | Closed Net | Open Δ | Return % | PF | Expectancy | Max DD % | Commission |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2015 | 1857.00 | 5.01 | 169.94 | 169.94 | -0.00 | 16.99 | 2.57 | 0.09 | 1.32 | 92.85 |
| 2016 | 1947.00 | 6.16 | 328.83 | 328.83 | -0.00 | 32.88 | 3.44 | 0.17 | 2.21 | 97.35 |
| 2017 | 2097.00 | 5.53 | 119.70 | 119.70 | -0.00 | 11.97 | 1.81 | 0.06 | 1.72 | 104.85 |
| 2018 | 2274.00 | 7.04 | 229.50 | 229.50 | -0.00 | 22.95 | 2.81 | 0.10 | 0.81 | 113.70 |
| 2019 | 2092.00 | 7.93 | 318.64 | 318.64 | -0.00 | 31.86 | 3.50 | 0.15 | 1.31 | 104.60 |
| 2020 | 1774.00 | 8.85 | 839.25 | 839.25 | -0.00 | 83.93 | 9.38 | 0.47 | 2.33 | 88.70 |
| 2021 | 2118.00 | 9.25 | 684.82 | 684.82 | -0.00 | 68.48 | 6.94 | 0.32 | 1.31 | 105.90 |
| 2022 | 2146.00 | 9.65 | 864.63 | 864.47 | 0.16 | 86.46 | 8.41 | 0.40 | 2.07 | 107.33 |
| 2023 | 1827.00 | 9.69 | 641.95 | 641.95 | -0.00 | 64.20 | 7.46 | 0.35 | 2.24 | 91.35 |
| 2024 | 1986.00 | 10.02 | 1166.91 | 1166.91 | -0.00 | 116.69 | 10.56 | 0.59 | 2.26 | 99.30 |
| 2025 | 2022.00 | 9.35 | 1932.41 | 1932.41 | -0.00 | 193.24 | 6.40 | 0.96 | 4.87 | 101.10 |

## Trade Breakdown By Side

| Group | Trades | Win % | Net PnL | PF | Expectancy | Avg Hold |
|---|---:|---:|---:|---:|---:|---:|
| long | 10168.00 | 8.64 | 3773.16 | 7.65 | 0.37 | 2.97 |
| short | 11972.00 | 7.53 | 3523.25 | 4.56 | 0.29 | 3.02 |

## Trade Breakdown By Exit Reason

| Group | Trades | Win % | Net PnL | PF | Expectancy | Avg Hold |
|---|---:|---:|---:|---:|---:|---:|
| SL | 20347.00 | 0.00 | -1545.86 | 0.00 | -0.08 | 2.69 |
| TP | 1793.00 | 99.27 | 8842.27 | 889.43 | 4.93 | 6.49 |

## Filter Activity Totals

| Filter / Counter | Total |
|---|---:|
| atr_ratio_filter_reject_count | 6756.00 |
| breakeven_move_count | 21771.00 |
| fat_tail_filter_reject_count | 22922.00 |
| session_reject_count | 0.00 |
| trend_filter_reject_count | 42898.00 |

## Common Parameters

| Parameter | Value |
|---|---:|
| ema_period | 36.00 |
| atr_period | 7.00 |
| atr_ratio_lookback | 160.00 |
| atr_ratio_min | 0.30 |
| atr_ratio_max | 2.00 |
| band_atr_mult | 2.25 |
| sl_atr_mult | 8.00 |
| adx_period | 28.00 |
| wick_body_ratio | 1.50 |
| fat_tail_body_lookback | 3.00 |
| fat_tail_body_mult | 2.50 |
| breakeven_retrace_ratio | 2.00 |
| entry_logic | touch EMA±k*ATR with candle confirmation; skip fat-tail bars |
| tp_logic | target EMA; move SL to breakeven after partial mean reversion |
| sl_logic | initial SL=entry±8.0*ATR; breakeven trail at retrace ratio |
| position_mode | single_position_no_pyramiding |

## Common Cost Settings

| Setting | Value |
|---|---:|
| point_value | 0.01 |
| pip_value | 0.01 |
| slippage_ticks | 1.00 |
| commission_per_trade | 0.05 |
| swap_long_per_lot_per_night | 0.00 |
| swap_short_per_lot_per_night | 0.00 |
| total_realized_swap | 0.00 |

## Reading Notes

- Each annual report resets to its own initial balance.
- Simple-sum and compounded returns are research summaries, not one continuous portfolio simulation.
- Annual report net PnL/return uses final equity and may include an open position at year end.
- Pooled trade PF is calculated from all closed trade net PnL across the included annual reports.
- OHLC backtests cannot reproduce tick-level intrabar ordering or production execution exactly.
