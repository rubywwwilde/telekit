# Telekit

Telekit is a Telegram self-automation client built with Telethon. It signs into your own Telegram account, watches your outgoing messages, and transcribes voice notes with OpenAI speech-to-text models.

This is not a Telegram bot account with a `/start` command or a web app. Telekit runs as your own Telegram client session.

## What Telekit Can Do Today

- Automatically transcribe voice messages that you send from your own Telegram account.
- Transcribe someone else's voice message when you reply to it with `@` or `@ingTranscribe`.
- Return the result as inline text or as a text file, depending on the command flags and Telegram message limits.
- Run multiple Telegram sessions from one Telekit install.

## What Is Planned or In Progress

- Real VTT output instead of the current plain-text fallback.
- Real summarization and chapter generation for reply-trigger mode.
- A real GPT command surface to replace the current stub.
- Migration from the legacy OpenAI Python client to the current SDK.

## Current Limitations

- `IngGPTCommand` exists in the codebase but is not implemented yet.
- `--summarize` and `--chapters` flags are parsed by the transcription command but do not currently change behavior.
- `--format vtt` is not fully implemented. The current code falls back to sending a text file.
- The current code listens to outgoing messages only. That is intentional for a self-automation client, but it means Telekit does not act like a separate Telegram bot account.
- Python 3.13 is not supported by the current Telethon stack used in this repository. Use Python 3.10 through 3.12.

## Quick Start

Choose one installation path:

- Docker operator path: best if you want the simplest deployment and do not want to manage Python directly.
- Local developer path: best if you want to work on the code, inspect logs, or run Telekit without Docker.

## Prerequisites

You need all of the following regardless of installation path:

- A Telegram account.
- A Telegram API ID and API hash from <https://core.telegram.org/api/obtaining_api_id>.
- An OpenAI API key.

You should also know that Telekit stores Telegram session files on disk. Those files let Telekit sign back into your account without asking for login information every time.

## Beginner Setup

If you do not already have a Python development environment, start here before running any Telekit commands.

### Windows

1. Install Python 3.12 from <https://www.python.org/downloads/windows/> and make sure the installer option to add Python to `PATH` is enabled.
2. Install Git from <https://git-scm.com/download/win> if you want to clone the repository. If not, download the project ZIP from GitHub and extract it.
3. Open `PowerShell` in the Telekit folder.

### macOS

1. Install Python 3.12 from <https://www.python.org/downloads/macos/> or with Homebrew.
2. Install Git with Xcode Command Line Tools: `xcode-select --install`, or download the project ZIP from GitHub if you do not want to use Git.
3. Open `Terminal` in the Telekit folder.

### Linux

1. Install Python 3.12 and Git with your package manager, or download the project ZIP from GitHub and extract it manually.
2. Open your terminal in the Telekit folder.

### If you do not want to use Git

You can still run Telekit:

1. Open the GitHub repository page.
2. Download the project as a ZIP archive.
3. Extract it to a folder you control.
4. Open a terminal in that extracted folder before running the commands below.

## Configuration

Copy the example file first:

```bash
cp .env.example .env
```

On Windows PowerShell, use:

```powershell
Copy-Item .env.example .env
```

Then fill in the required values:

- `OPENAI_API_KEY`: your OpenAI API key.
- `API_ID`: your Telegram API ID.
- `API_HASH`: your Telegram API hash.

The current runtime also supports these optional settings:

- `TELEKIT_TRANSCRIPTION_MODEL`: default transcription model. Supported values are `whisper-1`, `gpt-4o-transcribe`, and `gpt-4o-mini-transcribe`.
- `TELEKIT_DATA_DIR`: override the base runtime data directory.
- `TELEKIT_CLIENTS_FILE`: override the path to `clients.json`.
- `TELEKIT_SESSIONS_DIR`: override where Telegram session files are stored.
- `TELEKIT_JOBS_DIR`: override where temporary audio job files are stored.

For compatibility, Telekit also accepts the older singular alias `TELEKIT_SESSION_DIR`, but `TELEKIT_SESSIONS_DIR` is the preferred name.

If you do not need to change model or path behavior, leave the `TELEKIT_*` values at their defaults.

### Safe `.env` editing

- Edit `.env` with a plain text editor such as VS Code, TextEdit in plain-text mode, Notepad, or nano.
- Do not commit `.env` to Git. It contains secrets.
- Keep the values on one line each in `KEY=value` format.
- If you copy the file to a server, restrict access to the account that runs Telekit.

## Local Developer Workflow

The supported local flow is:

```bash
uv sync
uv run telekit --help
```

If `uv` is not installed yet, install it first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows, see <https://docs.astral.sh/uv/getting-started/installation/>.

The legacy entrypoint still works inside the synced environment:

```bash
python app.py --help
python app.py add-client my_session
python app.py start-program
```

If you are contributing to the codebase, prefer the `uv` path. `python app.py ...` is kept as a compatibility entrypoint, but it still depends on having the project environment installed first.

## Docker Operator Workflow

Build the image:

```bash
docker build -t telekit .
```

Run the container with your `.env` file and persistent session storage:

```bash
docker run -d \
  --env-file .env \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/data/sessions:/app/data/sessions" \
  --name telekit \
  telekit
```

Create a Telegram session inside the container:

```bash
docker exec -it telekit python /app/app.py add-client my_session
docker exec -it telekit python /app/app.py start-program
```

During the first login, Telekit will ask for Telegram authentication details in the terminal. After the session file is created, Telekit can reuse it on later starts.

Note: Telekit does not currently expose an HTTP interface. If you see old examples with published ports, treat those as legacy deployment leftovers rather than a required part of setup.

## Beginner Troubleshooting

- `uv: command not found`
  Install `uv` first, then restart your shell.
- `python: command not found` or `python3: command not found`
  Python is not installed correctly or is not on your shell `PATH`. Reinstall Python 3.10 through 3.12 and reopen the terminal.
- `Configuration error: API_ID`
  Your `.env` file is missing one or more required credentials.
- Telekit asks for phone and login code every time
  Your session file was not saved in `data/sessions`, or the session is not authorized yet.
- `ModuleNotFoundError`
  You likely skipped `uv sync` or are using `python app.py ...` outside the project environment.

## CLI Help

Once dependencies are installed, you can see the available commands with:

```bash
python app.py --help
python app.py add-client --help
python app.py delete-client --help
python app.py start-program --help
```

The packaged console script is:

```bash
telekit --help
telekit add-client --help
telekit delete-client --help
telekit start-program --help
```

## How To Use Telekit In Telegram

Telekit responds to actions from your own Telegram account.

### 1. Automatic transcription of your own voice notes

Send a voice note from the Telegram account that Telekit is signed into. Telekit will detect that outgoing voice message and replace it with a transcription result.

### 2. Transcribe someone else's voice note

Reply to the voice note with one of these triggers:

- `@`
- `@ingTranscribe`

Example:

```text
@
```

or

```text
@ingTranscribe
```

Telekit will fetch the replied-to voice note and send back the transcript.

## Transcription Flags

The current transcription command recognizes these flags in reply-trigger mode:

- `-f`, `--format`: choose output format. Today the practical values are `text` and `file`.
- `-m`, `--model`: override the transcription model for this command. Supported values are `whisper-1`, `gpt-4o-transcribe`, and `gpt-4o-mini-transcribe`.
- `-n`, `--new`: send a new reply instead of editing the existing target when possible.
- `-e`, `--existing`: prefer editing the existing target when possible.
- `-s`, `--summarize`: accepted by the parser, but not implemented yet.
- `-c`, `--chapters`: accepted by the parser, but not implemented yet.

Example:

```text
@ --format file
```

Example with the long form:

```text
@ingTranscribe --format text
```

Important behavior notes:

- If the transcript is small enough, Telekit tries to return text inline.
- If the transcript is too large for one Telegram message, Telekit now splits it across multiple inline messages before falling back to `transcription.txt`.
- For voice messages with media captions, Telekit edits the original caption to a short continuation notice and posts the full transcript as text replies when necessary.

## Model Selection

Telekit supports these transcription models today:

- `whisper-1`
- `gpt-4o-transcribe`
- `gpt-4o-mini-transcribe`

The default is `whisper-1`. You can change it in either of these ways:

- environment variable: `TELEKIT_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe`
- process flag: `telekit start-program --transcription-model gpt-4o-transcribe`
- reply-trigger override: `@ --model gpt-4o-mini-transcribe`

The reason model selection needs validation instead of a simple string swap is that model outputs differ:

- `whisper-1` supports timestamp-oriented outputs such as `verbose_json`, `srt`, and `vtt`.
- The GPT transcription models use plain `json` or `text` style responses rather than Whisper timestamp segments.

Telekit normalizes those response shapes internally. If you choose a model that does not support a requested output format, Telekit replies with a plain-language fallback message instead of silently doing the wrong thing.

## Capability Summary

Implemented now:

- automatic transcription of your own outgoing voice messages
- reply-based transcription with `@` or `@ingTranscribe`
- multiple client sessions
- inline text output when short enough
- inline chunked text output when transcripts exceed a single Telegram message
- long-audio chunking through temporary exported audio files
- configurable model selection through env, process flags, and reply-trigger flags
- text-file fallback when needed

Not implemented yet or incomplete:

- GPT assistant command behavior
- real summarization mode
- real chapter generation
- fully supported VTT output

## Troubleshooting

### `python app.py --help` fails before it prints help

This usually means you are using the system interpreter without the project environment installed. The supported local path is:

```bash
uv sync
uv run telekit --help
```

### Telekit asks for Telegram login every time

That usually means your session directory is not being persisted. Make sure the session files are stored in a persistent `data/sessions` directory or the container volume that maps to it.

### A long transcript becomes `transcription.txt`

That now happens only when you explicitly ask for file output or when Telegram/API constraints still prevent usable inline text. Normal long transcripts should be split into multiple inline messages first.

### You expected Telekit to behave like a separate bot

Telekit is a self-automation client, not a standalone Telegram bot account. It reacts to your own account session.

## Development Notes

Important files if you are working on Telekit itself:

- `app.py`: Typer CLI entrypoint.
- `control.py`: Telethon client setup and Telegram message sending/editing behavior.
- `commands/ing_transcribe/ing_transcribe.py`: Telegram transcription trigger and flags.
- `job_manager/voice_job.py`: audio transcription workflow.
- `job_manager/transcription_result.py`: transcript result parsing.
- `utils.py`: audio conversion and audio splitting helpers.

The current implementation roadmap is tracked in:

- `docs/exec_plans/active/2026-03-07-telekit-runtime-transcription-execplan.md`

## Contributing

Pull requests are welcome. If you plan to work on runtime, model support, or packaging changes, read the active ExecPlan first so your changes stay aligned with the repository migration now in progress.
