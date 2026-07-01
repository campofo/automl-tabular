"""auto-sklearn adapter — AutoML Freiburg Group's competition winner.

Linux only: run inside Docker (or WSL2 on Windows). Note the auto-sklearn
image downgrades scikit-learn below the base pin; that is expected.
"""

from __future__ import annotations


def _prepare(df):
    """auto-sklearn needs object columns encoded as pandas category dtype."""
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype("category")
    return df


def run(X_train, y_train, X_test, y_test, task_type, time_budget, seed):
    if task_type == "regression":
        from autosklearn.regression import AutoSklearnRegressor as Estimator
    else:
        from autosklearn.classification import AutoSklearnClassifier as Estimator

    X_train = _prepare(X_train)
    X_test = _prepare(X_test)

    est = Estimator(
        time_left_for_this_task=time_budget,
        seed=seed,
        # RAM is capped by the container; don't let auto-sklearn's own
        # per-model limit kill models the tier would actually allow.
        memory_limit=None,
        n_jobs=-1,
    )
    est.fit(X_train, y_train)

    result = {"y_pred": est.predict(X_test)}
    if task_type == "binary":
        result["y_proba"] = est.predict_proba(X_test)
    return result
