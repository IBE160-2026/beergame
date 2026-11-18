#!/usr/bin/env bash
# Simulation LLM smoke run (Story 2.11): register the mock model config and an evaluation budget
# with the commands of Story 2.2, play a small batch of Games with `llm` Seats on the mock
# provider through a real `worker-ai` process, and print the batch report.
#
# Run from `backend/` with DATABASE_URL pointing at a migrated database (CI: the job's Postgres
# service). No key: in `local`, `test` and `ci` the mock answers (AD-17).
set -euo pipefail

config=$(uv run python -m app.ai.cli config add ai-configs/mock.json | awk '/^config /{print $2}')
uv run python -m app.ai.cli budget set --evaluation "$config" --limit 1 --reserve 0

uv run python -m app.worker --queues ai-orders &
worker=$!
trap 'kill "$worker" 2>/dev/null || true; wait "$worker" 2>/dev/null || true' EXIT

out=$(uv run python -m app.sim run batches/measure-mock-smoke.json --config "$config" --worker) ||
  { echo "$out"; exit 1; }
echo "$out"
batch=$(echo "$out" | awk '/^batch_id /{print $2}')
report=$(uv run python -m app.sim report "$batch")
echo "$report"
# Mock numbers are never measurements: the report must say so on its first line.
[[ "$(echo "$report" | head -n 1)" == "MOCK PROVIDER"* ]]
# The worker played every LLM Order: 2 Games x 4 Weeks after the Guided ones x 4 Seats.
echo "$report" | grep -qx '  llm_share orders=32/32 share=1.0000'
echo "$report" | grep -qx 'cut_short no'
# Story 2.12: a mock batch is never approved as a measurement.
if approve=$(uv run python -m app.sim approve "$batch" --level standard 2>&1); then
  echo "$approve"; echo "approve of a mock batch was not refused"; exit 1
fi
echo "$approve" | grep -q '^error mock_batch: '
echo "approve refused: mock_batch"
