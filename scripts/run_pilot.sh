#!/usr/bin/env bash
# Pilot benchmark campaign for restricted/sandboxed environments.
#
# Runs the full 5 frameworks x 7 datasets x 3 tiers grid with REDUCED time
# budgets (60/120/240s by default) so the whole campaign fits in hours
# instead of days. RAM/CPU caps are enforced exactly as in the paper design
# for the constrained and moderate tiers; the unconstrained tier is capped
# by the host (see results/PILOT_NOTES.md). The paper-grade campaign with
# full budgets remains ./run_all.sh.
#
# Usage:
#   scripts/run_pilot.sh              # everything
#   scripts/run_pilot.sh flaml        # one framework
#
# Env overrides:
#   PILOT_BUDGETS="60 120 240"   per-tier seconds (constrained moderate unconstrained)
#   CA_BUNDLE=/path/to/ca.crt    egress-proxy CA for build-time TLS

set -uo pipefail
cd "$(dirname "$0")/.."

ALL_FRAMEWORKS=(flaml pycaret h2o autogluon autosklearn)
DATASETS=(titanic wine_quality ames_housing california_housing bank_marketing adult credit_fraud)
TIERS=(constrained moderate unconstrained)

read -r B_CON B_MOD B_UNC <<< "${PILOT_BUDGETS:-60 120 240}"
declare -A TIER_MEM=([constrained]=4g [moderate]=8g [unconstrained]=14g)
declare -A TIER_CPUS=([constrained]=2 [moderate]=4 [unconstrained]=4)
declare -A TIER_BUDGET=([constrained]=$B_CON [moderate]=$B_MOD [unconstrained]=$B_UNC)

FRAMEWORKS=("${ALL_FRAMEWORKS[@]}")
if [[ $# -ge 1 ]]; then
    FRAMEWORKS=("$@")
fi

CA_BUNDLE="${CA_BUNDLE:-/root/.ccr/ca-bundle.crt}"

mkdir -p results data .pilot
if [[ -f "$CA_BUNDLE" ]]; then
    cp "$CA_BUNDLE" .pilot/ca-bundle.crt
else
    # no proxy in this environment: use the system bundle (harmless no-op CA)
    cp /etc/ssl/certs/ca-certificates.crt .pilot/ca-bundle.crt
fi

build_image() {
    local fw="$1"
    # Reuse an existing image unless explicitly asked to rebuild: images are
    # multi-GB and concurrent rebuilds can starve the shared egress proxy.
    if [[ "${PILOT_REBUILD:-0}" != "1" ]] && \
       docker image inspect "automl-pilot-${fw}" > /dev/null 2>&1; then
        echo "==> image automl-pilot-${fw} exists; skipping build"
        return 0
    fi
    docker build \
        --network=host \
        -f docker/Dockerfile.pilot \
        --build-arg "FRAMEWORK=${fw}" \
        --build-arg "HTTPS_PROXY=${HTTPS_PROXY:-}" \
        --build-arg "NO_PROXY=${NO_PROXY:-localhost,127.0.0.1}" \
        -t "automl-pilot-${fw}" .
}

for fw in "${FRAMEWORKS[@]}"; do
    echo "==> [$(date +%H:%M:%S)] building automl-pilot-${fw}"
    if ! build_image "$fw"; then
        echo "!! build failed for ${fw}; logging its 21 cells as failed" >&2
        for tier in "${TIERS[@]}"; do
            for ds in "${DATASETS[@]}"; do
                python - "$fw" "$ds" "$tier" <<'PYEOF'
import sys
sys.path.insert(0, ".")
from src.utils import append_log_row
fw, ds, tier = sys.argv[1:4]
append_log_row({"framework": fw, "dataset": ds, "tier": tier,
                "status": "failed: docker image build failed"})
PYEOF
            done
        done
        continue
    fi

    for tier in "${TIERS[@]}"; do
        for ds in "${DATASETS[@]}"; do
            echo "==> [$(date +%H:%M:%S)] ${fw} / ${ds} / ${tier} (${TIER_BUDGET[$tier]}s, ${TIER_CPUS[$tier]}cpu, ${TIER_MEM[$tier]})"
            rows_before=$(wc -l < results/logs.csv 2>/dev/null || echo 0)
            docker run --rm \
                --memory="${TIER_MEM[$tier]}" \
                --memory-swap="${TIER_MEM[$tier]}" \
                --cpus="${TIER_CPUS[$tier]}" \
                -e "TIER=${tier}" \
                -e "TIME_BUDGET=${TIER_BUDGET[$tier]}" \
                -v "$(pwd)/results:/app/results" \
                -v "$(pwd)/data:/app/data" \
                "automl-pilot-${fw}" \
                --dataset "${ds}" \
                || echo "!! ${fw}/${ds}/${tier} did not complete (logged)" >&2
            rows_after=$(wc -l < results/logs.csv 2>/dev/null || echo 0)
            if [[ "$rows_after" -eq "$rows_before" ]]; then
                # container died before the runner could log (e.g. OOM kill)
                python - "$fw" "$ds" "$tier" <<'PYEOF'
import sys
sys.path.insert(0, ".")
from src.utils import append_log_row
fw, ds, tier = sys.argv[1:4]
append_log_row({"framework": fw, "dataset": ds, "tier": tier,
                "status": "failed: container killed (out of memory)"})
PYEOF
            fi
        done
    done
done

echo "==> [$(date +%H:%M:%S)] pilot campaign finished; see results/logs.csv"
