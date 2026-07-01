"""Framework adapter registry.

Each adapter module exposes::

    run(X_train, y_train, X_test, y_test, task_type, time_budget, seed) -> dict

returning at least ``{"y_pred": array}`` and, for classification,
optionally ``{"y_proba": array}`` used for AUC-ROC.

Imports are lazy: each Docker image only has one framework installed, so the
registry must not import the other four at module load time.
"""

from importlib import import_module

FRAMEWORKS = ["autogluon", "pycaret", "flaml", "autosklearn", "h2o"]


def get_runner(name: str):
    """Return the ``run`` callable for one framework, importing it lazily."""
    if name not in FRAMEWORKS:
        raise ValueError(f"unknown framework {name!r}; choose from {FRAMEWORKS}")
    module = import_module(f"src.frameworks.run_{name}")
    return module.run
