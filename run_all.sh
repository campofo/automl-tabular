#!/usr/bin/env bash
# Orchestrate the full benchmark: 5 frameworks x 3 tiers x 7 datasets = 105 runs.
#
# Usage:
#   ./run_all.sh                 # all three tiers
#   ./run_all.sh constrained     # one tier (35 runs)
#
# Each run is an independent Docker container. Resource caps are enforced
# here via --memory/--cpus; the time budget is baked into each tier image.
# Results are appended to results/logs.csv on the host via a bind mount.

set -uo pipefail

FRAMEWORKS=(flaml pycaret autosklearn h2o autogluon)
DATASETS=(titanic wine_quality ames_housing california_housing bank_marketing adult credit_fraud)
ALL_TIERS=(constrained moderate unconstrained)

# --memory / --cpus per tier
declare -A TIER_MEM=([constrained]=4g [moderate]=8g [unconstrained]=16g)
declare -A TIER_CPUS=([constrained]=2 [moderate]=4 [unconstrained]=8)
# Outer wall-clock kill per run (budget + generous grace), so a framework that
# ignores its own time budget can never stall the whole campaign. The runner's
# own hard-kill watchdog should fire first; this is the last line of defence.
declare -A TIER_HARDLIMIT=([constrained]=600 [moderate]=1500 [unconstrained]=5400)

TIERS=("${ALL_TIERS[@]}")
if [[ $# -ge 1 ]]; then
    TIERS=("$1")
fi

mkdir -p results data figures

# Pre-fetch all datasets once on the host so containers hit the cache and
# network variance never counts against a framework's time budget.
echo "==> Pre-fetching datasets into ./data"
python -m src.load_datasets --all

for tier in "${TIERS[@]}"; do
    for framework in "${FRAMEWORKS[@]}"; do
        image="automl-${framework}:${tier}"
        echo "==> Building ${image}"
        docker build \
            -f "docker/Dockerfile.${tier}" \
            --build-arg "FRAMEWORK=${framework}" \
            -t "${image}" . || {
            echo "!! build failed for ${image}; skipping its runs" >&2
            continue
        }

        for dataset in "${DATASETS[@]}"; do
            echo "==> Running ${framework} / ${dataset} / ${tier}"
            cname="run_${framework}_${dataset}_${tier}"
            # `timeout --kill-after` guarantees the container is torn down even
            # if it wedges; --name lets us force-remove it if the kill lands.
            timeout --kill-after=60 "${TIER_HARDLIMIT[$tier]}" \
                docker run --rm --name "${cname}" \
                    --memory="${TIER_MEM[$tier]}" \
                    --memory-swap="${TIER_MEM[$tier]}" \
                    --cpus="${TIER_CPUS[$tier]}" \
                    -v "$(pwd)/results:/app/results" \
                    -v "$(pwd)/data:/app/data" \
                    "${image}" \
                    --dataset "${dataset}" \
                || { echo "!! ${framework}/${dataset}/${tier} did not complete (logged)" >&2
                     docker rm -f "${cname}" >/dev/null 2>&1 || true; }
        done
    done
done

echo "==> Done. See results/logs.csv"
