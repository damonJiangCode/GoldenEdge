# Robust Regime Optimization Baseline

The original fixed-lot baseline is reproducible, but its cross-year risk exposure is not stable.
This report scales positions down so each strategy trade risks at most 1% of its 1000 sleeve.

## Exposure Audit

- Trades: `22421`
- Trades scaled down: `15837` (`70.63%`)
- Median / minimum size scale: `0.729` / `0.050`
- Original top-10 winner share of all net PnL: `15.76%`

## Executable Capital View

- Keep the original fixed `0.01 lot`; use `10000` capital per strategy sleeve.
- Maximum observed initial risk: `2.00%` of one sleeve.
- Positive years: `11/11`
- Average / median annual return: `4.52%` / `4.66%`
- Worst / best annual return: `1.04%` / `16.12%`

## Scenario Summary

| Scenario | Positive years | Avg return % | Median return % | Worst return % | Best return % | Worst closed-trade DD % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| base | 11/11 | 19.50 | 20.63 | 7.78 | 31.19 | 2.07 |
| stress | 6/11 | 3.08 | 9.45 | -14.34 | 24.40 | 14.47 |
| severe | 2/11 | -18.35 | -12.96 | -46.50 | 15.54 | 46.56 |

## Optimization Gate

- Baseline robust score: `-25.837`
- Require at least `8/11` positive stress years and `6/11` positive severe years.
- Candidate robust score must beat this baseline.
- Candidate stress worst drawdown must not exceed this baseline.
- 2025 is reported, but must not be used for parameter or Regime-rule selection.

## Important Limitation

Risk-normalized fractional lots are an analytical optimization score and may not be executable when the broker minimum lot is 0.01. The executable capital view is the primary money-return reference.

Drawdown in this report is calculated at closed-trade events and excludes intratrade MTM. Final Regime candidates must be rerun through a portfolio engine with full equity curves.
