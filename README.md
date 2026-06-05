# Deep Research Market Reporter

Daily market-report automation for Japanese morning workflows.

The workflow:

1. Reviews the previous report when yesterday's report directory exists.
2. Improves the market-research prompt from that review.
3. Generates staged research artifacts, today's `morning_market_report.md`, and `market_score.json`.
4. Validates the required artifacts.
5. Posts a concise summary of the report to Discord.

If yesterday's report directory does not exist, the review step is skipped and the base
[`prompt_market_research.md`](prompt_market_research.md) prompt is used directly.

## Previous-Day Review

When `agy-market-report/YYYY-MM-DD/` exists for yesterday, `run.sh` runs a review phase
before generating today's report. The previous report directory must contain:

```text
morning_market_report.md
market_score.json
prompt_market_research_YYYY-MM-DD.md
```

If the exact prompt filename is missing but exactly one `prompt_market_research_*.md`
file exists in the previous report directory, `run.sh` uses that file as a fallback and
prints a warning. If multiple candidates exist, the run stops and asks you to keep only
one or rename the intended file to the expected date.

The review phase writes:

```text
agy-market-report/YYYY-MM-DD/result/next_day_evaluation_report.md
agy-market-report/YYYY-MM-DD/result/evaluation_score.json
agy-market-report/YYYY-MM-DD/result/prompt_improvement.md
```

`prompt_improvement.md` is then copied to today's report directory as:

```text
agy-market-report/YYYY-MM-DD/report/prompt_market_research_YYYY-MM-DD.md
```

If yesterday's directory is missing, this phase is skipped and the base prompt is copied
instead.

## Files

- [`run.sh`](run.sh): Main workflow.
- [`AGENTS.md`](AGENTS.md): Shared instructions for coding agents working in this repository.
- [`prompt_market_research.md`](prompt_market_research.md): Base market-report generation prompt.
- [`prompt_improvement_points.md`](prompt_improvement_points.md): Previous-report evaluation and prompt-improvement prompt.
- [`scripts/post_to_discord.py`](scripts/post_to_discord.py): Posts a Discord-friendly report summary.
- [`scripts/scheduler.py`](scripts/scheduler.py): Simple Docker-friendly daily scheduler.
- [`scripts/normalize_report_artifacts.py`](scripts/normalize_report_artifacts.py): Normalizes backend output shape before validation.
- [`scripts/validate_report_artifacts.py`](scripts/validate_report_artifacts.py): Validates staged report artifacts.
- [`opencode.json`](opencode.json): Project-level OpenCode defaults.
- [`.opencode/agents/market-reporter.md`](.opencode/agents/market-reporter.md): OpenCode market-report agent.
- [`compose.yaml`](compose.yaml): Manual and scheduled Docker services.
- [`CONTAINER.md`](CONTAINER.md): Container usage details.

## Required Local Secrets

Do not commit `.env`.

This project expects the Antigravity CLI command `agy` to be installed and authenticated
on the host machine before running Docker. The Docker image does not install or bundle
Antigravity CLI; it mounts your existing host binary and config.

Check your local install:

```bash
command -v agy
agy --version
```

Create one from the example:

```bash
cp .env.example .env
```

`run.sh` reads `.env` automatically for local runs. Environment variables that are
already exported by your shell or Docker Compose take precedence.

Set at least:

```env
AGENT_BACKEND=agy
AGY_BIN=/path/to/agy
AGY_HOME=/path/to/.gemini
OPENCODE_BIN=/path/to/opencode
DISCORD_BOT_TOKEN=
DISCORD_CHANNEL_ID=
TZ=Asia/Tokyo
RUN_AT=07:30
```

`AGY_BIN` is the full host path to the `agy` executable. You can usually get it with:

```bash
command -v agy
```

`OPENCODE_BIN` is the full host path to the OpenCode executable for Docker runs. Prefer
the resolved binary path, not a symlink:

```bash
readlink -f "$(command -v opencode)"
```

`AGY_HOME` is the host directory where Antigravity CLI stores its authentication/config.
For a standard install this is usually:

```text
~/.gemini
```

`OPENAI_API_KEY`, `GOOGLE_API_KEY`, and `GEMINI_API_KEY` are optional passthrough values
for setups where `agy` reads provider credentials from the environment.

## Agent Backend

The default backend is Antigravity CLI:

```env
AGENT_BACKEND=agy
```

To run the report workflow with OpenCode instead, install and authenticate OpenCode,
then set:

```env
AGENT_BACKEND=opencode
OPENCODE_COMMAND=opencode
```

Optional OpenCode settings:

```env
OPENCODE_MODEL=
OPENCODE_AGENT=
OPENCODE_RUN_ARGS=--format json
```

When `AGENT_BACKEND=opencode`, `run.sh` automatically points OpenCode at the
repository-local `opencode.json` and `.opencode/` directory unless `OPENCODE_CONFIG` or
`OPENCODE_CONFIG_DIR` are already set.

The repository-local OpenCode defaults are configured in `opencode.json`:

```json
{
  "model": "openai/gpt-5.4-mini",
  "default_agent": "market-reporter"
}
```

Use `.env` only for temporary overrides. If `OPENCODE_MODEL` is non-empty, `run.sh` passes
`--model "$OPENCODE_MODEL"` to `opencode run`, which overrides the model in `opencode.json`.
The same applies to `OPENCODE_AGENT`.

OpenCode authentication can be provided in either of two ways:

- Set provider keys such as `OPENAI_API_KEY` in `.env`.
- Run `opencode auth login` on the host and let Docker mount the standard OpenCode auth/config directories.

For Zhipu/ZAi models, provider names matter:

- `zhipuai-coding-plan/glm-5.1` uses the Zhipu AI Coding Plan provider.
- `zai-coding-plan/glm-5.1` uses the Z.AI Coding Plan provider.

Run `opencode auth login` for the provider you want to use, or set `ZHIPU_API_KEY` in
`.env` when you prefer environment-based auth.

Docker Compose mounts these host paths by default when they exist:

```text
~/.config/opencode       -> /home/app/.config/opencode
~/.local/share/opencode  -> /home/app/.local/share/opencode
~/.local/state/opencode  -> /home/app/.local/state/opencode
~/.cache/opencode        -> /home/app/.cache/opencode
```

Override them with `OPENCODE_CONFIG_HOME`, `OPENCODE_DATA_HOME`,
`OPENCODE_STATE_HOME`, or `OPENCODE_CACHE_HOME` if your OpenCode installation stores
auth elsewhere.

### Agent Instruction Files

Use [`AGENTS.md`](AGENTS.md) for backend-neutral repository rules: workflow, output
contracts, market-data safety rules, and what files must not be committed.

Use [`.opencode/agents/`](.opencode/agents/) for OpenCode-specific behavior: agent
prompts, permissions, tool routing, and how OpenCode should call the local `agy` search
wrapper.

`run.sh` validates the expected output files after the report phase, so either backend must
write the same staged artifacts during report generation.

OpenCode and `agy` binaries are mounted from the host so Docker uses the same CLI builds
you authenticate and update locally. OpenCode search is still routed through the local
`agy` wrapper.

## Manual Run

```bash
./run.sh
```

For a production-style dry run that should generate and validate files but not post to Discord:

```bash
SKIP_DISCORD_POST=1 ./run.sh
```

### Reruns And Phase Control

By default, `run.sh` uses the current Asia/Tokyo date and runs every phase:

```env
RUN_PHASE=all
```

For backfills or reruns, override the target dates:

```bash
RUN_DATE=2026-06-04 PREVIOUS_DATE=2026-06-03 SKIP_DISCORD_POST=1 ./run.sh
```

`PREVIOUS_DATE` is optional. When omitted, it is calculated as one day before
`RUN_DATE`.

You can also run one phase at a time:

```bash
RUN_PHASE=review RUN_DATE=2026-06-04 PREVIOUS_DATE=2026-06-03 ./run.sh
RUN_PHASE=report RUN_DATE=2026-06-04 SKIP_DISCORD_POST=1 ./run.sh
RUN_PHASE=validate RUN_DATE=2026-06-04 ./run.sh
RUN_PHASE=post RUN_DATE=2026-06-04 ./run.sh
```

Phase behavior:

- `all`: run review when previous data exists, then report, then Discord post.
- `review`: require previous data and only write review outputs plus today's improved prompt.
- `report`: generate today's report using today's prompt if it exists, otherwise the latest improved prompt, otherwise the base prompt.
- `validate`: validate existing report artifacts without regenerating the report.
- `post`: post an existing `morning_market_report.md`.

Artifact validation can be disabled for emergency investigation runs:

```env
SKIP_ARTIFACT_VALIDATION=1
```

By default, `run.sh` first normalizes common backend output variations before validating.
To inspect raw agent output exactly as generated:

```env
SKIP_ARTIFACT_NORMALIZATION=1
```

`RUN_PHASE=report` removes existing generated report artifacts before asking the agent to
produce a fresh report. To keep existing artifacts during investigation:

```env
KEEP_EXISTING_REPORT_ARTIFACTS=1
```

### Timing Logs

`run.sh` prints phase timing lines during each run:

```text
[timing] review agent 00:13:40 (...)
[timing] report agent 00:19:40 (...)
[timing] run total    00:33:20 (...)
```

When OpenCode routes source discovery through `agy`, the wrapper also writes per-search
timing to the active work directory:

```text
agy-market-report/YYYY-MM-DD/result/agy_research_timing.log
agy-market-report/YYYY-MM-DD/report/agy_research_timing.log
```

These sidecar logs are kept out of the research JSON so timing metadata does not pollute
the report inputs.

## Docker Run

Build:

```bash
docker compose build
```

Run once:

```bash
docker compose run --rm deep-research
```

## Scheduled Docker Run

Set the schedule in `.env`:

```env
TZ=Asia/Tokyo
RUN_AT=07:30
RUN_ON_START=0
```

Start the scheduler:

```bash
docker compose up -d deep-research-scheduler
```

Follow logs:

```bash
docker compose logs -f deep-research-scheduler
```

Stop:

```bash
docker compose down
```

## Output Location

Generated reports are written under:

```text
agy-market-report/YYYY-MM-DD/report/
```

When using Docker Compose, the project directory is bind-mounted into the container at
`/workspace`, so `agy-market-report/` is created and updated on the host machine as well.
You can inspect generated files outside the container normally.

The report directory contains these staged artifacts:

```text
research_context.md
market_facts.json
market_thesis.md
market_score.json
report_audit.md
morning_market_report.md
prompt_market_research_YYYY-MM-DD.md
```

`market_facts.json` is the factual source layer, `market_thesis.md` records the investment
thesis, `market_score.json` captures quantitative scoring with supporting and opposing
factors, and `report_audit.md` records source/date/consistency checks before the final
report is posted.

Because different agent backends may produce slightly different JSON shapes, `run.sh`
normalizes common variants before validation. The normalizer preserves the original fields
and adds the common keys expected by the validator.

## Safety Notes

- `.env` is ignored by Git.
- `agy-market-report/` is ignored by Git because reports may contain run-specific data.
- Discord bot tokens should only be provided through environment variables.

## License

MIT License. See [LICENSE](LICENSE).
