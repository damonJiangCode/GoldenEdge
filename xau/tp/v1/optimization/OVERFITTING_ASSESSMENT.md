# TP V1 Overfitting Assessment

## Verdict

The original `2015-2024` parameter-island winner must be treated as an
in-sample research winner. Searching many candidates on the same ten years and
then reporting those ten years creates data-mining bias. One 2025 holdout year
is not enough to validate it.

## Corrected Protocol

- Search and island generation: `2015-2019`
- Selection: `2020-2022`
- Protocol-isolated confirmation: `2023-2024`
- Protocol-isolated final check: `2025`

The corrected protocol selected:

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

It was profitable in every yearly segment, including 2023-2025. However,
2023-2025 had already been viewed during the original experiment, so they are
not pristine holdouts at the overall research-project level.

## Remaining Risk

- Only about `15-31` closed trades occur per year for the corrected candidate.
- The 2025 maximum drawdown is `44.71%`.
- H1 OHLC data cannot reproduce intrabar SL/TP ordering.
- The same XAU history has now been used repeatedly.

The parameters are evidence of a potentially persistent strategy region, not
proof of a production-ready edge. A trustworthy next test requires unseen
future data, tick-level XAU data not used during development, or a predeclared
cross-market validation with no parameter changes.
