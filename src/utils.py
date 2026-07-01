"""Shared utilities: metric computation, resource profiling, results logging."""

from __future__ import annotations

import csv
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import psutil
from sklearn.metrics import f1_score, mean_squared_error, roc_auc_score

RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", "results"))
LOG_PATH = RESULTS_DIR / "logs.csv"
LOG_COLUMNS = [
    "framework",
    "dataset",
    "tier",
    "f1",
    "auc",
    "rmse",
    "time_sec",
    "peak_ram_mb",
    "cpu_pct",
    "status",
]


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(task_type, y_true, y_pred, y_proba=None):
    """Return the metric dict for one run.

    Classification -> weighted F1 (primary) and, for binary tasks with
    probabilities available, AUC-ROC (secondary). Regression -> RMSE.
    Metrics that do not apply to the task are left as None and logged empty.
    """
    metrics = {"f1": None, "auc": None, "rmse": None}
    if task_type == "regression":
        metrics["rmse"] = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        return metrics

    metrics["f1"] = float(f1_score(y_true, y_pred, average="weighted"))
    if task_type == "binary" and y_proba is not None:
        proba = np.asarray(y_proba)
        if proba.ndim == 2:  # (n, 2) probability matrix -> positive class col
            proba = proba[:, -1]
        metrics["auc"] = float(roc_auc_score(y_true, proba))
    return metrics


# ---------------------------------------------------------------------------
# Resource profiling
# ---------------------------------------------------------------------------

@dataclass
class ResourceProfiler:
    """Samples process-tree RAM and CPU in a background thread.

    Peak RAM is the max RSS (MB) over the run summed across the process and
    its children (frameworks such as H2O and auto-sklearn spawn workers).
    CPU is the average utilisation percentage across the training duration.
    """

    interval: float = 0.5
    peak_ram_mb: float = 0.0
    cpu_samples: list = field(default_factory=list)
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = None

    def _sample(self):
        proc = psutil.Process()
        proc.cpu_percent(None)  # prime the counter
        while not self._stop.is_set():
            try:
                procs = [proc] + proc.children(recursive=True)
                rss = 0
                cpu = 0.0
                for p in procs:
                    try:
                        rss += p.memory_info().rss
                        cpu += p.cpu_percent(None)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                self.peak_ram_mb = max(self.peak_ram_mb, rss / 1024 / 1024)
                self.cpu_samples.append(cpu)
            except psutil.Error:
                pass
            self._stop.wait(self.interval)

    def __enter__(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        return False

    @property
    def avg_cpu_pct(self) -> float:
        return float(np.mean(self.cpu_samples)) if self.cpu_samples else 0.0


class Timer:
    """Wall-clock timer usable as a context manager."""

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.elapsed = time.perf_counter() - self.start
        return False


# ---------------------------------------------------------------------------
# Results logging
# ---------------------------------------------------------------------------

def append_log_row(row: dict, log_path: Path = LOG_PATH) -> None:
    """Append one experiment row to results/logs.csv, creating it if needed."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not log_path.exists() or log_path.stat().st_size == 0
    with open(log_path, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=LOG_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(
            {
                col: ("" if row.get(col) is None else _fmt(col, row.get(col)))
                for col in LOG_COLUMNS
            }
        )


def _fmt(col, value):
    if col in ("f1", "auc", "rmse") and isinstance(value, float):
        return f"{value:.4f}"
    if col in ("time_sec", "peak_ram_mb", "cpu_pct") and isinstance(value, float):
        return f"{value:.1f}"
    return value
