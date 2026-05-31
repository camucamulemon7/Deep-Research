#!/bin/bash
set -euo pipefail

link_input_file() {
  local source_file="$1"
  local target_file="$RESULT_INPUT_DIR/$(basename "$source_file")"

  rm -f "$target_file"
  ln -s "$source_file" "$target_file"
}

BASE_DIR="$PWD"
YESTERDAY="$(TZ=Asia/Tokyo date -d 'yesterday' +%Y-%m-%d)"
TODAY="$(TZ=Asia/Tokyo date +%Y-%m-%d)"

YESTERDAY_DIR="$BASE_DIR/agy-market-report/$YESTERDAY"
TODAY_DIR="$BASE_DIR/agy-market-report/$TODAY"
YESTERDAY_REPORT_DIR="$YESTERDAY_DIR/report"
RESULT_DIR="$YESTERDAY_DIR/result"
RESULT_INPUT_DIR="$RESULT_DIR/input"
REPORT_DIR="$TODAY_DIR/report"
BASE_REPORT_PROMPT="$BASE_DIR/prompt_market_research.md"
IMPROVED_PROMPT="$RESULT_DIR/prompt_improvement.md"
REPORT_PROMPT="$REPORT_DIR/prompt_market_research_${TODAY}.md"
MORNING_REPORT="$REPORT_DIR/morning_market_report.md"

mkdir -p "$REPORT_DIR"

if [[ ! -f "$BASE_REPORT_PROMPT" ]]; then
  echo "Base report prompt not found: $BASE_REPORT_PROMPT" >&2
  exit 1
fi

if [[ -d "$YESTERDAY_DIR" ]]; then
  if [[ -d "$YESTERDAY_REPORT_DIR" ]]; then
    PREVIOUS_REPORT_DIR="$YESTERDAY_REPORT_DIR"
  else
    PREVIOUS_REPORT_DIR="$YESTERDAY_DIR"
  fi

  ORIGINAL_PROMPT="$PREVIOUS_REPORT_DIR/prompt_market_research_${YESTERDAY}.md"
  PREVIOUS_REPORT_FILE="$PREVIOUS_REPORT_DIR/morning_market_report.md"

  if [[ ! -f "$PREVIOUS_REPORT_FILE" && -f "$PREVIOUS_REPORT_DIR/morning_market_report.html" ]]; then
    PREVIOUS_REPORT_FILE="$PREVIOUS_REPORT_DIR/morning_market_report.html"
  fi

  mkdir -p "$RESULT_INPUT_DIR"

  if [[ ! -f "$ORIGINAL_PROMPT" ]]; then
    echo "Original prompt not found: $ORIGINAL_PROMPT" >&2
    exit 1
  fi

  for required_file in "$PREVIOUS_REPORT_FILE" "$PREVIOUS_REPORT_DIR/market_score.json"; do
    if [[ ! -f "$required_file" ]]; then
      echo "Previous report file not found: $required_file" >&2
      exit 1
    fi
  done

  link_input_file "$PREVIOUS_REPORT_FILE"
  link_input_file "$PREVIOUS_REPORT_DIR/market_score.json"
  if [[ -f "$PREVIOUS_REPORT_DIR/sources.md" ]]; then
    link_input_file "$PREVIOUS_REPORT_DIR/sources.md"
  elif [[ -f "$PREVIOUS_REPORT_DIR/sources.html" ]]; then
    link_input_file "$PREVIOUS_REPORT_DIR/sources.html"
  fi
  link_input_file "$ORIGINAL_PROMPT"

  cd "$RESULT_DIR"

  agy \
    --sandbox \
    --print-timeout 30m \
    --add-dir "$RESULT_DIR" \
    -p "$(cat "$BASE_DIR/prompt_improvement_points.md")"

  if [[ ! -f "$IMPROVED_PROMPT" ]]; then
    echo "Improved prompt not found: $IMPROVED_PROMPT" >&2
    exit 1
  fi

  cp "$IMPROVED_PROMPT" "$REPORT_PROMPT"
else
  echo "Yesterday directory not found, skipping review phase: $YESTERDAY_DIR" >&2
  cp "$BASE_REPORT_PROMPT" "$REPORT_PROMPT"
fi

cd "$REPORT_DIR"

agy \
  --sandbox \
  --print-timeout 30m \
  --add-dir "$REPORT_DIR" \
  -p "$(cat "$REPORT_PROMPT")"

if [[ ! -f "$MORNING_REPORT" ]]; then
  echo "Morning market report not found: $MORNING_REPORT" >&2
  exit 1
fi

"$BASE_DIR/scripts/post_to_discord.py" --summary "$MORNING_REPORT"


