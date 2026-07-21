"""AutoGluon adapter — Amazon's ensemble-stacking AutoML.

Must run in its own image/venv: AutoGluon conflicts with the other
frameworks when co-installed.
"""

from __future__ import annotations

import random
import tempfile


def run(X_train, y_train, X_test, y_test, task_type, time_budget, seed):
    import numpy as np
    from autogluon.tabular import TabularPredictor

    # TabularPredictor.fit() in autogluon 1.1.x has no seed argument;
    # determinism comes from the global RNGs it samples at fit time.
    random.seed(seed)
    np.random.seed(seed)

    train = X_train.copy()
    train["target"] = y_train.values

    problem_type = {
        "binary": "binary",
        "multiclass": "multiclass",
        "regression": "regression",
    }[task_type]

    with tempfile.TemporaryDirectory(prefix="autogluon_") as model_dir:
        predictor = TabularPredictor(
            label="target",
            problem_type=problem_type,
            path=model_dir,
            verbosity=0,
        )
        predictor.fit(
            train,
            time_limit=time_budget,
            presets="medium_quality",
            random_seed=seed,
        )

        result = {"y_pred": predictor.predict(X_test).values}
        if task_type == "binary":
            result["y_proba"] = predictor.predict_proba(X_test).values
    return result
