#!/bin/bash
set -euo pipefail

link_input_file() {
  local source_file="$1"
  local target_file="$RESULT_INPUT_DIR/$(basename "$source_file")"

  rm -f "$target_file"
  ln -s "$source_file" "$target_file"
}

normalize_date() {
  local value="$1"
  local label="$2"

  if ! TZ=Asia/Tokyo date -d "$value" +%Y-%m-%d; then
    echo "Invalid $label date: $value" >&2
    exit 1
  fi
}

previous_date_for() {
  local value="$1"

  TZ=Asia/Tokyo date -d "$value -1 day" +%Y-%m-%d
}

find_previous_prompt() {
  local previous_report_dir="$1"
  local previous_date="$2"
  local expected_prompt="$previous_report_dir/prompt_market_research_${previous_date}.md"
  local -a candidates

  if [[ -f "$expected_prompt" ]]; then
    printf '%s\n' "$expected_prompt"
    return
  fi

  shopt -s nullglob
  candidates=("$previous_report_dir"/prompt_market_research_*.md)
  shopt -u nullglob

  case "${#candidates[@]}" in
    0)
      echo "Original prompt not found: $expected_prompt" >&2
      exit 1
      ;;
    1)
      echo "Expected previous prompt not found: $expected_prompt" >&2
      echo "Using fallback previous prompt: ${candidates[0]}" >&2
      printf '%s\n' "${candidates[0]}"
      ;;
    *)
      echo "Expected previous prompt not found: $expected_prompt" >&2
      echo "Multiple fallback previous prompts found. Rename one to the expected date or remove extras:" >&2
      printf '  %s\n' "${candidates[@]}" >&2
      exit 1
      ;;
  esac
}

run_agent() {
  local work_dir="$1"
  local prompt_file="$2"
  local title="$3"
  local backend="${AGENT_BACKEND:-agy}"

  case "$backend" in
    agy)
      local agy_command="${AGY_COMMAND:-agy}"
      local agy_print_timeout="${AGY_PRINT_TIMEOUT:-30m}"

      if ! command -v "$agy_command" >/dev/null 2>&1; then
        echo "Agent backend command not found: $agy_command" >&2
        exit 1
      fi

      (
        cd "$work_dir"
        "$agy_command" \
          --sandbox \
          --print-timeout "$agy_print_timeout" \
          --add-dir "$work_dir" \
          -p "$(cat "$prompt_file")"
      )
      ;;
    opencode)
      local opencode_command="${OPENCODE_COMMAND:-opencode}"
      local opencode_tool_dir="$work_dir/.agent-tools"
      local opencode_research_tool="$opencode_tool_dir/agy_research.sh"
      local opencode_shared_instructions="$opencode_tool_dir/AGENTS.md"
      local -a opencode_args

      if ! command -v "$opencode_command" >/dev/null 2>&1; then
        echo "Agent backend command not found: $opencode_command" >&2
        exit 1
      fi

      mkdir -p "$opencode_tool_dir"
      cp "$BASE_DIR/scripts/agy_research.sh" "$opencode_research_tool"
      chmod +x "$opencode_research_tool"
      if [[ -f "$BASE_DIR/AGENTS.md" ]]; then
        cp "$BASE_DIR/AGENTS.md" "$opencode_shared_instructions"
      fi

      if [[ -z "${OPENCODE_CONFIG:-}" && -f "$BASE_DIR/opencode.json" ]]; then
        export OPENCODE_CONFIG="$BASE_DIR/opencode.json"
      fi

      if [[ -z "${OPENCODE_CONFIG_DIR:-}" && -d "$BASE_DIR/.opencode" ]]; then
        export OPENCODE_CONFIG_DIR="$BASE_DIR/.opencode"
      fi

      opencode_args=(
        run
        --dir "$work_dir"
        --file "$prompt_file"
        --title "$title"
      )

      if [[ -n "${OPENCODE_MODEL:-}" ]]; then
        opencode_args+=(--model "$OPENCODE_MODEL")
      fi

      if [[ -n "${OPENCODE_AGENT:-}" ]]; then
        opencode_args+=(--agent "$OPENCODE_AGENT")
      fi

      if [[ -n "${OPENCODE_RUN_ARGS:-}" ]]; then
        # shellcheck disable=SC2206
        opencode_args+=($OPENCODE_RUN_ARGS)
      fi

      export AGY_RESEARCH_WORK_DIR="$work_dir"

      "$opencode_command" "${opencode_args[@]}" \
        "Execute the instructions in the attached prompt file. Shared repository rules are available at ./.agent-tools/AGENTS.md. Only edit files in the working directory. Write all requested output files in the working directory. If an input/ directory exists, treat it as the complete local previous-run input bundle and do not inspect parent or sibling directories. If current source discovery is required, write the research prompt to a local file and run ./.agent-tools/agy_research.sh PROMPT_FILE; do not call agy directly."
      ;;
    *)
      echo "Unsupported AGENT_BACKEND: $backend. Use 'agy' or 'opencode'." >&2
      exit 1
      ;;
  esac
}

BASE_DIR="$PWD"

if [[ -f "$BASE_DIR/.env" ]]; then
  while IFS= read -r env_line || [[ -n "$env_line" ]]; do
    if [[ "$env_line" =~ ^[[:space:]]*$ || "$env_line" =~ ^[[:space:]]*# ]]; then
      continue
    fi

    if [[ "$env_line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      env_key="${BASH_REMATCH[1]}"
      env_value="${BASH_REMATCH[2]%$'\r'}"
      if [[ -z "${!env_key+x}" ]]; then
        export "$env_key=$env_value"
      fi
    fi
  done < "$BASE_DIR/.env"
fi

if [[ -n "${RUN_DATE:-}" ]]; then
  TODAY="$(normalize_date "$RUN_DATE" "RUN_DATE")"
else
  TODAY="$(TZ=Asia/Tokyo date +%Y-%m-%d)"
fi

if [[ -n "${PREVIOUS_DATE:-}" ]]; then
  YESTERDAY="$(normalize_date "$PREVIOUS_DATE" "PREVIOUS_DATE")"
else
  YESTERDAY="$(previous_date_for "$TODAY")"
fi

RUN_PHASE="${RUN_PHASE:-all}"

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
NORMALIZER="$BASE_DIR/scripts/normalize_report_artifacts.py"
VALIDATOR="$BASE_DIR/scripts/validate_report_artifacts.py"

mkdir -p "$REPORT_DIR"

if [[ ! -f "$BASE_REPORT_PROMPT" ]]; then
  echo "Base report prompt not found: $BASE_REPORT_PROMPT" >&2
  exit 1
fi

run_review_phase() {
  local require_previous="$1"

  if [[ ! -d "$YESTERDAY_DIR" ]]; then
    if [[ "$require_previous" == "1" ]]; then
      echo "Yesterday directory not found: $YESTERDAY_DIR" >&2
      exit 1
    fi
    echo "Yesterday directory not found, skipping review phase: $YESTERDAY_DIR" >&2
    cp "$BASE_REPORT_PROMPT" "$REPORT_PROMPT"
    return
  fi

  if [[ -d "$YESTERDAY_REPORT_DIR" ]]; then
    PREVIOUS_REPORT_DIR="$YESTERDAY_REPORT_DIR"
  else
    PREVIOUS_REPORT_DIR="$YESTERDAY_DIR"
  fi

  ORIGINAL_PROMPT="$(find_previous_prompt "$PREVIOUS_REPORT_DIR" "$YESTERDAY")"
  PREVIOUS_REPORT_FILE="$PREVIOUS_REPORT_DIR/morning_market_report.md"

  if [[ ! -f "$PREVIOUS_REPORT_FILE" && -f "$PREVIOUS_REPORT_DIR/morning_market_report.html" ]]; then
    PREVIOUS_REPORT_FILE="$PREVIOUS_REPORT_DIR/morning_market_report.html"
  fi

  mkdir -p "$RESULT_INPUT_DIR"

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

  run_agent "$RESULT_DIR" "$BASE_DIR/prompt_improvement_points.md" "market prompt review $TODAY"

  if [[ ! -f "$IMPROVED_PROMPT" ]]; then
    echo "Improved prompt not found: $IMPROVED_PROMPT" >&2
    exit 1
  fi

  cp "$IMPROVED_PROMPT" "$REPORT_PROMPT"
}

prepare_report_prompt() {
  if [[ -f "$REPORT_PROMPT" ]]; then
    return
  fi

  if [[ -f "$IMPROVED_PROMPT" ]]; then
    cp "$IMPROVED_PROMPT" "$REPORT_PROMPT"
    return
  fi

  cp "$BASE_REPORT_PROMPT" "$REPORT_PROMPT"
}

clean_report_artifacts() {
  if [[ "${KEEP_EXISTING_REPORT_ARTIFACTS:-0}" == "1" ]]; then
    return
  fi

  rm -f \
    "$REPORT_DIR/research_context.md" \
    "$REPORT_DIR/research_context.json" \
    "$REPORT_DIR/research_prompt.md" \
    "$REPORT_DIR/market_facts.json" \
    "$REPORT_DIR/market_thesis.md" \
    "$REPORT_DIR/market_score.json" \
    "$REPORT_DIR/report_audit.md" \
    "$REPORT_DIR/morning_market_report.md" \
    "$REPORT_DIR/execution_plan.md"
}

run_report_phase() {
  prepare_report_prompt
  clean_report_artifacts
  run_agent "$REPORT_DIR" "$REPORT_PROMPT" "morning market report $TODAY"

  if [[ ! -f "$MORNING_REPORT" ]]; then
    echo "Morning market report not found: $MORNING_REPORT" >&2
    exit 1
  fi

  run_validate_phase
}

run_validate_phase() {
  if [[ "${SKIP_ARTIFACT_VALIDATION:-0}" == "1" ]]; then
    echo "SKIP_ARTIFACT_VALIDATION=1, skipping artifact validation: $REPORT_DIR" >&2
    return
  fi

  if [[ "${SKIP_ARTIFACT_NORMALIZATION:-0}" != "1" ]]; then
    if [[ ! -x "$NORMALIZER" ]]; then
      echo "Report artifact normalizer not found or not executable: $NORMALIZER" >&2
      exit 1
    fi
    "$NORMALIZER" "$REPORT_DIR"
  fi

  if [[ ! -x "$VALIDATOR" ]]; then
    echo "Report artifact validator not found or not executable: $VALIDATOR" >&2
    exit 1
  fi

  "$VALIDATOR" "$REPORT_DIR"
}

run_post_phase() {
  if [[ ! -f "$MORNING_REPORT" ]]; then
    echo "Morning market report not found: $MORNING_REPORT" >&2
    exit 1
  fi

  if [[ "${SKIP_DISCORD_POST:-0}" == "1" ]]; then
    echo "SKIP_DISCORD_POST=1, skipping Discord post: $MORNING_REPORT" >&2
    return
  fi

  "$BASE_DIR/scripts/post_to_discord.py" --summary "$MORNING_REPORT"
}

case "$RUN_PHASE" in
  all)
    run_review_phase 0
    run_report_phase
    run_post_phase
    ;;
  review)
    run_review_phase 1
    ;;
  report)
    run_report_phase
    ;;
  validate)
    run_validate_phase
    ;;
  post)
    run_post_phase
    ;;
  *)
    echo "Unsupported RUN_PHASE: $RUN_PHASE. Use all, review, report, validate, or post." >&2
    exit 1
    ;;
esac
