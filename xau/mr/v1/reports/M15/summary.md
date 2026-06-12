# mean_reversion_v1 M15 Report Summary

Source: `/Users/damon/Documents/GoldenEdge/xau/mr/v1/reports/M15/report_*.json`

## Executive Summary

- Coverage: `2015-2025` (11 annual reports).
- Positive years: `11/11`.
- Average / median annual return: `66.43%` / `64.24%`.
- Best year: `2025` at `193.24%`.
- Worst year: `2017` at `11.97%`.
- Average / worst annual max drawdown: `2.04%` / `4.87%`.
- Pooled trades: `22123`; pooled net PnL: `7306.60`; pooled PF: `5.727`.
- Reports ending with an open position: `1/11`; combined year-end open-position effect: `0.16`.

## Aggregate Metrics

| Metric | Value |
|---|---:|
| Simple sum return % | 730.68 |
| Hypothetical compounded return % | 17035.58 |
| Average annual PF | 5.80 |
| Sum report net PnL | 7306.77 |
| Sum closed-trade net PnL | 7306.60 |
| Year-end open-position effect | 0.16 |
| Pooled win rate % | 8.05 |
| Pooled expectancy / trade | 0.33 |
| Median trade PnL | -0.06 |
| Average winning trade | 4.97 |
| Average losing trade abs | 0.08 |
| Average win / average loss | 65.46 |
| Best trade | 78.68 |
| Worst trade | -55.08 |
| Average holding bars | 3.00 |
| Median holding bars | 2.00 |
| Maximum holding bars | 315.00 |
| Total commission | 1106.15 |
| Total swap | 0.00 |
| Average R multiple | 0.02 |
| Sum R multiple | 342.52 |

## Annual Performance

| Year | Trades | Win % | Report Net | Closed Net | Open Δ | Return % | PF | Expectancy | Max DD % | Commission |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2015 | 1851.00 | 5.02 | 172.82 | 172.82 | -0.00 | 17.28 | 2.64 | 0.09 | 1.32 | 92.55 |
| 2016 | 1943.00 | 6.18 | 330.07 | 330.07 | -0.00 | 33.01 | 3.47 | 0.17 | 2.21 | 97.15 |
| 2017 | 2097.00 | 5.53 | 119.70 | 119.70 | -0.00 | 11.97 | 1.81 | 0.06 | 1.72 | 104.85 |
| 2018 | 2274.00 | 7.04 | 229.50 | 229.50 | -0.00 | 22.95 | 2.81 | 0.10 | 0.81 | 113.70 |
| 2019 | 2090.00 | 7.94 | 320.62 | 320.62 | -0.00 | 32.06 | 3.56 | 0.15 | 1.30 | 104.50 |
| 2020 | 1772.00 | 8.86 | 842.49 | 842.49 | -0.00 | 84.25 | 9.69 | 0.48 | 2.33 | 88.60 |
| 2021 | 2118.00 | 9.25 | 684.82 | 684.82 | -0.00 | 68.48 | 6.94 | 0.32 | 1.31 | 105.90 |
| 2022 | 2145.00 | 9.65 | 864.98 | 864.82 | 0.16 | 86.50 | 8.44 | 0.40 | 2.07 | 107.28 |
| 2023 | 1826.00 | 9.69 | 642.40 | 642.40 | -0.00 | 64.24 | 7.49 | 0.35 | 2.24 | 91.30 |
| 2024 | 1985.00 | 10.03 | 1166.97 | 1166.97 | -0.00 | 116.70 | 10.57 | 0.59 | 2.26 | 99.25 |
| 2025 | 2022.00 | 9.35 | 1932.41 | 1932.41 | -0.00 | 193.24 | 6.40 | 0.96 | 4.87 | 101.10 |

## Trade Breakdown By Side

| Group | Trades | Win % | Net PnL | PF | Expectancy | Avg Hold |
|---|---:|---:|---:|---:|---:|---:|
| long | 10156.00 | 8.65 | 3777.87 | 7.72 | 0.37 | 2.97 |
| short | 11967.00 | 7.53 | 3528.73 | 4.59 | 0.29 | 3.02 |

## Trade Breakdown By Exit Reason

| Group | Trades | Win % | Net PnL | PF | Expectancy | Avg Hold |
|---|---:|---:|---:|---:|---:|---:|
| SL | 20343.00 | 0.00 | -1545.62 | 0.00 | -0.08 | 2.69 |
| TP | 1780.00 | 100.00 | 8852.22 | 0.00 | 4.97 | 6.53 |

## Filter Activity Totals

| Filter / Counter | Total |
|---|---:|
| atr_ratio_filter_reject_count | 6756.00 |
| breakeven_move_count | 21767.00 |
| fat_tail_filter_reject_count | 22922.00 |
| insufficient_margin_reject_count | 0.00 |
| invalid_target_reject_count | 17.00 |
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
| margin_check | reject entry when post-commission balance is below required margin |

## Common Cost Settings

| Setting | Value |
|---|---:|
| point_value | 0.01 |
| pip_value | 0.01 |
| slippage_ticks | 1.00 |
| commission_per_trade | 0.05 |
| lot_size | 0.01 |
| contract_size | 100.00 |
| leverage | 100.00 |
| margin_formula | price * lot_size * contract_size / leverage |
| swap_long_per_lot_per_night | 0.00 |
| swap_short_per_lot_per_night | 0.00 |
| total_realized_swap | 0.00 |

## Reading Notes

- Each annual report resets to its own initial balance.
- Simple-sum and compounded returns are research summaries, not one continuous portfolio simulation.
- Annual report net PnL/return uses final equity and may include an open position at year end.
- Pooled trade PF is calculated from all closed trade net PnL across the included annual reports.
- OHLC backtests cannot reproduce tick-level intrabar ordering or production execution exactly.
