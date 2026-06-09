# volatility_breakout_v1 H4 Report Summary

Source: `/Users/damon/Documents/GoldenEdge/xau/data/reports/vb/v1/H4/report_*.json`

## Executive Summary

- Coverage: `2015-2025` (11 annual reports).
- Positive years: `11/11`.
- Average / median annual return: `25.73%` / `17.19%`.
- Best year: `2025` at `139.33%`.
- Worst year: `2018` at `1.18%`.
- Average / worst annual max drawdown: `9.28%` / `14.63%`.
- Pooled trades: `281`; pooled net PnL: `2649.08`; pooled PF: `2.118`.
- Reports ending with an open position: `4/11`; combined year-end open-position effect: `181.65`.

## Aggregate Metrics

| Metric | Value |
|---|---:|
| Simple sum return % | 283.07 |
| Hypothetical compounded return % | 778.19 |
| Average annual PF | 2.12 |
| Sum report net PnL | 2830.73 |
| Sum closed-trade net PnL | 2649.08 |
| Year-end open-position effect | 181.65 |
| Pooled win rate % | 43.77 |
| Pooled expectancy / trade | 9.43 |
| Median trade PnL | -3.20 |
| Average winning trade | 40.80 |
| Average losing trade abs | 15.00 |
| Average win / average loss | 2.72 |
| Best trade | 304.59 |
| Worst trade | -113.08 |
| Average holding bars | 23.24 |
| Median holding bars | 19.00 |
| Maximum holding bars | 100.00 |
| Total commission | 14.05 |
| Total swap | 0.00 |
| Average R multiple |  |
| Sum R multiple |  |

## Annual Performance

| Year | Trades | Win % | Report Net | Closed Net | Open Δ | Return % | PF | Expectancy | Max DD % | Commission |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2015 | 4.00 | 50.00 | 54.34 | 54.34 | -0.00 | 5.43 | 4.55 | 13.59 | 1.66 | 0.20 |
| 2016 | 10.00 | 40.00 | 34.62 | 34.62 | -0.00 | 3.46 | 1.43 | 3.46 | 4.95 | 0.50 |
| 2017 | 27.00 | 44.44 | 88.48 | 88.48 | -0.00 | 8.85 | 1.76 | 3.28 | 4.61 | 1.35 |
| 2018 | 32.00 | 37.50 | 11.84 | -5.53 | 17.37 | 1.18 | 0.96 | -0.17 | 6.39 | 1.62 |
| 2019 | 32.00 | 37.50 | 47.96 | -4.28 | 52.23 | 4.80 | 0.98 | -0.13 | 13.49 | 1.62 |
| 2020 | 30.00 | 36.67 | 196.49 | 196.49 | -0.00 | 19.65 | 1.58 | 6.55 | 14.63 | 1.50 |
| 2021 | 31.00 | 45.16 | 248.04 | 248.04 | -0.00 | 24.80 | 2.09 | 8.00 | 8.64 | 1.55 |
| 2022 | 33.00 | 42.42 | 171.89 | 162.19 | 9.70 | 17.19 | 1.55 | 4.91 | 10.85 | 1.67 |
| 2023 | 30.00 | 40.00 | 351.00 | 351.00 | -0.00 | 35.10 | 2.35 | 11.70 | 10.91 | 1.50 |
| 2024 | 20.00 | 40.00 | 232.72 | 232.72 | -0.00 | 23.27 | 1.90 | 11.64 | 13.75 | 1.00 |
| 2025 | 32.00 | 68.75 | 1393.34 | 1291.00 | 102.34 | 139.33 | 4.19 | 40.34 | 12.26 | 1.62 |

## Trade Breakdown By Side

| Group | Trades | Win % | Net PnL | PF | Expectancy | Avg Hold |
|---|---:|---:|---:|---:|---:|---:|
| long | 154.00 | 43.51 | 1897.17 | 2.28 | 12.32 | 22.29 |
| short | 127.00 | 44.09 | 751.91 | 1.84 | 5.92 | 24.40 |

## Trade Breakdown By Exit Reason

| Group | Trades | Win % | Net PnL | PF | Expectancy | Avg Hold |
|---|---:|---:|---:|---:|---:|---:|
| SL | 281.00 | 43.77 | 2649.08 | 2.12 | 9.43 | 23.24 |

## Filter Activity Totals

| Filter / Counter | Total |
|---|---:|
| adx_filter_reject_count | 534.00 |
| atr_ratio_filter_reject_count | 6631.00 |
| both_breakout_reject_count | 3.00 |
| session_reject_count | 0.00 |
| spread_filter_reject_count | 1047.00 |
| trail_move_count | 3546.00 |

## Common Parameters

| Parameter | Value |
|---|---:|
| donchian_breakout_period | 18.00 |
| donchian_exit_period | 10.00 |
| atr_period | 14.00 |
| atr_ratio_lookback | 100.00 |
| sl_atr_mult | 2.20 |
| trail_mode | chandelier |
| trail_atr_mult | 3.20 |
| entry_logic | intrabar donchian breakout (high/low trigger), next bar market entry |
| exit_logic | SL + trailing stop (chandelier/donchian) |
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
