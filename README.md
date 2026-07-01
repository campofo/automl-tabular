# AutoML Tabular Benchmark

**Comparative Evaluation of AutoML Frameworks for Tabular Data in Resource-Constrained Environments — Implications for Data Science Practice in Ghana**

Prepared for the 4th Annual Statistics and Data Science Conference 2026 (Ghana Statistical Association), Tamale Technical University, 25–29 August 2026.

## Research Question

> Which open-source AutoML framework delivers the best accuracy-to-resource ratio for tabular ML tasks on hardware typical of Ghanaian public-sector institutions?

## Experiment Design

```
5 frameworks × 3 resource tiers × 7 datasets = 105 experimental runs
```

### Frameworks

| Framework | Developer | Key Strength |
|---|---|---|
| AutoGluon | Amazon AWS | Highest accuracy, ensemble stacking |
| PyCaret | Community | Fastest runs, low memory, easy API |
| FLAML | Microsoft | Cost-frugal optimisation, low compute |
| auto-sklearn | AutoML Freiburg Group | Competition winner, scikit-learn base |
| H2O AutoML | H2O.ai | Scalable, fast inference |

### Resource Tiers (enforced via Docker)

| Tier | RAM | CPU Cores | Time Budget | Represents |
|---|---|---|---|---|
| Constrained | 4 GB | 2 cores | 5 min | Basic government office laptop |
| Moderate | 8 GB | 4 cores | 15 min | Standard institutional workstation |
| Unconstrained | 16 GB | 8 cores | 60 min | High-spec research machine |

### Datasets

| # | Dataset | Task | Rows | Domain |
|---|---|---|---|---|
| 1 | UCI Adult Income | Binary classification | 48,842 | Finance / Policy |
| 2 | Bank Marketing | Binary classification | 45,211 | Finance |
| 3 | Titanic | Binary classification | 891 | Benchmark standard |
| 4 | Credit Card Fraud | Binary (imbalanced) | 284,807 | Finance / Risk |
| 5 | California Housing | Regression | 20,640 | Urban planning |
| 6 | Ames Housing | Regression | 2,930 | Urban planning |
| 7 | Wine Quality | Multiclass classification | 6,497 | Agriculture |

## Repository Layout

```
docker/              Dockerfiles for the 3 resource tiers (one framework per image via build-arg)
src/                 Dataset loading, benchmark runner, profiling utilities
src/frameworks/      One adapter per AutoML framework (common run() interface)
requirements/        Per-framework dependency pins (frameworks conflict if co-installed)
notebooks/           Analysis notebook (summary table, Pareto plot, degradation, heatmap)
results/logs.csv     Master experiment log (one row per run)
figures/             Generated plots
paper/               Conference paper draft
slides/              Presentation deck
run_all.sh           Orchestrates all 105 containerised runs
```

## Quick Start

### 1. Local smoke test (no Docker)

FLAML has the lightest install, so use it to verify the pipeline first:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements/flaml.txt
python -m src.load_datasets --dataset titanic          # fetch + cache one dataset
python -m src.benchmark_runner --framework flaml --dataset titanic --tier constrained
```

### 2. Full containerised benchmark

```bash
# Build one image per framework per tier, e.g.:
docker build -f docker/Dockerfile.constrained --build-arg FRAMEWORK=flaml -t automl-flaml:constrained .

# Or run everything (35 builds/runs per tier):
./run_all.sh                 # all tiers
./run_all.sh constrained     # single tier
```

Resource limits are applied at `docker run` time (`--memory`, `--cpus`); the time
budget is baked into each tier image as `TIME_BUDGET` and enforced by the runner.

Results are appended to `results/logs.csv`:

```
framework,dataset,tier,f1,auc,rmse,time_sec,peak_ram_mb,cpu_pct,status
```

`status` ∈ `completed` | `timeout` | `failed: <error>`.

### 3. Analysis

```bash
jupyter lab notebooks/analysis.ipynb
```

Produces the master summary table, Pareto frontier plots, degradation curves,
failure heatmap, and the framework recommendation matrix.

## Known Framework Gotchas

| Framework | Issue | Fix |
|---|---|---|
| AutoGluon | Conflicts with other frameworks | Separate image/venv per framework (this repo does that) |
| auto-sklearn | Linux only | Use WSL2 on Windows, or Docker |
| H2O AutoML | Requires Java 11+ | The H2O image installs OpenJDK 17; check `java -version` locally |
| PyCaret | Conflicts with newer scikit-learn | Pinned `scikit-learn==1.3.2` |
| FLAML | Lightest install | Use as the first pipeline smoke test |

## Reproducibility

- All random states seeded at **42**
- Every run is independent and containerised
- Datasets are fetched programmatically (OpenML / scikit-learn) and cached under `data/`

## Authors

- **Dr. Hanifatu Napari Mumuni** — Tamale Technical University (lead researcher)
- **Clement Donkor Ampofo** — MTech, Data Science (co-author)
