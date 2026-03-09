# Telekit Agent Guide

This repository ships a Telegram self-automation client that runs either locally with `uv` or in Docker with `docker compose`. Keep changes small, testable, and aligned with the real operator workflow.

## Working Agreement

- Use `uv` for local Python commands.
- Prefer repo-relative runtime paths under `data/` and `jobs/`.
- Never commit `.env`, session files, generated job artifacts, or other private Telegram/OpenAI data.
- Treat `PLANS.md` as the contract for any substantial feature, refactor, or multi-step recovery. Execution plans live under `docs/exec_plans/active/`.

## Project Orientation

- `app.py` defines the Typer CLI and process entrypoints.
- `telekit_config.py` resolves environment variables and runtime paths.
- `control.py` owns Telethon client startup, command routing, and transcript delivery.
- `commands/ing_transcribe/ing_transcribe.py` is the active user-facing Telegram command.
- `job_manager/voice_job.py` and `job_manager/transcription_result.py` implement transcription behavior.
- `docker-compose.yml` and `Dockerfile` define the container workflow.

## Useful Commands

Run these from the repository root.

- `uv sync`
- `uv run telekit --help`
- `uv run telekit start-program --help`
- `uv run pytest -v`
- `docker compose build`
- `docker compose up -d`
- `docker compose logs --tail=200`
- `docker compose down`

## Change Discipline

- If a change affects user setup, update `README.md` and `.env.example` in the same pass.
- If a change affects runtime behavior, add or update tests in `tests/`.
- If Docker behavior changes, validate with `docker compose` before closing the task.
- If long-running or risky work is involved, create or update the active ExecPlan before implementation.
