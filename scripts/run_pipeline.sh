#!/usr/bin/env bash
# Daily pipeline trigger — safe to run from host cron even if Docker is down.
# Usage: add to crontab: 0 20 * * * /path/to/mobiPartner/scripts/run_pipeline.sh

set -euo pipefail

COMPOSE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
API_URL="http://localhost:8000/api/scrape/run-pipeline"
LOG_FILE="$COMPOSE_DIR/scripts/pipeline.log"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') pipeline trigger ===" >> "$LOG_FILE"

# Ensure Docker services are up
cd "$COMPOSE_DIR"
docker compose up -d >> "$LOG_FILE" 2>&1

# Wait for backend to be healthy (up to 60s)
for i in $(seq 1 12); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    break
  fi
  echo "Waiting for backend... ($i)" >> "$LOG_FILE"
  sleep 5
done

# Trigger the pipeline
response=$(curl -sf -X POST "$API_URL" 2>&1) || {
  echo "ERROR: failed to trigger pipeline: $response" >> "$LOG_FILE"
  exit 1
}

echo "Pipeline started: $response" >> "$LOG_FILE"
