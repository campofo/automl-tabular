# Pilot Campaign Notes

`results/logs.csv` currently holds the **pilot campaign**: all 105 cells of
the study grid (5 frameworks × 7 datasets × 3 tiers) executed on the **real
datasets** (see `data/PROVENANCE.json`) in Docker containers with enforced
resource caps. It validates the full pipeline end-to-end and gives a first
relative picture, but it deviates from the paper protocol in two ways, so
these numbers are **not** the final results.

## Deviations from the paper protocol

| Aspect | Paper protocol | This pilot |
|---|---|---|
| Time budget, constrained | 300 s | **60 s** |
| Time budget, moderate | 900 s | **120 s** |
| Time budget, unconstrained | 3600 s | **240 s** |
| Unconstrained tier caps | 8 cores / 16 GB | **4 cores / 14 GB** (host maximum in the pilot environment) |
| Constrained tier caps | 2 cores / 4 GB | 2 cores / 4 GB ✓ |
| Moderate tier caps | 4 cores / 8 GB | 4 cores / 8 GB ✓ |

Additional environment note: the pilot images were built with
`docker/Dockerfile.pilot` (PyPI-sourced swig and Java because apt is
unreachable behind the sandbox's egress policy). Framework versions are
identical to the paper pins in `requirements/`.

## What transfers and what doesn't

- **Completion/failure patterns** (which framework survives 4 GB / 2 cores on
  which dataset) are directly meaningful — resource caps are real.
- **Peak RAM** is comparable to the paper protocol (memory needs don't shrink
  with shorter budgets; if anything the pilot understates ensemble growth).
- **F1 / RMSE values** are lower bounds: every framework had far less search
  time than the paper protocol allows.
- **Relative rankings** are indicative, not final: frameworks that improve
  steeply with more search time (e.g. stacking ensembles) are handicapped at
  60–240 s.

## Regenerating paper-grade results

On the target institutional hardware (Docker + internet access):

```bash
./run_all.sh            # full budgets: 300/900/3600 s, all 105 runs (~2 days)
```

The script overwrites nothing — it appends to `results/logs.csv`; archive or
truncate the pilot rows first:

```bash
mv results/logs.csv results/logs_pilot.csv
head -1 results/logs_pilot.csv > results/logs.csv
```

To rerun the pilot itself (e.g. after an adapter fix):

```bash
scripts/run_pilot.sh                 # everything
scripts/run_pilot.sh h2o             # one framework's 21 cells
PILOT_BUDGETS="30 60 120" scripts/run_pilot.sh   # even faster smoke pass
```
