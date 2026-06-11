# MR V1 Rolling Robust Parameter-Island Assessment

## Verdict

The rolling test found a stable alternative parameter island, but it did not
provide sufficient evidence to replace the current MR v1 defaults.

The alternative produced higher protocol-OOS return, but the current defaults
had higher profit factor, lower drawdown, a better worst year, and better
execution-cost robustness. No engine defaults were changed.

All historical years have been observed in earlier MR research. The OOS labels
below describe the rolling protocol, not pristine project-level holdouts.

## Test Protocol

Six fixed-length rolling folds were used:

| Fold | Train | Validation | OOS Test |
| ---: | --- | ---: | ---: |
| 1 | 2015-2018 | 2019 | 2020 |
| 2 | 2016-2019 | 2020 | 2021 |
| 3 | 2017-2020 | 2021 | 2022 |
| 4 | 2018-2021 | 2022 | 2023 |
| 5 | 2019-2022 | 2023 | 2024 |
| 6 | 2020-2023 | 2024 | 2025 |

For every fold:

1. Candidate performance was calculated on the four training years.
2. The same candidates were evaluated on the next validation year.
3. One eligible candidate was selected using the fixed robust score.
4. The selected parameters were locked and run once on the following OOS year.

No candidates, parameter ranges, eligibility rules, or scores were changed
between folds.

## Fixed Parameter Islands

The candidate pool was created once before evaluating any fold:

- Fixed random seed: `20260611`
- Coarse discrete parameter values
- Ten island centers
- One-axis immediate neighbors around each center
- `226` total candidates

The first island contained the current MR defaults, which were previously
optimized using historical data. A second full run excluded that entire island:

- Current-default island excluded
- Nine remaining islands
- `200` total candidates

This leave-current-island-out run is the more useful robustness diagnostic.

## Scoring

The base score for a candidate over a set of years was:

```text
median_return
+ 0.35 * average_return
+ 0.45 * worst_return
+ 0.50 * positive_years
+ 1.50 * (capped_average_profit_factor - 1)
- 0.20 * average_max_drawdown
- low_trade_penalty
```

Profit factor was capped at `3.0` inside the score so unusually high PF values
could not dominate selection.

Eligibility required:

- At least `3/4` profitable training years
- A profitable validation year
- At least `100` average trades in both training and validation

The robust fold-selection score was:

```text
min(
  candidate_train_score,
  candidate_validation_score,
  island_train_median_score,
  island_validation_median_score
)
+ 0.10 * mean(the same four scores)
```

The weakest candidate/island segment therefore dominates selection. A single
high-performing parameter cannot win if its immediate neighborhood is weak.

## Rolling OOS Results

| Variant | Avg Return | Worst Return | Positive Years | Avg PF | Avg Max DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Adaptive, includes current island | `128.92%` | `75.04%` | `6/6` | `7.83` | `2.63%` |
| Adaptive, current island excluded | `109.49%` | `71.70%` | `6/6` | `4.40` | `5.68%` |
| Fixed current MR defaults | `102.17%` | `64.20%` | `6/6` | `8.19` | `2.51%` |

The include-current-island run selected the current-default neighborhood in all
six folds. This result is contaminated by the earlier optimization and should
not be treated as independent evidence.

The leave-current-island-out run selected exactly the same alternative
parameters in all six folds:

```json
{
  "ema_period": 50,
  "atr_period": 7,
  "band_atr_mult": 2.25,
  "sl_atr_mult": 10.0,
  "adx_period": 28,
  "h1_adx_limit": 28.0,
  "atr_ratio_lookback": 40,
  "atr_ratio_min": 0.0,
  "atr_ratio_max": 2.0,
  "wick_body_ratio": 3.0,
  "fat_tail_body_lookback": 13,
  "fat_tail_body_mult": 5.0,
  "breakeven_retrace_ratio": 2.0,
  "session_start_hour_utc": 0,
  "session_end_hour_utc": 24
}
```

This repeated selection is evidence that a second stable parameter region
exists. It is not evidence that the alternative is better for production.

## Execution-Cost Stress

The consensus alternative and current defaults were run across `2015-2025`.
Both slippage and commission were multiplied together.

| Variant | Cost | Avg Return | Worst Return | Positive Years | Avg PF | Avg Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Alternative consensus | `1x` | `69.53%` | `4.87%` | `11/11` | `3.42` | `4.46%` |
| Alternative consensus | `2x` | `54.88%` | `-11.71%` | `10/11` | `2.20` | `6.05%` |
| Alternative consensus | `3x` | `40.02%` | `-27.24%` | `7/11` | `1.62` | `9.68%` |
| Alternative consensus | `5x` | `10.33%` | `-58.08%` | `6/11` | `1.06` | `23.01%` |
| Current defaults | `1x` | `66.33%` | `11.97%` | `11/11` | `5.75` | `2.04%` |
| Current defaults | `2x` | `53.52%` | `-1.88%` | `10/11` | `3.03` | `2.77%` |
| Current defaults | `3x` | `40.50%` | `-15.72%` | `8/11` | `2.05` | `5.42%` |
| Current defaults | `5x` | `14.95%` | `-43.12%` | `6/11` | `1.22` | `15.64%` |

The strategy family is materially sensitive to execution costs. The current
defaults are more robust than the alternative under every stressed-cost level.

## Decision

- Keep the current MR v1 default parameters.
- Do not replace them with the rolling alternative.
- Treat the alternative as evidence of a second stable island only.
- Require tick-level execution testing and realistic broker costs before any
  production decision.

Additional limitations:

- Historical years were previously observed.
- M15 OHLC cannot reproduce tick-level fill ordering.
- Swap is configured as zero.
- Fixed lot sizing means absolute XAU volatility changes affect yearly returns.

