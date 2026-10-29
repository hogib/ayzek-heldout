#!/bin/sh
# Fetches the per-station STA/LTA tuning windows (sets/tune_*.toml): probe,
# pull and catalogue, one network group at a time per service, the three
# groups in parallel (NOA, GeoNet, KOERI/AFAD are different services).
cd "$(dirname "$0")/.."
group() {
    for f in sets/tune_$1_*.toml; do
        uv run heldout probe "$f" && uv run heldout pull "$f" && uv run heldout catalog "$f" \
            || echo "FAILED $f"
    done
}
mkdir -p logs
group greece > logs/tune_greece.log 2>&1 &
group nz > logs/tune_nz.log 2>&1 &
group ko > logs/tune_ko.log 2>&1 &
wait
echo done
