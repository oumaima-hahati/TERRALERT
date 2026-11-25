#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

for year in $(seq 2001 2025); do
    echo ""
    echo "========== YEAR $year =========="

    python scripts/download_nasa_power.py \
        --year "$year" \
        --limit 11

    echo "Completed year $year"

    # Reduce request frequency between years
    sleep 15
done

echo ""
echo "NASA POWER historical download batch completed."
