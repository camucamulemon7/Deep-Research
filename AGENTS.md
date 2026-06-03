# AGENTS.md

This file is for every coding agent that works in this repository, regardless of the
runner. Keep runner-specific behavior in that runner's own configuration.

## What Goes Here

- Repository purpose, layout, and entrypoints.
- Backend-neutral workflow rules.
- Output contracts that all agents must preserve.
- Safety rules for generated reports, credentials, and local artifacts.
- Pointers to runner-specific config files.

## What Does Not Go Here

- OpenCode-only prompts, permissions, or tool routing.
- Model-specific tuning such as temperature.
- Detailed instructions for how OpenCode should call tools.
- Long report-generation prompts. Keep those in `prompt_*.md`.

## Project Purpose

This repository automates Japanese morning market reports for Discord posting.

## Workflow

- The main entrypoint is `./run.sh`.
- Generated reports go under `agy-market-report/YYYY-MM-DD/report/`.
- `prompt_market_research.md` is the base report-generation prompt.
- `prompt_improvement_points.md` reviews the previous report and writes the next improved prompt.
- Use `SKIP_DISCORD_POST=1` for smoke tests or dry verification runs.

## Backend Selection

- `AGENT_BACKEND=agy` uses Antigravity CLI directly.
- `AGENT_BACKEND=opencode` uses OpenCode.
- OpenCode project config lives in `opencode.json`.
- OpenCode project agents live under `.opencode/agents/`.
- The default OpenCode report agent is `market-reporter`.
- The default OpenCode model is `openai/gpt-5.4-mini`.

## Output Contract

- The report phase must write `morning_market_report.md`.
- The report phase must write `market_score.json`.
- The review phase must write `prompt_improvement.md`.
- Preserve these filenames because `run.sh` validates them.
- Generated reports should be self-contained enough for Discord summary posting.

## Market Data Rules

- Do not fabricate market data, consensus values, prices, dates, or source details.
- If data cannot be verified, write it as unavailable in Japanese.
- Include traceable source notes in generated reports.
- Keep generated prose in Japanese unless a prompt explicitly requests otherwise.

## Safety Rules

- Do not commit `.env`, generated reports, credentials, or local tool caches.
- Keep changes scoped to this automation workflow.
- During report generation, edit only files in the current report working directory.
- Do not modify repository root scripts, prompts, docs, or config files while generating a report.
