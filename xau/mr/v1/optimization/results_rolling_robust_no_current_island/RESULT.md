# MR V1 Rolling Robust Parameter-Island Test

This is a robustness diagnostic. The historical years were previously observed,
so the OOS labels describe the protocol, not pristine project-level holdouts.
Current optimized parameter island excluded: `True`.

## Method

- Six rolling folds use four training years, one validation year, and the next year as OOS test.
- The coarse candidate pool and parameter islands are fixed once before all folds.
- Every fold uses exactly the same candidates, eligibility rule, and score.
- No candidates are created from validation or OOS results.

## Selection Score

Base score for a set of years:

`median_return + 0.35*average_return + 0.45*worst_return + 0.50*positive_years + 1.50*(capped_average_PF-1) - 0.20*average_drawdown - low_trade_penalty`

Robust fold selection score:

`min(candidate_train, candidate_validation, island_train_median, island_validation_median) + 0.10*mean(the four components)`

Eligibility requires at least `3/4` profitable training years, a profitable
validation year, and at least `100` average trades in both segments.

## OOS Results

- Adaptive rolling OOS average / worst return: `109.4945%` / `71.7021%`
- Adaptive rolling OOS positive years: `6/6`
- Adaptive rolling OOS average PF / drawdown: `4.3974` / `5.6837%`
- Fixed current parameters OOS average / worst return: `102.1661%` / `64.1953%`
- Fixed current parameters OOS positive years: `6/6`

See `fold_summary.csv`, `oos_years.csv`, `fold_candidates.csv`,
`selected_parameter_frequency.csv`, `execution_cost_stress_summary.csv`,
and `best_summary.json`.
