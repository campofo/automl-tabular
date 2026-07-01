"""PyCaret adapter — community low-code AutoML.

Requires the pinned scikit-learn==1.3.2 from the base requirements; newer
scikit-learn releases break this PyCaret version.
"""

from __future__ import annotations


def run(X_train, y_train, X_test, y_test, task_type, time_budget, seed):
    if task_type == "regression":
        from pycaret.regression import compare_models, predict_model, setup
    else:
        from pycaret.classification import compare_models, predict_model, setup

    train = X_train.copy()
    train["target"] = y_train.values

    setup_kwargs = {}
    if task_type != "regression":
        # stratify PyCaret's internal split; otherwise rare classes can be
        # absent from its training fold and predict() hits unseen labels
        setup_kwargs["data_split_stratify"] = True
        setup_kwargs["fold_strategy"] = "stratifiedkfold"
    setup(
        data=train,
        target="target",
        session_id=seed,
        verbose=False,
        html=False,
        n_jobs=-1,
        **setup_kwargs,
    )
    # compare_models takes its budget in minutes.
    best = compare_models(budget_time=time_budget / 60.0, verbose=False)

    if task_type == "binary":
        # raw_score=True adds one prediction_score_<class> column per class.
        preds = predict_model(best, data=X_test, raw_score=True, verbose=False)
        score_cols = sorted(
            c for c in preds.columns if c.startswith("prediction_score_")
        )
        result = {"y_pred": preds["prediction_label"].values}
        if score_cols:
            # column order matches sorted class labels; last = positive class
            result["y_proba"] = preds[score_cols].values
        return result

    preds = predict_model(best, data=X_test, verbose=False)
    return {"y_pred": preds["prediction_label"].values}
