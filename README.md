# Deep Research Market Reporter

Daily market-report automation for Japanese morning workflows.

The workflow:

1. Reviews the previous report when yesterday's report directory exists.
2. Improves the market-research prompt from that review.
3. Generates today's `morning_market_report.md` and `market_score.json`.
4. Posts a concise summary of the report to Discord.

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
DISCORD_BOT_TOKEN=
DISCORD_CHANNEL_ID=
TZ=Asia/Tokyo
RUN_AT=07:30
```

`AGY_BIN` is the full host path to the `agy` executable. You can usually get it with:

```bash
command -v agy
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
OPENCODE_MODEL=openai/gpt-5.4-mini
OPENCODE_AGENT=agent-name
OPENCODE_RUN_ARGS=--format json
```

When `AGENT_BACKEND=opencode`, `run.sh` automatically points OpenCode at the
repository-local `opencode.json` and `.opencode/` directory unless `OPENCODE_CONFIG` or
`OPENCODE_CONFIG_DIR` are already set.

The repository-local OpenCode default model is `openai/gpt-5.4-mini`.

### Agent Instruction Files

Use [`AGENTS.md`](AGENTS.md) for backend-neutral repository rules: workflow, output
contracts, market-data safety rules, and what files must not be committed.

Use [`.opencode/agents/`](.opencode/agents/) for OpenCode-specific behavior: agent
prompts, permissions, tool routing, and how OpenCode should call the local `agy` search
wrapper.

`run.sh` validates the expected output files after each agent run, so either backend must
write the same files: `prompt_improvement.md` during the review phase and
`morning_market_report.md` during the report phase.

The Docker image includes the OpenCode CLI. The host `agy` binary/config is still mounted
because OpenCode search is routed through the local `agy` wrapper.

## Manual Run

```bash
./run.sh
```

For a smoke test that should generate files but not post to Discord:

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
RUN_PHASE=post RUN_DATE=2026-06-04 ./run.sh
```

Phase behavior:

- `all`: run review when previous data exists, then report, then Discord post.
- `review`: require previous data and only write review outputs plus today's improved prompt.
- `report`: generate today's report using today's prompt if it exists, otherwise the latest improved prompt, otherwise the base prompt.
- `post`: post an existing `morning_market_report.md`.

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

## Safety Notes

- `.env` is ignored by Git.
- `agy-market-report/` is ignored by Git because reports may contain run-specific data.
- Discord bot tokens should only be provided through environment variables.

## License

MIT License. See [LICENSE](LICENSE).
