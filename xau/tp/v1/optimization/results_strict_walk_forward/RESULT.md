# TP V1 Strict Walk-Forward Result

No parameter changes are allowed after validation selection inside this run.

> Research caveat: 2023-2025 had already been observed in an earlier experiment.
> They are isolated from this run's selection code, but are no longer pristine holdouts.

## Fixed Time Split

- Development/search: `2015-2019`
- Validation/selection: `2020-2022`
- Untouched confirmation: `2023-2024`
- Untouched final holdout: `2025`

## Selected Parameters

```json
{
  "ema_fast_period": 20,
  "ema_slow_period": 120,
  "atr_period": 14,
  "pullback_depth_atr_mult": 0.75,
  "atr_sl_mult": 4.0,
  "tp_rr": 5.0
}
```

## Segment Results

- Development average / worst / positive years: `11.6430%` / `1.7770%` / `5/5`
- Validation average / worst / positive years: `13.7293%` / `1.1320%` / `3/3`
- Confirmation average / worst / positive years: `16.2135%` / `10.2327%` / `2/2`
- Final 2025 return / PF / drawdown: `78.4060%` / `1.8826` / `44.7124%`

## Interpretation

- This run did not use 2023-2025 to generate, filter, rank, or change parameters.
- Because those years were previously observed, passing this test reduces selection bias but is not a clean out-of-sample proof.
- `adx_period`, `atr_pct_window`, and `slope_th_norm` remain excluded because they do not affect trades.
