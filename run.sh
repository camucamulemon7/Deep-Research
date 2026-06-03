#!/bin/bash
set -euo pipefail

link_input_file() {
  local source_file="$1"
  local target_file="$RESULT_INPUT_DIR/$(basename "$source_file")"

  rm -f "$target_file"
  ln -s "$source_file" "$target_file"
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
        "Execute the instructions in the attached prompt file. Shared repository rules are available at ./.agent-tools/AGENTS.md. Only edit files in the working directory. Write all requested output files in the working directory. If current source discovery is required, write the research prompt to a local file and run ./.agent-tools/agy_research.sh PROMPT_FILE; do not call agy directly."
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

  run_agent "$RESULT_DIR" "$BASE_DIR/prompt_improvement_points.md" "market prompt review $TODAY"

  if [[ ! -f "$IMPROVED_PROMPT" ]]; then
    echo "Improved prompt not found: $IMPROVED_PROMPT" >&2
    exit 1
  fi

  cp "$IMPROVED_PROMPT" "$REPORT_PROMPT"
else
  echo "Yesterday directory not found, skipping review phase: $YESTERDAY_DIR" >&2
  cp "$BASE_REPORT_PROMPT" "$REPORT_PROMPT"
fi

run_agent "$REPORT_DIR" "$REPORT_PROMPT" "morning market report $TODAY"

if [[ ! -f "$MORNING_REPORT" ]]; then
  echo "Morning market report not found: $MORNING_REPORT" >&2
  exit 1
fi

if [[ "${SKIP_DISCORD_POST:-0}" == "1" ]]; then
  echo "SKIP_DISCORD_POST=1, skipping Discord post: $MORNING_REPORT" >&2
  exit 0
fi

"$BASE_DIR/scripts/post_to_discord.py" --summary "$MORNING_REPORT"
