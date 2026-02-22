# Backtest Scripts Map

## Scripts -> Output Folders

- `engine_1.py`
  - Single-file backtest engine
  - Default output: `eur/data/backtest/samples/EUR_simple_backtest_report.json`

- `run_yearly_backtests.py`
  - Yearly batch runner (one report per year + summary)
  - Output root: `eur/data/backtest/runs/<run-name>/`

- `optimize_base_strategy.py`
  - Grid optimization runner (many parameter sets + ranking)
  - Output root: `eur/data/backtest/optimizations/<run-name>/`

## Quick Rule

- If you are validating one fixed parameter set, use `runs/`.
- If you are searching for better parameters, use `optimizations/`.
- If you just need one sample JSON report, use `samples/`.
