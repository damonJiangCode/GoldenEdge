# AlgoAlchemy ML Workspace

This folder uses an ML-first layout.

## Folder layout

- `data/raw/`
  - Canonical source market data for ML.
- `data/interim/`
  - Cleaned/aligned data before feature generation.
- `data/features/`
  - Model-ready feature tables.
- `data/processed/`
  - Final train/valid/test datasets.
- `src/ingest/`
  - Data loading/downloading logic.
- `src/features/`
  - Feature engineering code.
- `src/models/`
  - Training and inference code.
- `src/evaluation/`
  - Backtest-like model evaluation and metrics.
  - Backtest scripts now live under `src/evaluation/backtests/`.
- `src/utils/`
  - Shared helpers.
- `pipelines/`
  - End-to-end run scripts (data -> features -> train -> eval).
- `notebooks/`
  - Exploration and experiments.
- `configs/`
  - Config files for datasets/models/experiments.
- `artifacts/models/`
  - Saved trained models.
- `artifacts/reports/`
  - Metrics, plots, experiment summaries.

## Data/Backtest locations

- Raw market CSVs: `data/raw/market/XAUUSD/M5/`
- Data getter: `src/ingest/xauusd_data_getter.py`
- Backtest scripts: `src/evaluation/backtests/`
- Backtest outputs: `artifacts/reports/backtests/`

## Jupyter recommendation

Use notebooks for exploration and diagnostics, but keep reusable logic in `src/`.
Notebook cells should call functions from `src/` instead of duplicating core logic.
