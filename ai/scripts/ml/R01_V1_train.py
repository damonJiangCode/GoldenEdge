"""Train baseline models for R01_V1 2017 features/labels."""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)


def find_ai_root(start: Path | None = None) -> Path:
    cwd = (start or Path.cwd()).resolve()
    if cwd.name == "ai":
        return cwd
    if (cwd / "ai").exists():
        return (cwd / "ai").resolve()
    for parent in [cwd, *cwd.parents]:
        if parent.name == "ai":
            return parent
    raise FileNotFoundError("Cannot locate ai folder from current working directory.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train baseline models for R01_V1.")
    parser.add_argument("--features", type=Path, help="Path to features csv.")
    parser.add_argument("--labels", type=Path, help="Path to labels csv.")
    parser.add_argument(
        "--out-dir", type=Path, help="Directory to save models and report."
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.7,
        help="Train split ratio (default: 0.7).",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    return parser.parse_args()


def load_xy(
    features_path: Path, labels_path: Path
) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = pd.read_csv(features_path)
    y = pd.read_csv(labels_path)
    if len(x) != len(y):
        raise ValueError(f"Length mismatch: features={len(x)}, labels={len(y)}")
    return x, y


def preprocess_features(x: pd.DataFrame) -> pd.DataFrame:
    out = x.copy()
    out = pd.get_dummies(out, drop_first=False)
    out = out.replace([np.inf, -np.inf], np.nan)
    out = out.ffill().bfill().fillna(0.0)
    return out


def split_time_aware(
    x: pd.DataFrame, y: pd.DataFrame, train_ratio: float
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    split_idx = int(len(x) * train_ratio)
    x_train = x.iloc[:split_idx].copy()
    x_test = x.iloc[split_idx:].copy()
    y_train = y.iloc[:split_idx].copy()
    y_test = y.iloc[split_idx:].copy()
    return x_train, x_test, y_train, y_test


def train_classifier(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_test: pd.DataFrame,
    y_test: pd.Series,
    seed: int,
) -> tuple[str, object, dict]:
    candidates = {
        "logistic_regression": LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=seed
        ),
        "random_forest_classifier": RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=5,
            n_jobs=-1,
            random_state=seed,
        ),
    }

    best_name = ""
    best_model = None
    best_metrics = {}
    best_score = -1.0

    for name, model in candidates.items():
        model.fit(x_train, y_train)
        pred = model.predict(x_test)
        metrics = {
            "accuracy": float(accuracy_score(y_test, pred)),
            "precision": float(precision_score(y_test, pred, zero_division=0)),
            "recall": float(recall_score(y_test, pred, zero_division=0)),
            "f1": float(f1_score(y_test, pred, zero_division=0)),
        }
        if hasattr(model, "predict_proba") and len(set(y_test.tolist())) > 1:
            proba = model.predict_proba(x_test)[:, 1]
            metrics["roc_auc"] = float(roc_auc_score(y_test, proba))

        score = metrics["f1"]
        if score > best_score:
            best_score = score
            best_name = name
            best_model = model
            best_metrics = metrics

    return best_name, best_model, best_metrics


def train_regressor(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_test: pd.DataFrame,
    y_test: pd.Series,
    seed: int,
) -> tuple[str, object, dict]:
    candidates = {
        "ridge": Ridge(alpha=1.0, random_state=seed),
        "random_forest_regressor": RandomForestRegressor(
            n_estimators=300,
            min_samples_leaf=5,
            n_jobs=-1,
            random_state=seed,
        ),
    }

    best_name = ""
    best_model = None
    best_metrics = {}
    best_score = float("inf")

    for name, model in candidates.items():
        model.fit(x_train, y_train)
        pred = model.predict(x_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
        metrics = {
            "mae": float(mean_absolute_error(y_test, pred)),
            "rmse": rmse,
            "r2": float(r2_score(y_test, pred)),
        }
        score = metrics["mae"]
        if score < best_score:
            best_score = score
            best_name = name
            best_model = model
            best_metrics = metrics

    return best_name, best_model, best_metrics


def save_pickle(obj: object, path: Path) -> None:
    with path.open("wb") as f:
        pickle.dump(obj, f)


def main() -> None:
    args = parse_args()
    root = find_ai_root()

    features_path = (
        args.features or root / "data" / "ml" / "features" / "R01_V1_2017_features.csv"
    )
    labels_path = (
        args.labels or root / "data" / "ml" / "labels" / "R01_V1_2017_labels.csv"
    )
    out_dir = args.out_dir or root / "models" / "R01_V1_2017"
    out_dir.mkdir(parents=True, exist_ok=True)

    x_raw, y = load_xy(features_path, labels_path)
    x = preprocess_features(x_raw)

    x_train, x_test, y_train, y_test = split_time_aware(x, y, args.train_ratio)
    if len(x_train) == 0 or len(x_test) == 0:
        raise ValueError(
            "Train/test split is empty. Check --train-ratio and dataset size."
        )

    clf_name, clf_model, clf_metrics = train_classifier(
        x_train,
        y_train["label_win"],
        x_test,
        y_test["label_win"],
        seed=args.seed,
    )
    reg_name, reg_model, reg_metrics = train_regressor(
        x_train,
        y_train["label_net_pnl"],
        x_test,
        y_test["label_net_pnl"],
        seed=args.seed,
    )

    save_pickle(
        {
            "model": clf_model,
            "feature_columns": x.columns.tolist(),
            "target": "label_win",
        },
        out_dir / "classifier.pkl",
    )
    save_pickle(
        {
            "model": reg_model,
            "feature_columns": x.columns.tolist(),
            "target": "label_net_pnl",
        },
        out_dir / "regressor.pkl",
    )

    report = {
        "dataset": {
            "features_path": str(features_path),
            "labels_path": str(labels_path),
            "rows": int(len(x)),
            "train_rows": int(len(x_train)),
            "test_rows": int(len(x_test)),
        },
        "classifier": {
            "selected_model": clf_name,
            "metrics": clf_metrics,
        },
        "regressor": {
            "selected_model": reg_name,
            "metrics": reg_metrics,
        },
        "artifacts": {
            "classifier": str(out_dir / "classifier.pkl"),
            "regressor": str(out_dir / "regressor.pkl"),
        },
    }
    (out_dir / "metrics.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    print("Training complete.")
    print(f"Classifier: {clf_name} -> {clf_metrics}")
    print(f"Regressor : {reg_name} -> {reg_metrics}")
    print(f"Saved artifacts in: {out_dir}")


if __name__ == "__main__":
    main()
