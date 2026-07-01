"""Fetch, cache, and split the seven benchmark datasets.

Every dataset is downloaded from a verified public mirror of the original
source (the canonical hosts — UCI, OpenML, Kaggle — are unreachable from some
institutional networks, which is itself part of this study's motivation).
Raw files are kept under ``data/raw/`` with SHA-256 provenance recorded in
``data/PROVENANCE.json``; parsed frames are cached as ``data/<name>.pkl`` and
split 80/20 with ``random_state=42`` (stratified for classification).

AutoML frameworks receive the raw feature frame — each framework performs its
own preprocessing, which is part of what this benchmark measures.

Usage:
    python -m src.load_datasets --dataset titanic
    python -m src.load_datasets --all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from . import SEED

DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))

ADULT_COLUMNS = [
    "age", "workclass", "fnlwgt", "education", "education-num",
    "marital-status", "occupation", "relationship", "race", "sex",
    "capital-gain", "capital-loss", "hours-per-week", "native-country",
    "income",
]

# task_type: "binary" | "multiclass" | "regression"
# sources: one or more raw files; multiple sources are concatenated
DATASETS = {
    "adult": {
        "task_type": "binary",
        "sources": [
            {
                # UCI Adult Income train split (32,561 rows), Google Cloud
                # sample-data mirror of the canonical adult.data
                "url": "https://storage.googleapis.com/cloud-samples-data/ml-engine/census/data/adult.data.csv",
                "read_kwargs": {
                    "header": None,
                    "names": ADULT_COLUMNS,
                    "na_values": ["?", " ?"],
                    "skipinitialspace": True,
                },
            },
            {
                # UCI Adult Income test split; this cleaned mirror has 16,278
                # rows (UCI's 16,281 minus 3 malformed) — together 48,839
                "url": "https://storage.googleapis.com/cloud-samples-data/ml-engine/census/data/adult.test.csv",
                "read_kwargs": {
                    "header": None,
                    "names": ADULT_COLUMNS,
                    "na_values": ["?", " ?"],
                    "skipinitialspace": True,
                },
            },
        ],
        "target": "income",
        "expected": {"rows": 48839, "features": 14},
    },
    "bank_marketing": {
        "task_type": "binary",
        "sources": [
            {
                # UCI Bank Marketing bank-additional-full (41,188 rows,
                # 20 features) — the variant with the study's feature count
                "url": "https://raw.githubusercontent.com/madmashup/targeted-marketing-predictive-engine/master/banking.csv",
                "read_kwargs": {},
            }
        ],
        "target": "y",
        "expected": {"rows": 41188, "features": 20},
    },
    "titanic": {
        "task_type": "binary",
        "sources": [
            {
                # classic 891-row Kaggle training set
                "url": "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv",
                "read_kwargs": {},
            }
        ],
        "target": "Survived",
        # identifier / free-text columns
        "drop": ["PassengerId", "Name", "Ticket"],
        "expected": {"rows": 891, "features": 8},
    },
    "credit_fraud": {
        "task_type": "binary",
        "sources": [
            {
                # full ULB/Kaggle Credit Card Fraud data (284,807 rows)
                "url": "https://raw.githubusercontent.com/nsethi31/Kaggle-Data-Credit-Card-Fraud-Detection/master/creditcard.csv",
                "read_kwargs": {},
            }
        ],
        "target": "Class",
        "expected": {"rows": 284807, "features": 30},
    },
    "california_housing": {
        "task_type": "regression",
        "sources": [
            {
                # 1990 California census housing (20,640 rows)
                "url": "https://raw.githubusercontent.com/ageron/handson-ml2/master/datasets/housing/housing.csv",
                "read_kwargs": {},
            }
        ],
        "target": "median_house_value",
        "expected": {"rows": 20640, "features": 9},
    },
    "ames_housing": {
        "task_type": "regression",
        "sources": [
            {
                # De Cock's original Ames data (2,930 rows, tab-separated)
                "url": "https://raw.githubusercontent.com/dlsun/pods/master/data/AmesHousing.txt",
                "read_kwargs": {"sep": "\t"},
            }
        ],
        "target": "SalePrice",
        # observation number and parcel ID
        "drop": ["Order", "PID"],
        "expected": {"rows": 2930, "features": 79},
    },
    "wine_quality": {
        "task_type": "multiclass",
        "sources": [
            {
                # UCI Wine Quality — red (1,599 rows); this mirror is
                # comma-separated with a UTF-8 BOM, unlike the white file
                "url": "https://raw.githubusercontent.com/plotly/datasets/master/winequality-red.csv",
                "read_kwargs": {"sep": ",", "encoding": "utf-8-sig"},
            },
            {
                # UCI Wine Quality — white (4,898 rows)
                "url": "https://raw.githubusercontent.com/shrikant-temburwar/Wine-Quality-Dataset/master/winequality-white.csv",
                "read_kwargs": {"sep": ";"},
            },
        ],
        "target": "quality",
        "expected": {"rows": 6497, "features": 11},
    },
}


# ---------------------------------------------------------------------------
# Download with provenance
# ---------------------------------------------------------------------------

def _download(url: str, dest: Path, attempts: int = 12) -> None:
    """Download with resume: proxies may silently truncate long transfers,
    so keep issuing Range requests until the file matches Content-Length."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    total = None
    for attempt in range(attempts):
        pos = tmp.stat().st_size if tmp.exists() else 0
        try:
            req = urllib.request.Request(url)
            if pos:
                req.add_header("Range", f"bytes={pos}-")
            with urllib.request.urlopen(req, timeout=120) as resp:
                if total is None:
                    length = resp.headers.get("Content-Length")
                    total = pos + int(length) if length else None
                mode = "ab" if pos and resp.status == 206 else "wb"
                with open(tmp, mode) as fh:
                    while chunk := resp.read(1 << 20):
                        fh.write(chunk)
        except Exception:
            if attempt == attempts - 1:
                raise
        got = tmp.stat().st_size if tmp.exists() else 0
        if total is None or got >= total:
            if total is not None and got > total:
                raise IOError(f"{url}: got {got} bytes, expected {total}")
            tmp.rename(dest)
            return
        time.sleep(min(2 ** attempt, 15))
    raise IOError(f"{url}: incomplete after {attempts} attempts "
                  f"({tmp.stat().st_size if tmp.exists() else 0}/{total} bytes)")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def _record_provenance(name: str, entries: list[dict], df: pd.DataFrame,
                       data_dir: Path) -> None:
    prov_path = data_dir / "PROVENANCE.json"
    prov = json.loads(prov_path.read_text()) if prov_path.exists() else {}
    prov[name] = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": entries,
        "parsed_rows": int(len(df)),
        "parsed_columns": int(df.shape[1]),
        "task_type": DATASETS[name]["task_type"],
    }
    prov_path.write_text(json.dumps(prov, indent=2, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Fetch + normalise
# ---------------------------------------------------------------------------

def _fetch_raw(name: str, data_dir: Path) -> pd.DataFrame:
    """Download one dataset's file(s) and return a single normalised frame."""
    cfg = DATASETS[name]
    frames, prov_entries = [], []
    for src in cfg["sources"]:
        fname = src["url"].rsplit("/", 1)[-1]
        raw_path = data_dir / "raw" / f"{name}__{fname}"
        if not raw_path.exists():
            print(f"[data] downloading {src['url']}")
            _download(src["url"], raw_path)
        frames.append(pd.read_csv(raw_path, **src["read_kwargs"]))
        prov_entries.append(
            {"url": src["url"], "sha256": _sha256(raw_path),
             "bytes": raw_path.stat().st_size}
        )

    df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]

    target = cfg["target"]
    if target not in df.columns:
        raise KeyError(
            f"target column {target!r} not found in {name}; columns: {list(df.columns)}"
        )
    df = df.drop(columns=[c for c in cfg.get("drop", []) if c in df.columns])
    df = df.rename(columns={target: "target"})

    # Classification targets as clean string categories; regression as float.
    if cfg["task_type"] == "regression":
        df["target"] = df["target"].astype(float)
    else:
        df = df.dropna(subset=["target"])
        df["target"] = (
            df["target"].astype(str).str.strip().str.rstrip(".")
        )

    _record_provenance(name, prov_entries, df, data_dir)
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
        df = _fetch_raw(name, Path(data_dir))
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
