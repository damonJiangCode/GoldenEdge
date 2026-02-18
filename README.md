# GoldenEdge

GoldenEdge is your XAUUSD strategy workspace with two main parts:

- `ai/`: research, backtest, feature engineering, and ML training.
- `mt5/`: MT5 live/demo strategy files and records.

## Workspace Structure

```text
GoldenEdge/
├── ai/
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
└── utlib/
   ├── requirements.txt
   └── ta_lib-*.whl
```

## ai Scripts (Current)

### Ingest

- `ai/scripts/ingest/hist_data_getter.py`

### Backtest

- `ai/scripts/backtest/R01_V1_backtest.py`
- `ai/scripts/backtest/R01_V1_backtest_ml_filter.py`
- `ai/scripts/backtest/T02_V1_backtest.py`

### ML

- `ai/scripts/ml/R01_V1_train.py`
- `ai/scripts/ml/R01_V1_threshold_eval.py`
- `ai/scripts/ml/R01_V1_2017_feature_engineering.py`

## Standard Pipeline (R01_V1)

1. Run base backtest to generate trade-level dataset.
2. Build features + labels from backtest output.
3. Train classifier/regressor.
4. Evaluate probability thresholds.
5. Run ML-filtered backtest and compare with base backtest.

## Key Output Files

- Base backtest: `ai/data/backtest_results/R01_V1_2017.csv`
- ML-filtered backtest: `ai/data/backtest_results/R01_V1_2017_ml_filtered.csv`
- Features: `ai/data/ml/features/R01_V1_2017_features.csv`
- Labels: `ai/data/ml/labels/R01_V1_2017_labels.csv`
- Trained models: `ai/models/R01_V1_2017/classifier.pkl`, `regressor.pkl`
- Training report: `ai/models/R01_V1_2017/metrics.json`
- Threshold report: `ai/models/R01_V1_2017/threshold_report.csv`
