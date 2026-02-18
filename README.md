# GoldenEdge

GoldenEdge is your XAUUSD strategy workspace with two main parts:

- `AlgoAlchemy/`: research, backtest, feature engineering, and ML training.
- `mt5/`: MT5 live/demo strategy files and records.

## Workspace Structure

```text
GoldenEdge_win/
├── AlgoAlchemy/
│   ├── data/
│   │   ├── historical/           # Raw OHLCV csv input
│   │   ├── backtest_results/     # Backtest trade history outputs
│   │   └── ml/
│   │       ├── features/         # ML feature tables
│   │       └── labels/           # ML label tables
│   ├── models/
│   │   └── R01_V1_2017/          # Trained artifacts + reports
│   └── scripts/
│       ├── ingest/               # Data ingestion scripts
│       ├── backtest/             # Backtest scripts
│       └── ml/                   # Train/eval scripts
├── mt5/
│   ├── 2025/
│   ├── 2026/
│   └── records/
├── utlib/
│   ├── requirements.txt
│   └── ta_lib-*.whl
└── run.ps1
```

## AlgoAlchemy Scripts (Current)

### Ingest

- `AlgoAlchemy/scripts/ingest/hist_data_getter.py`

### Backtest

- `AlgoAlchemy/scripts/backtest/R01_V1_backtest.py`
- `AlgoAlchemy/scripts/backtest/R01_V1_backtest_ml_filter.py`
- `AlgoAlchemy/scripts/backtest/T02_V1_backtest.py`

### ML

- `AlgoAlchemy/scripts/ml/R01_V1_train.py`
- `AlgoAlchemy/scripts/ml/R01_V1_threshold_eval.py`
- `AlgoAlchemy/scripts/ml/R01_V1_2017_feature_engineering.py`

## Standard Pipeline (R01_V1)

1. Run base backtest to generate trade-level dataset.
2. Build features + labels from backtest output.
3. Train classifier/regressor.
4. Evaluate probability thresholds.
5. Run ML-filtered backtest and compare with base backtest.

## PowerShell Quick Commands

From project root:

```powershell
cd C:\Users\damon\Documents\GoldenEdge_win
.\.venv\Scripts\python.exe -m pip install -r .\utlib\requirements.txt
```

Run R01 base backtest:

```powershell
.\.venv\Scripts\python.exe .\AlgoAlchemy\scripts\backtest\R01_V1_backtest.py
```

Build ML features/labels:

```powershell
.\.venv\Scripts\python.exe .\AlgoAlchemy\scripts\ml\R01_V1_2017_feature_engineering.py
```

Train ML:

```powershell
.\.venv\Scripts\python.exe .\AlgoAlchemy\scripts\ml\R01_V1_train.py
```

Evaluate thresholds:

```powershell
.\.venv\Scripts\python.exe .\AlgoAlchemy\scripts\ml\R01_V1_threshold_eval.py
```

Run ML-filtered backtest (example threshold):

```powershell
.\.venv\Scripts\python.exe .\AlgoAlchemy\scripts\backtest\R01_V1_backtest_ml_filter.py --threshold 0.55
```

## Key Output Files

- Base backtest: `AlgoAlchemy/data/backtest_results/R01_V1_2017.csv`
- ML-filtered backtest: `AlgoAlchemy/data/backtest_results/R01_V1_2017_ml_filtered.csv`
- Features: `AlgoAlchemy/data/ml/features/R01_V1_2017_features.csv`
- Labels: `AlgoAlchemy/data/ml/labels/R01_V1_2017_labels.csv`
- Trained models: `AlgoAlchemy/models/R01_V1_2017/classifier.pkl`, `regressor.pkl`
- Training report: `AlgoAlchemy/models/R01_V1_2017/metrics.json`
- Threshold report: `AlgoAlchemy/models/R01_V1_2017/threshold_report.csv`

## Notes

- Old flat script entry files under `AlgoAlchemy/scripts/*.py` were removed on purpose.
- Keep new scripts under the correct category folder (`ingest`, `backtest`, `ml`).
- `._*` files are macOS metadata files; they are ignored by `.gitignore`.
