"""Fetch, cache, and split the seven benchmark datasets.

Every dataset is fetched programmatically (OpenML or scikit-learn), cached
under ``data/`` as pickles, and split 80/20 with ``random_state=42``
(stratified for classification). AutoML frameworks receive the raw feature
frame — each framework performs its own preprocessing, which is part of what
this benchmark measures.

Usage:
    python -m src.load_datasets --dataset titanic
    python -m src.load_datasets --all
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
from sklearn.datasets import fetch_california_housing, fetch_openml
from sklearn.model_selection import train_test_split

from . import SEED

DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))

# task_type: "binary" | "multiclass" | "regression"
DATASETS = {
    "adult": {
        "task_type": "binary",
        "openml_id": 1590,  # UCI Adult Income, 48,842 rows
        "target": "class",
    },
    "bank_marketing": {
        "task_type": "binary",
        "openml_id": 1461,  # UCI Bank Marketing, 45,211 rows
        "target": "Class",
    },
    "titanic": {
        "task_type": "binary",
        "openml_id": 40945,  # Titanic, 891 labelled rows in common splits
        "target": "survived",
        # free-text identifiers and post-outcome (leakage) columns
        "drop": ["name", "ticket", "cabin", "boat", "body", "home.dest"],
    },
    "credit_fraud": {
        "task_type": "binary",
        "openml_id": 1597,  # Credit Card Fraud, 284,807 rows, heavily imbalanced
        "target": "Class",
    },
    "california_housing": {
        "task_type": "regression",
        "sklearn": "california_housing",  # 20,640 rows
        "target": "MedHouseVal",
    },
    "ames_housing": {
        "task_type": "regression",
        "openml_id": 43926,  # Ames Housing, 2,930 rows, 79 features
        "target": "SalePrice",
    },
    "wine_quality": {
        "task_type": "multiclass",
        "openml_id": 287,  # Wine Quality (red + white), 6,497 rows
        "target": "quality",
    },
}


def _fetch_raw(name: str) -> pd.DataFrame:
    """Download one dataset and return it as a single dataframe (target last)."""
    cfg = DATASETS[name]
    if cfg.get("sklearn") == "california_housing":
        bunch = fetch_california_housing(as_frame=True)
        df = bunch.frame
    else:
        bunch = fetch_openml(data_id=cfg["openml_id"], as_frame=True, parser="auto")
        df = bunch.frame

    # Normalise: locate the target column case-insensitively, rename to 'target'.
    target = cfg["target"]
    if target not in df.columns:
        matches = [c for c in df.columns if c.lower() == target.lower()]
        if not matches:
            raise KeyError(
                f"target column {target!r} not found in {name}; columns: {list(df.columns)}"
            )
        target = matches[0]

    df = df.drop(columns=[c for c in cfg.get("drop", []) if c in df.columns])
    df = df.rename(columns={target: "target"})

    # Classification targets as string categories; regression as float.
    if cfg["task_type"] == "regression":
        df["target"] = df["target"].astype(float)
    else:
        df["target"] = df["target"].astype(str)
        df = df.dropna(subset=["target"])
    return df


def load_dataset(name: str, data_dir: Path = DATA_DIR):
    """Return (X_train, X_test, y_train, y_test, task_type) for one dataset.

    Fetches and caches on first use; later calls read the cache so all 105
    runs see identical splits.
    """
    if name not in DATASETS:
        raise ValueError(f"unknown dataset {name!r}; choose from {sorted(DATASETS)}")
    cfg = DATASETS[name]
    cache = Path(data_dir) / f"{name}.pkl"
    if cache.exists():
        df = pd.read_pickle(cache)
    else:
        df = _fetch_raw(name)
        cache.parent.mkdir(parents=True, exist_ok=True)
        df.to_pickle(cache)

    y = df["target"]
    X = df.drop(columns=["target"])
    stratify = y if cfg["task_type"] != "regression" else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=stratify
    )
    return X_train, X_test, y_train, y_test, cfg["task_type"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and cache benchmark datasets")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dataset", choices=sorted(DATASETS), help="fetch one dataset")
    group.add_argument("--all", action="store_true", help="fetch all seven datasets")
    args = parser.parse_args()

    names = sorted(DATASETS) if args.all else [args.dataset]
    for name in names:
        X_train, X_test, y_train, _, task = load_dataset(name)
        print(
            f"{name}: task={task} train={len(X_train)} test={len(X_test)} "
            f"features={X_train.shape[1]}"
        )


if __name__ == "__main__":
    main()
