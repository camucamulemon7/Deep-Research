# Container Usage

This project can run inside Docker while reusing the host `agy` binary and its existing authentication/config.

## 1. Create `.env`

```bash
cp .env.example .env
```

Edit `.env`:

```env
AGY_BIN=/home/your-user/.local/bin/agy
AGY_HOME=/home/your-user/.gemini
DISCORD_BOT_TOKEN=
DISCORD_CHANNEL_ID=
```

`DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_ID` are required because `run.sh` posts the generated report summary to Discord after report generation.

## 2. Build

```bash
docker compose build
```

## 3. Run

```bash
docker compose run --rm deep-research
```

The repository is mounted at `/workspace`, so generated files are written back to the host under `agy-market-report/`.

## Scheduled Run

Set the schedule in `.env`:

```env
TZ=Asia/Tokyo
RUN_AT=07:30
RUN_ON_START=0
```

`RUN_AT` uses 24-hour `HH:MM`. Multiple daily runs are supported with commas:

```env
RUN_AT=07:30,18:00
```

Start the scheduler:

```bash
docker compose up -d deep-research-scheduler
```

View logs:

```bash
docker compose logs -f deep-research-scheduler
```

Stop it:

```bash
docker compose down
```

For a smoke test, set `RUN_ON_START=1` temporarily. The scheduler will run `./run.sh` immediately, then continue waiting for the next scheduled time.

## Notes

- The image does not bundle `agy`; it mounts your host `agy` binary at `/usr/local/bin/agy`.
- The `AGY_HOME` directory is mounted to `/home/app/.gemini` so existing `agy` authentication is available in the container.
- If your `agy` setup uses API-key environment variables, add them to `.env`.
