# VB Bucket Analysis

Source: `xau/data/optimization/vb/*/unified_trades.csv`

Output purpose: identify which VB trade buckets are structurally better or worse. Entry-time buckets such as ADX and ATR ratio can become live filters; post-trade buckets such as R, PnL result, SL updates, and holding bucket are diagnostics only.

## Variant Overview

| Variant | Trades | Profit % | PF | Avg R | Sum R | Avg SL Updates | Net PnL |
|---|---:|---:|---:|---:|---:|---:|---:|
| 00_baseline_current_v1_default | 281 | 43.77 | 2.1181 | 0.3439 | 96.6316 | 12.33 | 2649.077 |
| 01_close_breakout_confirm | 228 | 44.3 | 1.9901 | 0.3004 | 68.4948 | 11.76 | 1834.302 |
| 02_candle_close_quality | 224 | 44.2 | 2.1611 | 0.3266 | 73.1655 | 11.96 | 2007.8832 |
| 03_adx20_rising | 189 | 44.97 | 2.1466 | 0.4091 | 77.3141 | 11.94 | 1714.6147 |
| 04_atr_ratio_1_1 | 185 | 46.49 | 2.1802 | 0.3163 | 58.5091 | 12.1 | 1796.0101 |
| 05_overextension_filter | 242 | 42.56 | 1.8795 | 0.274 | 66.2967 | 11.58 | 1809.2228 |
| 06_early_failure_exit | 341 | 41.06 | 1.7104 | 0.1874 | 63.8905 | 7.65 | 1740.3254 |
| 07_candle_quality_adx20_rising | 150 | 45.33 | 1.9321 | 0.3674 | 55.1082 | 11.15 | 1188.9883 |

## Top adx_bucket

| Variant | Bucket Value | Trades | Profit % | PF | Avg R | Sum R |
|---|---|---:|---:|---:|---:|---:|
| 04_atr_ratio_1_1 | adx_25_30 | 52 | 63.46 | 5.2273 | 0.8469 | 44.0397 |
| 02_candle_close_quality | adx_25_30 | 61 | 59.02 | 3.9257 | 0.6609 | 40.313 |
| 07_candle_quality_adx20_rising | adx_20_25 | 40 | 52.5 | 2.6447 | 0.6287 | 25.1474 |
| 00_baseline_current_v1_default | adx_25_30 | 68 | 50.0 | 2.9652 | 0.5857 | 39.8302 |
| 03_adx20_rising | adx_25_30 | 58 | 48.28 | 2.3273 | 0.5359 | 31.0827 |
| 05_overextension_filter | adx_20_25 | 81 | 43.21 | 2.7302 | 0.4729 | 38.302 |
| 01_close_breakout_confirm | adx_25_30 | 66 | 50.0 | 2.765 | 0.4638 | 30.6139 |
| 03_adx20_rising | adx_20_25 | 79 | 45.57 | 2.4133 | 0.4218 | 33.3195 |

## Top atr_ratio_bucket

| Variant | Bucket Value | Trades | Profit % | PF | Avg R | Sum R |
|---|---|---:|---:|---:|---:|---:|
| 02_candle_close_quality | atrr_1_25_1_5 | 36 | 52.78 | 3.7872 | 0.8546 | 30.7641 |
| 00_baseline_current_v1_default | atrr_1_25_1_5 | 38 | 52.63 | 3.9557 | 0.8402 | 31.9274 |
| 04_atr_ratio_1_1 | atrr_1_25_1_5 | 44 | 54.55 | 3.9692 | 0.811 | 35.6842 |
| 01_close_breakout_confirm | atrr_1_25_1_5 | 34 | 50.0 | 3.207 | 0.7391 | 25.128 |
| 03_adx20_rising | atrr_1_25_1_5 | 24 | 58.33 | 3.4957 | 0.7298 | 17.5144 |
| 05_overextension_filter | atrr_1_25_1_5 | 36 | 50.0 | 3.298 | 0.6938 | 24.9776 |
| 07_candle_quality_adx20_rising | atrr_1_25_1_5 | 27 | 55.56 | 2.6946 | 0.6568 | 17.7331 |
| 06_early_failure_exit | atrr_1_25_1_5 | 45 | 48.89 | 2.8235 | 0.5398 | 24.2897 |

## Top sl_update_bucket

| Variant | Bucket Value | Trades | Profit % | PF | Avg R | Sum R |
|---|---|---:|---:|---:|---:|---:|
| 06_early_failure_exit | sl_updates_gt_10 | 98 | 81.63 | 31.9219 | 1.433 | 140.4311 |
| 03_adx20_rising | sl_updates_gt_10 | 90 | 77.78 | 27.7546 | 1.3572 | 122.1522 |
| 00_baseline_current_v1_default | sl_updates_gt_10 | 132 | 78.03 | 27.7555 | 1.3363 | 176.3945 |
| 07_candle_quality_adx20_rising | sl_updates_gt_10 | 68 | 79.41 | 29.6253 | 1.3066 | 88.8462 |
| 02_candle_close_quality | sl_updates_gt_10 | 102 | 78.43 | 25.6202 | 1.2886 | 131.4417 |
| 01_close_breakout_confirm | sl_updates_gt_10 | 106 | 78.3 | 20.5977 | 1.2374 | 131.163 |
| 05_overextension_filter | sl_updates_gt_10 | 110 | 73.64 | 19.3608 | 1.2137 | 133.5067 |
| 04_atr_ratio_1_1 | sl_updates_gt_10 | 87 | 79.31 | 23.0705 | 1.1639 | 101.2568 |

## Top post_entry_holding_bucket

| Variant | Bucket Value | Trades | Profit % | PF | Avg R | Sum R |
|---|---|---:|---:|---:|---:|---:|
| 06_early_failure_exit | hold_25_plus | 66 | 98.48 | 459.4093 | 2.0603 | 135.9817 |
| 00_baseline_current_v1_default | hold_25_plus | 104 | 86.54 | 49.2318 | 1.7027 | 177.0825 |
| 07_candle_quality_adx20_rising | hold_25_plus | 49 | 83.67 | 40.0872 | 1.6907 | 82.844 |
| 03_adx20_rising | hold_25_plus | 73 | 78.08 | 31.2891 | 1.6478 | 120.2916 |
| 01_close_breakout_confirm | hold_25_plus | 80 | 85.0 | 38.3006 | 1.5941 | 127.5302 |
| 02_candle_close_quality | hold_25_plus | 79 | 84.81 | 35.4454 | 1.5918 | 125.7538 |
| 04_atr_ratio_1_1 | hold_25_plus | 64 | 87.5 | 50.7119 | 1.5281 | 97.8 |
| 05_overextension_filter | hold_25_plus | 88 | 78.41 | 23.1854 | 1.487 | 130.8593 |

## Weak adx_bucket

| Variant | Bucket Value | Trades | Profit % | PF | Avg R | Sum R |
|---|---|---:|---:|---:|---:|---:|
| 05_overextension_filter | adx_lt20 | 23 | 26.09 | 0.9364 | -0.106 | -2.4373 |
| 02_candle_close_quality | adx_lt20 | 20 | 35.0 | 0.7121 | -0.0235 | -0.4703 |
| 01_close_breakout_confirm | adx_lt20 | 20 | 40.0 | 0.7607 | 0.0243 | 0.4857 |
| 06_early_failure_exit | adx_ge30 | 91 | 37.36 | 1.3959 | 0.1119 | 10.1823 |
| 06_early_failure_exit | adx_lt20 | 37 | 40.54 | 1.0343 | 0.1389 | 5.1384 |
| 04_atr_ratio_1_1 | adx_ge30 | 69 | 40.58 | 1.5055 | 0.1465 | 10.11 |
| 06_early_failure_exit | adx_20_25 | 132 | 40.91 | 1.8302 | 0.1569 | 20.7111 |
| 04_atr_ratio_1_1 | adx_20_25 | 54 | 42.59 | 1.8049 | 0.1621 | 8.7522 |

## Weak atr_ratio_bucket

| Variant | Bucket Value | Trades | Profit % | PF | Avg R | Sum R |
|---|---|---:|---:|---:|---:|---:|
| 04_atr_ratio_1_1 | atrr_lt1_1 | 36 | 38.89 | 1.0379 | -0.0679 | -2.4459 |
| 05_overextension_filter | atrr_1_1_1_25 | 69 | 40.58 | 1.0958 | 0.0732 | 5.0492 |
| 02_candle_close_quality | atrr_1_1_1_25 | 75 | 41.33 | 1.3567 | 0.1181 | 8.8598 |
| 06_early_failure_exit | atrr_lt1_1 | 177 | 37.85 | 1.3844 | 0.1357 | 24.0191 |
| 06_early_failure_exit | atrr_1_1_1_25 | 105 | 43.81 | 1.6463 | 0.1414 | 14.8444 |
| 01_close_breakout_confirm | atrr_lt1_1 | 105 | 40.95 | 1.3018 | 0.1509 | 15.8472 |
| 07_candle_quality_adx20_rising | atrr_1_1_1_25 | 50 | 42.0 | 1.1613 | 0.1843 | 9.2125 |
| 00_baseline_current_v1_default | atrr_lt1_1 | 143 | 38.46 | 1.756 | 0.235 | 33.6 |

## Weak adx_bucket__atr_ratio_bucket

| Variant | Bucket Value | Trades | Profit % | PF | Avg R | Sum R |
|---|---|---:|---:|---:|---:|---:|
| 02_candle_close_quality | adx_ge30__atrr_1_1_1_25 | 20 | 30.0 | 0.7426 | -0.1648 | -3.2968 |
| 04_atr_ratio_1_1 | adx_ge30__atrr_1_1_1_25 | 28 | 35.71 | 0.737 | -0.1261 | -3.5313 |
| 05_overextension_filter | adx_ge30__atrr_lt1_1 | 29 | 37.93 | 0.6907 | -0.0491 | -1.4236 |
| 05_overextension_filter | adx_ge30__atrr_1_1_1_25 | 20 | 45.0 | 0.7731 | -0.0332 | -0.6637 |
| 06_early_failure_exit | adx_ge30__atrr_1_1_1_25 | 26 | 38.46 | 1.1425 | -0.0137 | -0.3559 |
| 03_adx20_rising | adx_20_25__atrr_1_1_1_25 | 30 | 40.0 | 0.945 | -0.0063 | -0.1886 |
| 06_early_failure_exit | adx_ge30__atrr_lt1_1 | 36 | 36.11 | 0.9065 | 0.0033 | 0.1191 |
| 07_candle_quality_adx20_rising | adx_25_30__atrr_lt1_1 | 24 | 41.67 | 1.0843 | 0.0073 | 0.1763 |

## Live Filter Takeaways

- Baseline ADX `adx_25_30` is the strongest single entry-time ADX bucket; `adx_lt20` is clearly weaker.
- Baseline ATR ratio `atrr_1_25_1_5` is the strongest single entry-time volatility bucket; `atrr_lt1_1` is materially weaker.
- Very high `sl_update_count` and long `post_entry_holding_bucket` show that VB makes money when the breakout follows through. These are useful for exit diagnostics, not entry filters.
- For live filtering, prioritize tests around ADX floor/rising behavior and ATR ratio lower bound. Avoid turning post-entry labels into entry rules.

## Reading Notes

- `profit_ratio_pct` is the simple percentage of trades with positive net PnL; it is not the engine's win-rate label.
- `avg_r` and `sum_r` normalize results by initial risk, so they are better than raw PnL for filter research.
- `sl_update_bucket`, `post_entry_holding_bucket`, `pnl_result`, and `r_multiple_bucket` are outcome diagnostics. Do not use them directly as entry filters because they are only known after entry or after exit.
- `adx_bucket` and `atr_ratio_bucket` are usable pre-trade regime features and are the first fields to inspect for hard filters.
