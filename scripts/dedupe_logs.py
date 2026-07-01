"""Keep only the most recent row per (framework, dataset, tier) in logs.csv.

Used after re-running failed cells (e.g. following an adapter fix): the
re-run appends a fresh row, and this script drops the superseded one.

Usage:
    python scripts/dedupe_logs.py [path/to/logs.csv]
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results/logs.csv")
df = pd.read_csv(path)
before = len(df)
df = df.drop_duplicates(subset=["framework", "dataset", "tier"], keep="last")
df.to_csv(path, index=False)
print(f"{path}: {before} -> {len(df)} rows")
