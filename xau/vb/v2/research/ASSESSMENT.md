# VB V2 Development Assessment

Research boundary: **2015-2023 only**. Years 2024-2026 remain frozen OOS and
were not used by the V2 engine or research scripts.

## Correctness Changes From V1

- Replaced the synthetic H1 ADX made from H4 bars with ADX calculated from the
  matching true H1 file.
- H1 ADX uses the last H1 bar completed by the H4 signal decision time.
- Initial stop ATR comes from the completed H4 signal bar, not the future entry
  bar.
- Stops crossed by an opening gap fill at the worse open price.
- Open positions are liquidated at the end of each annual test with spread,
  slippage, and commission included.
- Position sizing targets 1% initial-equity risk and rounds lots down to the
  broker lot step.
- Trades below the minimum executable lot or above available margin are
  rejected.
- The engine refuses to load 2024 or later.

## Current Candidate

The current candidate keeps the V1 intrabar Donchian breakout and chandelier
exit, then requires:

- H1 ADX >= 18;
- H4 ATR ratio >= 1.10;
- breakout candle close in the strongest 35% of its range for longs, or weakest
  35% for shorts.

The `0.65` close-quality threshold is the center of the tested
`0.60 / 0.65 / 0.70` neighborhood, not the best-performing boundary.

## 2015-2023 Candidate Comparison

| Candidate | Positive years | Median return | Worst return | Worst DD | Trades |
| --- | ---: | ---: | ---: | ---: | ---: |
| Corrected intrabar baseline | 7/9 | 9.19% | -1.19% | 8.68% | 259 |
| Close confirmation + ATR 1.10 | 8/9 | 2.01% | -1.50% | 5.64% | 142 |
| Close quality 0.65 + ATR 1.10 | 9/9 | 1.56% | 0.53% | 5.73% | 142 |

The current candidate sacrifices return for cross-year consistency and lower
drawdown. Its 2020-2023 internal validation years are all positive.

## Parameter Neighborhood

ATR ratio `1.10` is the stable center of the tested neighborhood. All three
close-quality values at that ATR threshold were positive in at least 8/9
years. Raising ATR ratio to `1.15` materially reduced stability, while lowering
it to `1.05` allowed larger losing years.

This supports a broad logic choice around moderate volatility expansion. It
does not justify further precision tuning.

## Cost Stress

Using closed trades only, the current candidate remains positive in 9/9 years
under:

- stress: 10 ticks slippage per side and 10 currency units commission per lot;
- severe: 20 ticks slippage per side and 20 currency units commission per lot.

The candidate has a thin median annual return. It should not be scaled up or
declared production-ready before the frozen OOS protocol is explicitly
approved.

## Risk Budget

The default account is `10000` with a maximum 1% initial-risk budget per trade.
Position size is always rounded down, so realized initial risk is at or below
the budget. Risk-budget neighborhood results are written to
`results/risk_budget_check.csv`; the purpose is to detect minimum-lot and lot
rounding instability, not to select the highest-return leverage.

| Risk budget | Positive years | Median return | Worst return | Worst DD |
| --- | ---: | ---: | ---: | ---: |
| 0.5% | 9/9 | 0.81% | 0.04% | 2.69% |
| 1.0% | 9/9 | 1.56% | 0.53% | 5.73% |
| 1.5% | 9/9 | 3.09% | 0.86% | 8.57% |

The 1% default is the middle risk setting. It was not selected for maximum
return.

## Remaining Limitations

- H4 OHLC data cannot determine intrabar ordering beyond the conservative
  old-stop-first handling.
- Annual tests reset balance and indicator warmup.
- Swap is not modeled.
- The minimum executable lot can cause actual risk to be below the 1% target.
