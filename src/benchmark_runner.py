"""Run one benchmark experiment and append the result to results/logs.csv.

One invocation = one (framework, dataset, tier) cell of the 5 × 3 × 7 design.
Runs are fully independent; orchestration across the 105 runs lives in
run_all.sh, which launches each invocation in its own Docker container.

Usage:
    python -m src.benchmark_runner --framework flaml --dataset titanic --tier constrained
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import traceback

import numpy as np

from .frameworks import FRAMEWORKS, get_runner
from .load_datasets import DATASETS, load_dataset
from .utils import ResourceProfiler, Timer, append_log_row, compute_metrics

from . import SEED

TIER_BUDGETS = {"constrained": 300, "moderate": 900, "unconstrained": 3600}

# Hard wall for a hung framework: budget + grace, after which the run is
# recorded as a timeout instead of blocking the whole campaign.
GRACE_FACTOR = 1.25
GRACE_MIN_SEC = 120


class RunTimeout(Exception):
    pass


def _alarm_handler(signum, frame):
    raise RunTimeout


def run_experiment(framework: str, dataset: str, tier: str, time_budget: int) -> dict:
    """Execute one run and return the logs.csv row (always returns a row)."""
    row = {
        "framework": framework,
        "dataset": dataset,
        "tier": tier,
        "f1": None,
        "auc": None,
        "rmse": None,
        "time_sec": None,
        "peak_ram_mb": None,
        "cpu_pct": None,
        "status": None,
    }

    try:
        X_train, X_test, y_train, y_test, task_type = load_dataset(dataset)
    except Exception as exc:  # dataset fetch/cache problems
        row["status"] = f"failed: dataset load: {exc}"
        return row

    runner = get_runner(framework)
    hard_limit = int(time_budget * GRACE_FACTOR) + GRACE_MIN_SEC
    signal.signal(signal.SIGALRM, _alarm_handler)
    signal.alarm(hard_limit)

    profiler = ResourceProfiler()
    timer = Timer()
    try:
        with profiler, timer:
            output = runner(
                X_train, y_train, X_test, y_test, task_type, time_budget, SEED
            )
        signal.alarm(0)

        y_pred = np.asarray(output["y_pred"])
        y_true = y_test.to_numpy()
        if task_type != "regression":
            # frameworks may return labels as int/bool/str — compare as str
            y_pred = y_pred.astype(str)
            y_true = y_true.astype(str)
        row.update(compute_metrics(task_type, y_true, y_pred, output.get("y_proba")))
        row["status"] = "completed"
    except RunTimeout:
        row["status"] = "timeout"
    except Exception as exc:
        traceback.print_exc()
        # keep the message single-line and comma-free for clean CSV rows
        msg = str(exc).replace("\n", " ").replace(",", ";")[:200]
        row["status"] = f"failed: {type(exc).__name__}: {msg}"
    finally:
        signal.alarm(0)
        # Timer/profiler exit even when the run raises, so partial resource
        # usage is still logged for timeout/failure rows.
        row["time_sec"] = getattr(timer, "elapsed", None)
        row["peak_ram_mb"] = profiler.peak_ram_mb
        row["cpu_pct"] = profiler.avg_cpu_pct
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one AutoML benchmark experiment")
    parser.add_argument("--framework", required=True, choices=FRAMEWORKS)
    parser.add_argument("--dataset", required=True, choices=sorted(DATASETS))
    parser.add_argument("--tier", required=True, choices=sorted(TIER_BUDGETS))
    parser.add_argument(
        "--time-budget",
        type=int,
        default=None,
        help="seconds; defaults to $TIME_BUDGET or the tier's standard budget",
    )
    args = parser.parse_args()

    time_budget = (
        args.time_budget
        or int(os.environ.get("TIME_BUDGET", 0))
        or TIER_BUDGETS[args.tier]
    )

    print(
        f"[benchmark] framework={args.framework} dataset={args.dataset} "
        f"tier={args.tier} time_budget={time_budget}s seed={SEED}"
    )
    row = run_experiment(args.framework, args.dataset, args.tier, time_budget)
    append_log_row(row)
    print(f"[benchmark] status={row['status']} -> results/logs.csv")

    if row["status"] != "completed":
        sys.exit(1)


if __name__ == "__main__":
    main()
