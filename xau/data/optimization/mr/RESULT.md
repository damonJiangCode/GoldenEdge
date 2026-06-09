# MR V1 Param Island Result

Timeframe: `M15`; train: `2015-2024`; holdout: `2025`.

## Winner

- Train score: `80.0773`
- Train avg return: `53.6417%`
- Train positive years: `10/10`
- Train worst year return: `11.9699%`
- Holdout 2025 return: `193.2405%`
- Holdout 2025 PF: `6.4027`

```json
{
  "ema_period": 36,
  "atr_period": 7,
  "band_atr_mult": 2.25,
  "sl_atr_mult": 8.0,
  "adx_period": 28,
  "h1_adx_limit": 28.0,
  "atr_ratio_lookback": 160,
  "atr_ratio_min": 0.3,
  "atr_ratio_max": 2.0,
  "wick_body_ratio": 1.5,
  "fat_tail_body_lookback": 3,
  "fat_tail_body_mult": 2.5,
  "breakeven_retrace_ratio": 2.0,
  "session_start_hour_utc": 0,
  "session_end_hour_utc": 24
}
```

## Baseline Comparison

- Baseline train avg return: `-2.8259%`
- Baseline train positive years: `2/10`
- Baseline holdout return: `-2.4724%`

## Island And Risk Notes

- The leading island is concentrated around `EMA 36`, `ATR 7`, `band 2.25`, `SL 8-10 ATR`, `ADX 28`, and full-day entry.
- The winner uses a wide initial stop and a low win-rate / many-small-loss payoff shape.
- M15 OHLC cannot reproduce tick-level fill ordering. Validate the winner on tick data and harsher execution costs before production use.

See `top_candidates.csv`, `best_summary.json`, and unified trade CSV files for details.
