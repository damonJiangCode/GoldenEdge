# MR V1 Default vs Rolling-Island Comparison

Coverage: `2015-2025`, M15. Each year resets to initial balance `1000`.
Hypothetical compounded return is shown only as a research comparison.

## Overall Comparison

| Metric | Current Default | Rolling Consensus |
| --- | ---: | ---: |
| Positive years | 11/11 | 11/11 |
| Average annual return % | 66.33 | 69.53 |
| Median annual return % | 64.20 | 71.70 |
| Worst annual return % | 11.97 | 4.87 |
| Best annual return % | 193.24 | 214.66 |
| Simple-sum return % | 729.66 | 764.81 |
| Hypothetical compounded return % | 16913.74 | 19098.48 |
| Average annual PF | 5.75 | 3.42 |
| Pooled trade PF | 5.69 | 3.60 |
| Average annual max DD % | 2.04 | 4.46 |
| Worst annual max DD % | 4.87 | 11.41 |
| Total trades | 22140 | 25556 |
| Pooled win rate % | 8.04 | 7.78 |
| Pooled expectancy / trade | 0.33 | 0.30 |
| Pooled net PnL | 7296.41 | 7647.96 |
| Total commission | 1107.03 | 1277.83 |
| Average holding bars | 3.00 | 3.56 |

## Annual Comparison

| Year | Default Return % | Rolling Return % | Δ Return | Default PF | Rolling PF | Default DD % | Rolling DD % |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2015 | 16.99 | 18.64 | +1.64 | 2.57 | 2.31 | 1.32 | 1.52 |
| 2016 | 32.88 | 29.00 | -3.89 | 3.44 | 2.61 | 2.21 | 3.08 |
| 2017 | 11.97 | 4.87 | -7.10 | 1.81 | 1.22 | 1.72 | 4.57 |
| 2018 | 22.95 | 28.62 | +5.67 | 2.81 | 2.81 | 0.81 | 1.47 |
| 2019 | 31.86 | 26.72 | -5.15 | 3.50 | 2.27 | 1.31 | 4.33 |
| 2020 | 83.93 | 99.75 | +15.83 | 9.38 | 5.06 | 2.33 | 5.44 |
| 2021 | 68.48 | 71.70 | +3.22 | 6.94 | 3.99 | 1.31 | 3.50 |
| 2022 | 86.46 | 83.73 | -2.74 | 8.41 | 4.12 | 2.07 | 4.65 |
| 2023 | 64.20 | 72.31 | +8.11 | 7.46 | 5.13 | 2.24 | 4.41 |
| 2024 | 116.69 | 114.82 | -1.87 | 10.56 | 4.14 | 2.26 | 4.70 |
| 2025 | 193.24 | 214.66 | +21.42 | 6.40 | 3.94 | 4.87 | 11.41 |

## Parameter Differences

| Parameter | Current Default | Rolling Consensus | Same |
| --- | ---: | ---: | --- |
| ema_period | 36 | 50 | no |
| atr_period | 7 | 7 | yes |
| band_atr_mult | 2.25 | 2.25 | yes |
| sl_atr_mult | 8.0 | 10.0 | no |
| adx_period | 28 | 28 | yes |
| h1_adx_limit | 28.0 | 28.0 | yes |
| atr_ratio_lookback | 160 | 40 | no |
| atr_ratio_min | 0.3 | 0.0 | no |
| atr_ratio_max | 2.0 | 2.0 | yes |
| wick_body_ratio | 1.5 | 3.0 | no |
| fat_tail_body_lookback | 3 | 13 | no |
| fat_tail_body_mult | 2.5 | 5.0 | no |
| breakeven_retrace_ratio | 2.0 | 2.0 | yes |
| session_start_hour_utc | 0 | 0 | yes |
| session_end_hour_utc | 24 | 24 | yes |

## Reading

- The rolling consensus has higher total and average return.
- The current defaults have materially higher PF, lower drawdown, and a better worst year.
- The rolling consensus creates more trades and pays more commission.
- The current defaults remain the preferred production candidate.
