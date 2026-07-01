"""H2O AutoML adapter — H2O.ai's scalable AutoML.

Requires Java 11+ (the H2O Docker image installs a headless JRE; verify
locally with `java -version`).
"""

from __future__ import annotations


def run(X_train, y_train, X_test, y_test, task_type, time_budget, seed):
    import h2o
    from h2o.automl import H2OAutoML

    h2o.init(nthreads=-1)
    try:
        train = X_train.copy()
        train["target"] = y_train.values
        train_h2o = h2o.H2OFrame(train)
        test_h2o = h2o.H2OFrame(X_test)

        if task_type != "regression":
            train_h2o["target"] = train_h2o["target"].asfactor()

        aml = H2OAutoML(max_runtime_secs=time_budget, seed=seed, verbosity=None)
        aml.train(y="target", training_frame=train_h2o)

        preds = aml.leader.predict(test_h2o).as_data_frame(use_multi_thread=True)
        result = {"y_pred": preds["predict"].values}
        if task_type == "binary":
            # remaining columns are per-class probabilities (sorted by label)
            proba_cols = [c for c in preds.columns if c != "predict"]
            result["y_proba"] = preds[proba_cols].values
        return result
    finally:
        h2o.cluster().shutdown()
