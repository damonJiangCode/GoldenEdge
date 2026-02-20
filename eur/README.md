# EUR Workspace

This folder contains only EURUSD-related files extracted from `ai/`.

## Structure
- `eur/scripts/backtest/`: EUR backtest scripts
- `eur/data/historical/`: EURUSD historical data (M15 CSVs)
- `eur/data/backtest_results/`: EUR backtest outputs

## Run
```bash
.venv/bin/python eur/scripts/backtest/EUR_backtesting.py --input eur/data/historical/M15_2025.csv
```
