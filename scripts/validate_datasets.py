"""Week 2 deliverable: validate all seven cached datasets against the study spec.

Checks per dataset:
- row and feature counts match the documented spec
- task type and target dtype (string classes vs float)
- class balance sanity (fraud must be heavily imbalanced)
- leakage/identifier columns are absent
- the 80/20 split is deterministic at seed 42

Usage:
    python scripts/validate_datasets.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.load_datasets import DATASETS, load_dataset  # noqa: E402

FORBIDDEN_COLUMNS = {
    "titanic": ["PassengerId", "Name", "Ticket"],
    "ames_housing": ["Order", "PID"],
}

# sanity bands for the positive/minority class share
BALANCE_CHECKS = {
    "credit_fraud": ("1", 0.001, 0.003),   # ~0.17% fraud
    "adult": (">50K", 0.20, 0.30),
    "bank_marketing": ("1", 0.08, 0.15),  # this mirror encodes y as 0/1
    "titanic": ("1", 0.30, 0.45),
}


def validate(name: str) -> list[str]:
    cfg = DATASETS[name]
    errors = []
    X_train, X_test, y_train, y_test, task = load_dataset(name)

    rows = len(X_train) + len(X_test)
    feats = X_train.shape[1]
    exp = cfg["expected"]
    if rows != exp["rows"]:
        errors.append(f"rows {rows} != expected {exp['rows']}")
    if feats != exp["features"]:
        errors.append(f"features {feats} != expected {exp['features']}")
    if task != cfg["task_type"]:
        errors.append(f"task {task} != {cfg['task_type']}")

    y_all = pd.concat([y_train, y_test])
    if task == "regression":
        if not pd.api.types.is_float_dtype(y_all):
            errors.append(f"regression target dtype {y_all.dtype} is not float")
    else:
        if y_all.isna().any():
            errors.append("classification target contains NaN")
        n_classes = y_all.nunique()
        if task == "binary" and n_classes != 2:
            errors.append(f"binary target has {n_classes} classes")
        if task == "multiclass" and n_classes < 3:
            errors.append(f"multiclass target has only {n_classes} classes")
        # stratification preserved between splits
        train_share = y_train.value_counts(normalize=True)
        test_share = y_test.value_counts(normalize=True)
        drift = (train_share - test_share).abs().max()
        if drift > 0.02:
            errors.append(f"stratification drift {drift:.3f} > 0.02")

    if name in BALANCE_CHECKS:
        label, lo, hi = BALANCE_CHECKS[name]
        share = float((y_all == label).mean())
        if not lo <= share <= hi:
            errors.append(f"class {label!r} share {share:.4f} outside [{lo}, {hi}]")

    for col in FORBIDDEN_COLUMNS.get(name, []):
        if col in X_train.columns:
            errors.append(f"leakage/identifier column {col!r} present")

    # determinism: a second load must produce the identical split
    X_train2, _, y_train2, _, _ = load_dataset(name)
    if not X_train.index.equals(X_train2.index) or not y_train.equals(y_train2):
        errors.append("split is not deterministic across loads")

    return errors


def main() -> None:
    print(f"{'dataset':<20} {'task':<11} {'rows':>7} {'feat':>5} {'classes':>8}  status")
    print("-" * 68)
    failed = False
    for name in sorted(DATASETS):
        errors = validate(name)
        X_train, X_test, y_train, y_test, task = load_dataset(name)
        rows = len(X_train) + len(X_test)
        classes = (
            str(pd.concat([y_train, y_test]).nunique())
            if task != "regression" else "-"
        )
        status = "OK" if not errors else "FAIL: " + "; ".join(errors)
        print(f"{name:<20} {task:<11} {rows:>7} {X_train.shape[1]:>5} {classes:>8}  {status}")
        failed = failed or bool(errors)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
