# XAUUSD VB/H4 Optimization Summary

- Engine: `volatility_breakout/v1`
- Timeframe: `H4`
- Dev years: `(2015, 2016, 2017, 2018, 2019, 2020, 2021)`
- Validation years: `(2022, 2023)`
- OOS years: `(2024, 2025)`
- Grid size: `1`

## Top Candidates

| Rank | Score | Params | OOS Avg Ret | OOS PF | Full Avg Ret | Full PF | Full DD | Pos Years | Best Year Share |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 259.15 | `N=20, exit=10, SL=2.2, trail=3.0, ADX=18.0, ATRr=1.0` | 69.72% | 2.55 | 22.54% | 2.11 | 9.10% | 11/11 | 0.47 |

## Reading The Score

The score favors OOS and validation strength, PF, positive-year count, and lower drawdown. It penalizes unstable train/OOS gaps, overdependence on one best year, too few trades, and weak OOS PF.

Use the top rows as candidates, not as final truth. A robust candidate should have nearby parameter combinations with similar results.
