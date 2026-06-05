# Container Usage

This project can run inside Docker while reusing the host Antigravity CLI (`agy`) and
OpenCode binaries plus their existing authentication/config.

## Prerequisite: Host CLIs

Install and authenticate the host CLI you plan to use first. The Docker image does not
bundle `agy` or `opencode`; it mounts the host commands into the container.

Verify that `agy` works locally:

```bash
command -v agy
agy --version
```

If `agy` is not found, install Antigravity CLI and complete its login/authentication flow
before using this container setup.

Verify that `opencode` works locally when using `AGENT_BACKEND=opencode`:

```bash
command -v opencode
opencode --version
opencode auth list
```

## 1. Create `.env`

```bash
cp .env.example .env
```

Edit `.env`:

```env
AGY_BIN=/home/your-user/.local/bin/agy
AGY_HOME=/home/your-user/.gemini
OPENCODE_BIN=/home/your-user/.npm-global/lib/node_modules/opencode-ai/bin/opencode.exe
DISCORD_BOT_TOKEN=
DISCORD_CHANNEL_ID=
```

`AGY_BIN` is the full host path to the `agy` executable. Use this to find it:

```bash
command -v agy
```

Example:

```env
AGY_BIN=/home/your-user/.local/bin/agy
```

`OPENCODE_BIN` is the full host path to the OpenCode executable. Prefer the resolved
binary path rather than an npm symlink:

```bash
readlink -f "$(command -v opencode)"
```

`AGY_HOME` is the host directory containing Antigravity CLI authentication/config. In a
standard setup this is usually:

```env
AGY_HOME=/home/your-user/.gemini
```

`DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_ID` are required because `run.sh` posts the generated report summary to Discord after report generation.

## Agent Backend

The container uses the same backend switch as local runs:

```env
AGENT_BACKEND=agy
```

To use OpenCode instead:

```env
AGENT_BACKEND=opencode
OPENCODE_COMMAND=opencode
OPENCODE_MODEL=openai/gpt-5.4-mini
OPENCODE_AGENT=market-reporter
OPENCODE_RUN_ARGS=
OPENCODE_CONFIG=
OPENCODE_CONFIG_DIR=
```

The host OpenCode binary is mounted to `/usr/local/bin/opencode`. Make sure provider
credentials are available through environment variables or OpenCode's config/auth files.
The host `agy` command is still mounted because OpenCode routes web search through the
local `agy` wrapper.

Docker also mounts the standard OpenCode directories:

```text
~/.config/opencode
~/.local/share/opencode
~/.local/state/opencode
~/.cache/opencode
```

When `OPENCODE_CONFIG` and `OPENCODE_CONFIG_DIR` are blank, `run.sh` uses the repository
local `opencode.json` and `.opencode/` directory.

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
- The image does not bundle `opencode`; it mounts your host OpenCode binary at `/usr/local/bin/opencode`.
- The `AGY_HOME` directory is mounted to `/home/app/.gemini` so existing `agy` authentication is available in the container.
- If your `agy` setup uses API-key environment variables, add them to `.env`.
