# Notebook Usage Rules

Use notebooks for:

- feature sanity checks
- label distribution checks
- quick model baselines
- plotting/debugging

Avoid putting production logic only in notebooks.

## Naming

Use numeric prefixes:

- `01_data_check.ipynb`
- `02_feature_check.ipynb`
- `03_lr_baseline.ipynb`

## Output policy

- Save datasets to `../data/features` or `../data/processed`.
- Save charts/reports to `../artifacts/reports`.
- Keep notebook outputs lightweight when committing.
