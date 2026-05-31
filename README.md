# Deep Research Market Reporter

Daily market-report automation for Japanese morning workflows.

The workflow:

1. Reviews the previous report when yesterday's report directory exists.
2. Improves the market-research prompt from that review.
3. Generates today's `morning_market_report.md` and `market_score.json`.
4. Posts a concise summary of the report to Discord.

If yesterday's report directory does not exist, the review step is skipped and the base
[`prompt_market_research.md`](prompt_market_research.md) prompt is used directly.

## Files

- [`run.sh`](run.sh): Main workflow.
- [`prompt_market_research.md`](prompt_market_research.md): Base market-report generation prompt.
- [`prompt_improvement_points.md`](prompt_improvement_points.md): Previous-report evaluation and prompt-improvement prompt.
- [`scripts/post_to_discord.py`](scripts/post_to_discord.py): Posts a Discord-friendly report summary.
- [`scripts/scheduler.py`](scripts/scheduler.py): Simple Docker-friendly daily scheduler.
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

Set at least:

```env
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

## Manual Run

```bash
./run.sh
```

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
