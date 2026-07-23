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

## Adapter fixes made during the pilot

Running the real frameworks surfaced version-drift bugs that are now fixed in
`src/frameworks/` (these are genuine hardening, valid for the paper campaign too):

- **PyCaret** — its internal holdout split is not stratified by default, so on
  `wine_quality` (rare quality classes) `predict()` hit *"y contains previously
  unseen labels"*. Fixed by enabling `data_split_stratify` + `stratifiedkfold`
  for classification tasks.
- **AutoGluon** — `TabularPredictor.fit()` in autogluon 1.1.x does not accept a
  `random_seed` argument (it raises `ValueError`). Fixed by seeding the global
  `random`/`numpy` RNGs before `fit()` instead.
- **FLAML** — pinned `xgboost<2.1` (2.1 removed the `callbacks` kwarg FLAML 2.1.2
  still passes) and `pandas<2.2` (3.x breaks FLAML's dtype handling).

## Runtime discipline observations

- **Time-budget adherence differs sharply.** FLAML and H2O land within a few
  seconds of every budget. **PyCaret ignores its budget** on some datasets —
  `compare_models(budget_time=…)` cannot interrupt native joblib/estimator
  sections, so several `wine_quality`/large-data cells ran far past budget.
  An external 900 s per-container watchdog killed those; such cells are logged
  as `timeout`. This is a real, reportable completion-rate finding, not a bug.
- Images carrying an adapter fix were refreshed with a thin **overlay build**
  (`FROM <image>` + `COPY src/`) rather than a full rebuild — the host disk is
  too small for AutoGluon's ~12 GB `--no-cache` rebuild.

## Final pilot outcome (105/105 cells)

Status tally: **100 completed, 4 timeout, 1 failed**. All non-completed cells
are PyCaret on `wine_quality`/`ames_housing`/`bank_marketing`:

- The 4 `timeout` cells are PyCaret runs the external 900 s watchdog had to
  kill (see the budget-adherence note above).
- The 1 `failed` cell — `pycaret,wine_quality,constrained` — raises
  `ValueError: y contains previously unseen labels: 7` *despite* the
  stratification fix. At the constrained budget (60 s / 4 GB) the model that
  wins PyCaret's truncated search was trained on a CV fold missing the rare
  wine-quality class 7, so `predict` on the held-out set hits an unseen label.
  At the moderate/unconstrained budgets the same cells instead `timeout`
  (PyCaret runs past that point but can't finish), so this is genuine
  budget-dependent PyCaret behaviour on rare-class multiclass under tight
  resources — a real completion-rate finding, not an unfixed adapter bug.

Every other framework completed all 21 cells. This clean failure/timeout
concentration on one framework/dataset is exactly the kind of signal the
study's failure heatmap is meant to surface.

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
