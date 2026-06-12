# Regime Baseline: VB + MR Fixed Combination

No Regime filter or strategy selector is applied.

## Allocation

- Single shared account initial balance: `2000`
- Both strategies retain original defaults, costs, positions, and exits.
- Account equity is `2000 + VB equity PnL + MR equity PnL`.
- All current positions consume margin from the same account.

## Executive Summary

- Positive years: `11/11`
- Average / median annual return: `46.03%` / `46.64%`
- Worst / best annual return: `10.41%` / `166.29%`
- Average / worst annual max drawdown: `3.22%` / `6.22%`
- Pooled trades / PF / expectancy: `22421` / `3.534` / `0.444`

## Annual Performance

| Year | Return % | PF | Max DD % | Trades | VB Return % | MR Return % |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2015 | 11.21 | 2.81 | 0.97 | 1861 | 2.72 | 8.50 |
| 2016 | 18.17 | 2.69 | 2.20 | 1957 | 1.73 | 16.44 |
| 2017 | 10.41 | 1.79 | 2.73 | 2124 | 4.42 | 5.98 |
| 2018 | 12.07 | 1.86 | 2.02 | 2306 | 0.59 | 11.47 |
| 2019 | 18.33 | 1.85 | 4.71 | 2124 | 2.40 | 15.93 |
| 2020 | 51.79 | 3.37 | 3.62 | 1804 | 9.82 | 41.96 |
| 2021 | 46.64 | 3.73 | 2.05 | 2149 | 12.40 | 34.24 |
| 2022 | 51.83 | 3.50 | 3.22 | 2179 | 8.59 | 43.23 |
| 2023 | 49.65 | 3.76 | 3.36 | 1857 | 17.55 | 32.10 |
| 2024 | 69.98 | 4.67 | 4.33 | 2006 | 11.64 | 58.35 |
| 2025 | 166.29 | 5.23 | 6.22 | 2054 | 69.67 | 96.62 |

## Strategy Contributions

| Strategy | Trades | Win % | Net PnL | PF | Expectancy |
| --- | ---: | ---: | ---: | ---: | ---: |
| MR | 22140 | 8.04 | 7296.41 | 5.69 | 0.330 |
| VB | 281 | 43.77 | 2649.08 | 2.12 | 9.427 |

## Reading Notes

- No regime filter, selector, conflict handling, or dynamic weight is applied.
- VB and MR trade one shared 2000 account; child engine balances are attribution ledgers only.
- Account equity equals 2000 plus the timestamp-aligned VB and MR equity PnL.
- The single account resets to 2000 at the start of each annual report.
- Return and drawdown use portfolio equity; pooled trade statistics use closed trades only.
- Historical results are research data, not pristine OOS.
