# TP V1 Parameter-Island Grid Test

> Warning: this is an in-sample research ranking, not a trustworthy out-of-sample
> optimum. Parameters were repeatedly selected using 2015-2024.

Timeframe: `H1`; train: `2015-2024`; untouched holdout: `2025`.

## Winner

- Train score: `24.0741`
- Train average / median / worst return: `14.7041%` / `15.7864%` / `1.8403%`
- Train positive years: `10/10`
- Train average PF / drawdown: `1.3884` / `16.3469%`
- Holdout 2025 return / PF / drawdown: `30.8000%` / `1.1901` / `52.4625%`

```json
{
  "ema_fast_period": 20,
  "ema_slow_period": 60,
  "atr_period": 40,
  "pullback_depth_atr_mult": 0.0,
  "atr_sl_mult": 4.0,
  "tp_rr": 4.0
}
```

## Baseline Comparison

- Baseline train average return / positive years: `-4.1509%` / `4/10`
- Baseline holdout return / PF: `18.0564%` / `1.1270`

## Important Engine Finding

- `adx_period`, `atr_pct_window`, and `slope_th_norm` do not affect entries or exits.
- They only change regime labels, so they were excluded from performance optimization.
- H1 OHLC cannot determine SL/TP ordering inside a bar; the engine conservatively checks SL first.
- The winner's 2025 holdout drawdown is high; treat the parameters as a research winner, not a production risk setting.

See `best_summary.json`, `top_candidates.csv`, `sensitivity_top100.csv`, `top20_holdout_diagnostic.csv`, `execution_cost_stress.csv`, and stage CSVs.
