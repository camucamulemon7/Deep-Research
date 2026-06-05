#!/bin/bash
set -euo pipefail

usage() {
  echo "Usage: $0 PROMPT_FILE" >&2
}

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

PROMPT_FILE="$1"
AGY_COMMAND="${AGY_COMMAND:-agy}"
AGY_PRINT_TIMEOUT="${AGY_PRINT_TIMEOUT:-10m}"
WORK_DIR="${AGY_RESEARCH_WORK_DIR:-$PWD}"
PREFIX="${AGY_RESEARCH_PREFIX:-WebSearch:}"
TIMING_LOG="${AGY_RESEARCH_TIMING_LOG:-$WORK_DIR/agy_research_timing.log}"

timer_now() {
  date +%s
}

format_duration() {
  local seconds="$1"
  local hours=$((seconds / 3600))
  local minutes=$(((seconds % 3600) / 60))
  local secs=$((seconds % 60))

  printf '%02d:%02d:%02d' "$hours" "$minutes" "$secs"
}

log_timing() {
  local status="$1"
  local start="$2"
  local end="$3"
  local elapsed=$((end - start))

  mkdir -p "$(dirname "$TIMING_LOG")"
  printf '[timing] agy_research %-7s %s prompt=%s work_dir=%s (%s -> %s)\n' \
    "$status" \
    "$(format_duration "$elapsed")" \
    "$PROMPT_FILE" \
    "$WORK_DIR" \
    "$(TZ=Asia/Tokyo date -d "@$start" '+%Y-%m-%d %H:%M:%S %Z')" \
    "$(TZ=Asia/Tokyo date -d "@$end" '+%Y-%m-%d %H:%M:%S %Z')" >> "$TIMING_LOG"
}

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "Prompt file not found: $PROMPT_FILE" >&2
  exit 1
fi

if ! command -v "$AGY_COMMAND" >/dev/null 2>&1; then
  echo "agy command not found: $AGY_COMMAND" >&2
  exit 1
fi

STARTED_AT="$(timer_now)"
STATUS="success"

set +e
{
  printf '%s\n' "$PREFIX"
  printf '%s\n' "Use web search only. Do not inspect local files. Do not describe your plan."
  printf '%s\n\n' "Return only the final requested output with source URLs and timestamps when available."
  cat "$PROMPT_FILE"
} | "$AGY_COMMAND" \
  --sandbox \
  --print-timeout "$AGY_PRINT_TIMEOUT" \
  --add-dir "$WORK_DIR" \
  --print "$(cat)"
EXIT_CODE="$?"
set -e

if [[ "$EXIT_CODE" -ne 0 ]]; then
  STATUS="failed:$EXIT_CODE"
fi

FINISHED_AT="$(timer_now)"
log_timing "$STATUS" "$STARTED_AT" "$FINISHED_AT"
exit "$EXIT_CODE"
