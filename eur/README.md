# EUR Backtesting Workspace

This directory is a dedicated EURUSD M15 research workspace.
The objective is not to maximize one-year return. The objective is robust multi-year performance, especially out-of-sample (OOS).

## 1. Directory Layout

- `eur/data/historical/`
  - Historical M15 data (`M15_2017.csv` ... `M15_2025.csv`)
- `eur/scripts/backtest/engine_1.py`
  - Core backtest engine
- `eur/scripts/backtest/run_yearly_backtests.py`
  - Year-by-year batch runner with summary outputs
- `eur/scripts/backtest/optimize_base_strategy.py`
  - Grid-search optimizer with train/validation/test scoring
- `eur/data/backtest/runs/`
  - Outputs for fixed-parameter backtest runs
- `eur/data/backtest/optimizations/`
  - Outputs for optimization experiments
- `eur/data/backtest/samples/`
  - Sample/template outputs from single-file runs

## 2. Data Requirements

`engine_1.py` expects the following CSV columns:

- `time`
- `open`
- `high`
- `low`
- `close`
- `tick_volume`
- `spread`

Notes:

- `time` is parsed as UTC, sorted, and deduplicated.
- Invalid numeric values are coerced and dropped.
- `spread` is interpreted in MT-style points (`1 point = 0.00001` for EURUSD).

## 3. Scripts and Usage

### A. Single-file Backtest (`engine_1.py`)

Use this for a direct run on one input file.

```bash
.venv/bin/python eur/scripts/backtest/engine_1.py \
  --input eur/data/historical/M15_2025.csv \
  --output eur/data/backtest/samples/EUR_simple_backtest_report.json
```

Common parameters:

- `--initial-balance`
- `--lot-size`
- `--contract-size`
- `--leverage`
- `--stop-out-level-pct`
- `--slippage-pips`
- `--commission-per-lot-per-side`
- `--confirm-use-rsi`

### B. Yearly Batch Backtest (`run_yearly_backtests.py`)

Use this to evaluate one parameter set across multiple years.

```bash
.venv/bin/python eur/scripts/backtest/run_yearly_backtests.py \
  --run-dir eur/data/backtest/runs/2026-02-21-base
```

Default split:

- Train: `2017-2021`
- Validation: `2022-2023`
- Test: `2024-2025`

Main outputs:

- `reports/EUR_M15_YYYY_report.json`
- `summary/yearly_summary.csv`
- `summary/yearly_summary.json`
- `summary/README.md`
- `config/run_config.json`

### C. Parameter Optimization (`optimize_base_strategy.py`)

Use this to search parameter combinations and rank robustness.

```bash
PYTHONUNBUFFERED=1 .venv/bin/python -u eur/scripts/backtest/optimize_base_strategy.py \
  --run-dir eur/data/backtest/optimizations/2026-02-21-priority0-opt1 \
  --adx-grid 19,21 \
  --rsi-grid 70:30,72:28 \
  --atr-sl-grid 0.8,1.0 \
  --atr-tp-grid 1.8,2.2 \
  --confirm-rsi-grid false,true
```

Main outputs:

- `trials/trials_all.csv`
- `summary/top10.csv`
- `summary/best_params.json`
- `summary/best_yearly_results.csv`
- `config/run_config.json`

## 4. Metric Definitions

- `return_pct`: yearly return in percent
- `max_drawdown_pct`: maximum peak-to-trough equity drawdown
- `profit_factor`: gross profit / gross loss
- `sharpe_per_trade`: average trade return divided by trade-return volatility
- `trades`: number of completed trades
- `oos_consistency`: percentage of positive years in validation + test

## 5. Benchmarks (Quick Quality Guide)

These are practical research thresholds, not guarantees.

### Profit Factor (`profit_factor`)

- `< 1.00`: `Bad` (losing edge)
- `1.00 - 1.15`: `Weak`
- `1.15 - 1.40`: `Acceptable`
- `1.40 - 1.80`: `Good`
- `> 1.80`: `Excellent`

### Sharpe per Trade (`sharpe_per_trade`)

- `< 0.00`: `Bad`
- `0.00 - 0.20`: `Weak`
- `0.20 - 0.50`: `Acceptable`
- `0.50 - 1.00`: `Good`
- `> 1.00`: `Excellent`

### Max Drawdown (`max_drawdown_pct`)

- `> 25%`: `Bad` (risk too high for most systems)
- `15% - 25%`: `Weak`
- `8% - 15%`: `Acceptable`
- `4% - 8%`: `Good`
- `< 4%`: `Excellent`

### OOS Consistency (`oos_consistency`)

- `< 40%`: `Bad`
- `40% - 60%`: `Weak`
- `60% - 75%`: `Acceptable`
- `75% - 90%`: `Good`
- `> 90%`: `Excellent`

### Trade Count (`trades` per year)

- `< 15`: `Too sparse` (low statistical confidence)
- `15 - 30`: `Minimum usable`
- `30 - 80`: `Healthy sample`
- `> 80`: `High frequency` (re-check costs/slippage assumptions)

## 6. How to Compare Two Strategy Versions

1. Run both versions into separate run folders.

Example:

- `eur/data/backtest/runs/2026-02-22-v1`
- `eur/data/backtest/runs/2026-02-22-v2`

2. Compare `summary/yearly_summary.csv` between the two runs.

Focus on validation/test first:

- better `return_pct`
- lower `max_drawdown_pct`
- higher `profit_factor`
- higher `oos_consistency`

Rule of thumb:

- Better train but worse validation/test = likely overfitting.
- Better validation/test with similar or lower drawdown = meaningful improvement.

## 7. Current Research Infrastructure (Priority 0)

Implemented:

- unified metrics (`Net PnL`, `MaxDD`, `Profit Factor`, `Sharpe`, `Trade Count`)
- fixed data split (`Train/Validation/Test`)
- consistent execution costs (`spread/slippage/commission`)
- traceable outputs (`run_config`, parameters, `code_version`)

## 8. Practical Notes

- Prefer `.venv/bin/python` for consistency.
- Do not judge strategy quality from a single year.
- Start optimization with coarse ranges, then refine locally.
- Keep all run folders for reproducibility and auditability.
