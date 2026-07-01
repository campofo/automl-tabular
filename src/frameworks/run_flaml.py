"""FLAML adapter — Microsoft's cost-frugal AutoML.

Lightest install of the five; use it as the first pipeline smoke test.
"""

from __future__ import annotations


def _as_category(df):
    """FLAML expects object columns as pandas category dtype."""
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype("category")
    return df


def run(X_train, y_train, X_test, y_test, task_type, time_budget, seed):
    from flaml import AutoML

    automl = AutoML()
    task = "regression" if task_type == "regression" else "classification"
    X_train = _as_category(X_train)
    X_test = _as_category(X_test)

    automl.fit(
        X_train=X_train,
        y_train=y_train,
        task=task,
        time_budget=time_budget,
        seed=seed,
        verbose=0,
    )

    result = {"y_pred": automl.predict(X_test)}
    if task_type == "binary":
        result["y_proba"] = automl.predict_proba(X_test)
    return result
