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

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "Prompt file not found: $PROMPT_FILE" >&2
  exit 1
fi

if ! command -v "$AGY_COMMAND" >/dev/null 2>&1; then
  echo "agy command not found: $AGY_COMMAND" >&2
  exit 1
fi

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
