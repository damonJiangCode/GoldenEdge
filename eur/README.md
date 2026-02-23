# EUR Backtesting Workspace

This directory is a EURUSD M15 backtesting workspace.  
The objective is multi-year robustness, not a high return in a single year.

## 1. Current Structure (Actual Files)

- `eur/data/historical/`
  - Historical data (currently `M15_2017.csv` to `M15_2025.csv`)
- `eur/data/engines/engine_1/`
  - Default results folder for `engine_1.py`
- `eur/scripts/engines/engine_1.py`
  - Mean-reversion engine (v1)
- `eur/scripts/engines/ema_pullback_trend_v1.py`
  - Trend pullback engine (EMA50/EMA200 + ADX filter)
- `eur/scripts/optimizations/`
  - Folder for optimization-related scripts
- `eur/ROADMAP.md`
  - Research and optimization roadmap

## 2. Data Requirements

The CSV input for `engine_1.py` must include:

- `time`
- `open`
- `high`
- `low`
- `close`
- `tick_volume`
- `spread`

Processing rules:

- `time` is parsed as UTC, sorted, and deduplicated.
- Numeric columns are converted with `to_numeric(errors="coerce")`; invalid values are dropped.
- `spread` uses MT-style points (EURUSD: `1 point = 0.00001`).

## 3. How to Run

### A. Run with a Specific Input File

```bash
.venv/bin/python eur/scripts/engines/engine_1.py \
  --input eur/data/historical/M15_2025.csv \
  --output eur/data/engines/engine_1/report_2025.json
```

### B. Run Without `--input`

The script will automatically use the first CSV (sorted by filename) under `eur/data/historical/`.

### C. Common Parameters

- `--initial-balance`
- `--lot-size`
- `--contract-size`
- `--leverage`
- `--stop-out-level-pct`
- `--slippage-pips`
- `--commission-per-lot-per-side`
- `--confirm-use-rsi`

Example:

```bash
.venv/bin/python eur/scripts/engines/engine_1.py \
  --input eur/data/historical/M15_2024.csv \
  --initial-balance 1000 \
  --lot-size 0.005 \
  --leverage 100 \
  --confirm-use-rsi
```

## 4. Output

Default output file:

- `eur/data/engines/engine_1/report_YEAR.json` (`YEAR` inferred from input filename)

Main JSON fields:

- `performance`: `net_pnl` / `return_pct` / `profit_factor` / `sharpe_per_trade` / `max_drawdown_pct`
- `risk`: `stop_out_level_pct` / `stop_out_count`
- `costs`: `slippage_pips` / `commission_per_lot_per_side` / `spread_mean_points`
- `equity_series`: per-bar `balance/equity/margin` path
- `sample_trades`: first 30 trade samples

## 5. Strategy Logic (Current `engine_1` Implementation)

- Indicators: `ADX + Bollinger Bands + RSI + ATR`
- Entry: `ADX` below threshold, price touches outer Bollinger band, `RSI` reaches overbought/oversold
- Confirmation: next bar must confirm reversion (optional extra RSI confirmation)
- Risk: `ATR`-based `SL/TP`, plus margin stop-out handling
- Costs: unified `spread + slippage + commission`
- Exit: `SL/TP`, reverse signal, Friday force close, and last-bar close

## 6. Roadmap (Unchanged)

Roadmap follows `eur/ROADMAP.md`. Priority order remains unchanged:

1. Priority 0: Research Infrastructure
2. Priority 1: Indicator Threshold Optimization
3. Priority 2: Exit Logic Optimization
4. Priority 3: Execution Logic Optimization
5. Priority 4: Position Sizing Optimization

## 7. Notes

- Backtest engines in this repo:
  - `engine_1.py`
  - `ema_pullback_trend_v1.py`
- This README only describes existing implementation and does not reference missing scripts.
