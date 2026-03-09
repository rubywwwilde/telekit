# ExecPlan: Align Telekit Runtime, Configurable Transcription Models, and User Help

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

`PLANS.md` is checked into this repository at `PLANS.md`. This plan must be maintained in accordance with that file.

## Purpose / Big Picture

After this change, Telekit will become installable and understandable for a non-expert user. A user will be able to choose one supported installation path, run `--help` without guessing missing dependencies, understand what the bot can do, understand how to trigger transcription in Telegram, and choose the transcription model through environment variables or command-line flags.

This work also fixes two broken behaviors. First, long-audio handling currently fails in the chunking path because the code sends `pydub` audio segment objects to the OpenAI client instead of real audio files. Second, when a transcript becomes too long for a Telegram message, the bot currently falls back to sending `transcription.txt`; the new behavior must prefer editing or replying in multiple text chunks when possible, and only use a file when the selected output format or Telegram constraints make text impossible.

The end result must be observable in three ways. A local developer can run a documented `uv` workflow and see `telekit --help` output. A Docker operator can build and run the same program using the same configuration keys. A Telegram user can read the README, send or reply to a voice note, and understand exactly what the bot does and how to control it.

## Progress

- [x] (2026-03-07 15:10Z) Completed repo exploration, issue `#3` review, OpenAI speech-to-text surface verification, and server-side deployment spot check.
- [x] (2026-03-07 15:18Z) Confirmed local install drift: `requirements.txt` omits `python-dotenv` and `pydub` while `Dockerfile` installs them separately.
- [x] (2026-03-07 15:23Z) Confirmed model hard-coding to `whisper-1` and verified the current code depends on `verbose_json` segment output.
- [x] (2026-03-07 15:29Z) Confirmed `uv` viability with Python 3.9 and 3.12 after dependency correction; confirmed Python 3.13 is not supported by the current Telethon pin.
- [x] (2026-03-07 15:37Z) Authored this ExecPlan in `docs/exec_plans/active/` so implementation can proceed against a shared spec.
- [x] (2026-03-07 16:42Z) Landed package/runtime alignment, shared settings, local/Docker-safe path handling, and `uv`-managed CLI help coverage.
- [x] (2026-03-07 16:44Z) Landed normalized transcription responses, model selection support, long-audio chunk file export, and Telegram inline chunk delivery.
- [x] (2026-03-07 16:40Z) Rewrote README and `.env.example` around the shipped self-automation workflow, Telegram trigger syntax, and real capability/limitation boundaries.
- [x] (2026-03-07 16:58Z) Fixed post-merge review regressions: process-level `--transcription-model` now reaches `VoiceJob`, singular and plural session-dir env names are both accepted, docs match the active config surface, and build/cache artifacts are ignored.
- [ ] End-to-end validation across local `uv` workflow and Docker workflow remains to be fully run after the final merged tree stabilizes. Local `uv` validation is complete; Docker daemon validation is still limited by host availability.

## Surprises & Discoveries

- Observation: `telekit/AGENTS.md` references `.agents/PLANS.md`, but the actual plan guidance file in this repository is `PLANS.md` at the root.
  Evidence: `AGENTS.md` contains “as described in .agents/PLANS.md”, while `find` returns `telekit/PLANS.md` and `telekit/.agents/` is empty.

- Observation: the documented local path fails before any command help is shown.
  Evidence: running `python3 app.py --help` in the repository currently raises `ModuleNotFoundError: No module named 'dotenv'`.

- Observation: the local and Docker session paths differ, so the README’s non-Docker path is not actually first-class.
  Evidence: `control.py` creates Telethon sessions under `/app/data/sessions/`, which only exists inside the container image.

- Observation: the long-audio path is structurally broken.
  Evidence: `utils.AudioHelper.split_audio()` returns `AudioSegment` objects, while `job_manager.voice_job.VoiceJob.process_job()` passes those objects to `openai.Audio.atranscribe()`, which expects a file-like object with a filename.

- Observation: newer GPT transcription models are supported by the current OpenAI speech-to-text API, but they do not support the same output formats as `whisper-1`.
  Evidence: current OpenAI documentation states `whisper-1` supports `json`, `text`, `srt`, `verbose_json`, and `vtt`, while `gpt-4o-transcribe` and `gpt-4o-mini-transcribe` support `json` or `text`.

- Observation: the current server deployment uses an untracked `docker-compose.yaml` and Docker daemon access is restricted for the current SSH user.
  Evidence: server `git status --short` shows `?? docker-compose.yaml`, and `docker compose ps` fails with `permission denied` on `/var/run/docker.sock`.

- Observation: the first merged implementation left a gap between process-level settings and per-message transcription jobs.
  Evidence: after wiring `start-program --transcription-model`, `load_settings(transcription_model='gpt-4o-mini-transcribe')` reported the chosen model while a default `VoiceJob(..., model=None)` still resolved to `whisper-1` until `IngTranscribeCommand` was updated to read `client_handler.settings.transcription_model`.

- Observation: docs and config drift can reappear quickly when env var names are changed in only one layer.
  Evidence: `.env.example` and `README.md` initially documented `TELEKIT_SESSION_DIR`, while `telekit_config.py` only read `TELEKIT_SESSIONS_DIR`.

## Decision Log

- Decision: treat `PLANS.md` at the repository root as the operative ExecPlan contract for this repository.
  Rationale: `AGENTS.md` points to a non-existent `.agents/PLANS.md`, but the repository already contains a complete root-level `PLANS.md` with the required format and rules.
  Date/Author: 2026-03-07 / Codex

- Decision: make `uv` the recommended local development path, but keep Docker as the recommended operator path for non-technical users.
  Rationale: `uv` reduces environment setup friction for developers and can manage Python versions, but Docker remains the lowest-friction deployment path for operators who do not want to manage local Python packaging.
  Date/Author: 2026-03-07 / Codex

- Decision: declare Python support as `>=3.10,<3.13` unless code and dependencies are upgraded further during implementation.
  Rationale: the current Telethon pin works in Python 3.10 and 3.12 in local checks once dependencies are corrected, but fails on Python 3.13 because `imghdr` has been removed from the standard library.
  Date/Author: 2026-03-07 / Codex

- Decision: preserve `whisper-1` as the default transcription model in the first implementation pass, while adding support for `gpt-4o-transcribe` and `gpt-4o-mini-transcribe`.
  Rationale: the current result parser assumes timestamped `verbose_json` segments, which map naturally to `whisper-1`. The GPT transcription models should be supported, but through a normalized parsing layer rather than a hard swap that breaks current text assembly.
  Date/Author: 2026-03-07 / Codex

- Decision: long transcript delivery should prefer Telegram text, including multi-message chunking, before falling back to a `.txt` file.
  Rationale: a text file is a poor default user experience when the desired result is readable inline. The fallback file path should remain available only for explicit file output mode or unavoidable Telegram/API constraints.
  Date/Author: 2026-03-07 / Codex

- Decision: explicitly document unimplemented features rather than implying they work.
  Rationale: the codebase currently advertises “various output formats” and contains flags like `--summarize` and `--chapters` that are not implemented. Trust improves when unsupported behavior is labeled as planned rather than hidden.
  Date/Author: 2026-03-07 / Codex

- Decision: accept both `TELEKIT_SESSIONS_DIR` and the older singular alias `TELEKIT_SESSION_DIR`, but document the plural form as canonical.
  Rationale: the singular form had already appeared in the merged docs surface and may exist in copied local env files. Supporting both names avoids needless breakage while preserving one preferred config key going forward.
  Date/Author: 2026-03-07 / Codex

## Outcomes & Retrospective

Current outcome snapshot:

- The local developer path is now centered on `uv`, and `uv run telekit --help` works against the merged tree.
- The transcription path now supports configurable selection across `whisper-1`, `gpt-4o-transcribe`, and `gpt-4o-mini-transcribe`, with normalization for model response shape differences.
- Long transcripts stay inline in Telegram through chunked text replies before the program falls back to `transcription.txt`.
- Long-audio chunking now writes real exported chunk files before sending them to OpenAI.
- Post-merge review found and fixed two integration regressions: CLI model propagation into runtime jobs and env-name drift for session directory overrides.

Remaining gaps:

- Docker image validation is structurally updated but still needs a full daemon-backed build/run verification in an environment where Docker is available.
- `IngGPTCommand`, summarization, chapter generation, and real VTT output remain incomplete by design.

## Context and Orientation

Telekit is a small Python project that automates actions in a user’s own Telegram account using Telethon, which is a Python client library for Telegram. The main command-line entrypoint is `app.py`. It defines Typer commands such as `add-client`, `delete-client`, and `start-program`, and it persists configured sessions in `data/clients.json`.

The runtime wiring lives in `control.py`. `ClientFactory.create_client()` creates Telethon clients from the JSON file, and `ClientHandler` registers message handlers for outgoing Telegram messages. In Telekit’s current design, the bot listens only to outgoing messages (`events.NewMessage(incoming=False)`), which means the user triggers behavior from their own account rather than from a separate bot account.

The transcription command lives in `commands/ing_transcribe/ing_transcribe.py`. A “command” in this repository means a class derived from `commands.base.Command` that inspects an event and performs an action. The transcription command triggers automatically for voice messages the user sends and also when the user replies with `@` or `@ingTranscribe` to an existing voice note.

Audio download and transcription work live in `job_manager/voice_job.py`, `job_manager/transcription_result.py`, and `utils.py`. A “job” here means a unit of work that downloads one Telegram voice message, writes temporary files under `jobs/<uuid>/`, and then sends audio to OpenAI’s transcription API. `TranscriptionResult` currently assumes a `verbose_json` response with timestamped `segments`, which is why model support needs to be normalized before alternative models become configurable.

The current packaging and deployment surfaces are inconsistent:

- `requirements.txt` contains only `Typer`, `Telethon`, `cryptg`, and `openai`.
- `Dockerfile` installs `python-dotenv` and `pydub` outside `requirements.txt`.
- `.env.example` includes only `OPENAI_API_KEY`, `API_ID`, and `API_HASH`.
- `README.md` documents basic commands but does not explain triggers, help output, supported Python versions, supported models, or actual capabilities and limitations.

The current server deployment at `192.168.50.120` contains a `telekit` checkout with an untracked `docker-compose.yaml`. That deployment context matters because local and Docker workflows must converge instead of drifting further.

## Plan of Work

### Milestone 1: Make packaging, configuration, and runtime paths consistent

This milestone makes the repository installable and runnable from one declared contract. At the end of this milestone, a novice can clone the repository, create or synchronize a local environment with `uv`, run `--help`, and understand which Python versions are supported.

Add a project packaging file at the repository root. Use `pyproject.toml` as the source of truth for project metadata, Python version constraints, dependencies, and a console script entrypoint named `telekit`. Keep `requirements.txt` only if needed for compatibility, but generate it from the same dependency set or clearly label it as legacy. The dependency set must include `python-dotenv` and `pydub`, and the `cryptg` pin must be updated to a version that installs cleanly in supported Python versions. If `cryptg` is made optional, the plan must document the performance tradeoff and keep runtime behavior correct without it.

Create one configuration module, for example `telekit_config.py` or `config.py`, that loads environment variables and exposes a single authoritative settings object. This module must define and validate:

- Telegram API credentials.
- OpenAI API key.
- Session root directory.
- Jobs directory.
- Default transcription model.
- Default text output mode.
- Optional chunk size or Telegram message splitting controls.

Replace hard-coded `/app/...` paths in `control.py` and any other modules with settings-based paths. The settings must default to repository-local paths such as `data/sessions` and `jobs` for local runs, while Docker can override them through environment variables or volume mounts.

Update the CLI entrypoint in `app.py` so `telekit --help` and `python app.py --help` both work. Keep the existing commands for compatibility, but improve their help text so a novice understands what each one does. Add a top-level help paragraph explaining that Telekit is a Telegram self-automation client and not a separate Telegram bot account.

Update `Dockerfile` so it installs from the same declared dependency source as local development. Remove duplicated ad hoc installs that drift from the main dependency list. Remove the unused exposed port unless a real HTTP surface is introduced during the same change. Ensure the Docker default command still starts the long-running program.

### Milestone 2: Add explicit model selection and normalize transcription responses

This milestone makes the transcription model configurable without breaking current text assembly. At the end of this milestone, the operator can set the model in `.env` or override it through CLI flags, and Telekit can successfully process supported responses from `whisper-1`, `gpt-4o-transcribe`, and `gpt-4o-mini-transcribe`.

Introduce a normalized transcription layer in `job_manager/transcription_result.py` or a new adjacent module. The normalization layer must accept two response families:

- `whisper-1` style verbose responses with `segments`.
- GPT transcription responses that return `json` or `text` content without the same segment structure.

The normalized result object must expose methods used by the rest of the program in plain language, such as `get_plain_text()`, `get_segments()`, and `supports_timestamps()`. If timestamps are unavailable for a model, the result must still produce correct plain text and explicitly report that timestamp-derived formats such as `vtt` are unavailable.

Update `job_manager/voice_job.py` so the model is not hardcoded. Read it from the shared configuration object, allow an override argument from the CLI or command path, and validate it against an allowed set:

- `whisper-1`
- `gpt-4o-transcribe`
- `gpt-4o-mini-transcribe`

When the selected model does not support a requested output mode, fail gracefully with an explanatory Telegram message or CLI error rather than silently producing the wrong format. For example, if `vtt` is requested under `gpt-4o-mini-transcribe`, the program should say that the current model does not support that output and suggest `whisper-1` instead.

Add operator-facing configuration precedence and document it clearly:

1. Command-line flag, such as `telekit start-program --transcription-model gpt-4o-mini-transcribe`.
2. Environment variable, such as `TELEKIT_TRANSCRIPTION_MODEL`.
3. Project default, initially `whisper-1`.

### Milestone 3: Fix long-audio processing and long-text Telegram delivery

This milestone removes the broken large-file path and improves user-visible output when transcripts are long. At the end of this milestone, large recordings can be transcribed successfully, and long transcript output stays inline in Telegram whenever feasible.

Rewrite `utils.AudioHelper.split_audio()` so it returns real temporary audio files or writes chunks to a deterministic temporary directory under the current job directory. A segment file must have a stable extension and filename so OpenAI’s client can send it correctly. The chunking code must clean up or safely overwrite its own artifacts when retried.

Update `job_manager/voice_job.py` so the long-audio branch opens each chunk as a file and passes that file object to the OpenAI client. When combining chunk results, preserve text order and any supported timestamps. If the model supports prompting and previous-context continuation, pass the trailing text from the prior chunk to improve continuity. Keep this behavior optional and documented because prompt support differs by model.

Replace the current “send `transcription.txt` when text length exceeds 4096” default in `control.py`. Introduce a delivery helper that can:

- Edit the original message if the entire transcript fits.
- Edit the original message with the first chunk and send follow-up replies for the remaining chunks when the transcript exceeds Telegram’s message size.
- Send a file only when the user explicitly asks for file output or when the selected output format is file-oriented.

The exact chunk size should leave safety headroom under Telegram’s limit, for example 3500 to 3800 characters per chunk, to account for prefixes and formatting. Preserve the current prepend banner only on the first chunk so the reply thread stays readable.

Ensure this logic works both for automatic transcription of the user’s own voice messages and for reply-triggered transcription of someone else’s voice message.

### Milestone 4: Clarify the product surface, help, and onboarding

This milestone closes the usability gaps raised in issue `#3`. At the end of this milestone, a non-expert can understand prerequisites, installation choices, the Telegram trigger syntax, real capabilities, real limitations, and where model selection lives.

Rewrite `README.md` from the perspective of a novice user. It must contain:

- A clear one-paragraph description of what Telekit is.
- A “What it can do today” section.
- A “What is planned but not implemented yet” section.
- A recommended install path for Docker users.
- A recommended install path for local developers using `uv`.
- A troubleshooting section for missing credentials, missing Python version, and failed Telethon session setup.
- A “How to use in Telegram” section with concrete examples of sending a voice note yourself and replying `@` to someone else’s voice note.
- A section explaining how to show help and inspect command options.

Update `.env.example` with every supported runtime configuration key, including model selection and path overrides. Each variable should include a short comment in the README explaining what it does and when a user should change it.

Add command help text and, if it is low-risk, a small in-chat help surface. For example, allow replying `@ --help` or `@ingTranscribe --help` to get a brief usage message in Telegram. If that is too invasive for the first pass, at minimum the README must explain the in-chat trigger syntax and the CLI help commands clearly.

Audit feature claims against the code. Remove or relabel claims about summarization, chapters, GPT command support, or VTT support if they are not actually implemented. If the placeholder `IngGPTCommand` remains unimplemented, either remove it from the default client command list or clearly mark it as disabled/incomplete.

### Milestone 5: Validate the unified contract across local and Docker workflows

This milestone proves the work is real rather than theoretical. At the end of this milestone, the repository will contain validation evidence showing that the documented commands and behaviors match the code.

Run the local developer path from a clean shell using `uv`. Confirm that `telekit --help`, `telekit add-client --help`, and `telekit start-program --help` work without manually installing undeclared packages.

Run a targeted unit or integration suite that covers:

- Configuration loading and precedence.
- Response normalization for `whisper-1` and GPT transcription result shapes.
- Long-audio chunk file creation and merge behavior.
- Telegram text chunking behavior for oversized transcripts.

Build the Docker image using the updated Dockerfile and confirm that the same configuration variables are honored there. If server-side Docker execution remains inaccessible for the current SSH user, note that limitation explicitly and keep Docker verification local.

Update this ExecPlan’s `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` sections as each milestone completes. The plan itself is part of the delivery artifact.

## Concrete Steps

Run every command from the repository root unless a different directory is specified. Re-run commands freely; the intended commands below are idempotent.

1. Inspect current dependency and runtime behavior before changing code.

    pwd
    python3 app.py --help || true
    uv --version

   Expected current failure before the implementation:

    Traceback (most recent call last):
      ...
    ModuleNotFoundError: No module named 'dotenv'

2. After packaging changes land, verify the local development workflow.

    uv sync
    uv run telekit --help
    uv run telekit add-client --help
    uv run telekit start-program --help

   Expected success shape after the implementation:

    Usage: telekit [OPTIONS] COMMAND [ARGS]...
    ...
    Commands:
      add-client
      delete-client
      start-program

3. Run the automated test suite added for this plan.

    uv run pytest

   If the repository uses another command for tests by the time implementation is complete, replace this step in the plan with the exact command used in the codebase and keep the expected output updated.

4. Validate the long-text delivery helper with unit tests and, if available, a small fake client test.

    uv run pytest -k "telegram or transcription or config"

5. Validate Docker packaging.

    docker build -t telekit:execplan .

   If Docker is unavailable locally, document the limitation in this plan and record the exact error.

6. Validate README instructions manually against the actual commands.

    uv run telekit --help
    uv run telekit add-client demo_session

7. Optionally validate the server filesystem layout through SSH without requiring Docker daemon access.

    /Users/ivan/.codex/skills/00-ssh-proxmox-vm-access/scripts/ssh_run.sh -- 'cd telekit && git status --short && ls -la'

## Validation and Acceptance

This plan is accepted only when all of the following behaviors are true and demonstrated:

1. A clean local environment can install and run Telekit help output without undocumented dependency fixes.
2. The repository clearly states which Python versions are supported, and the local workflow reflects that contract.
3. The transcription model can be selected through environment variables and overridden through a CLI flag.
4. `whisper-1`, `gpt-4o-transcribe`, and `gpt-4o-mini-transcribe` are supported as selectable models, with graceful errors for unsupported output modes.
5. Audio larger than the old single-file threshold is processed through real chunk files and produces a combined transcript.
6. Oversized transcripts remain readable inline in Telegram by splitting across edited or reply messages before falling back to `transcription.txt`.
7. The README explains real capabilities, real limitations, installation, help commands, and Telegram trigger syntax.
8. Placeholder or misleading feature claims are removed or explicitly marked as not implemented.
9. Docker and local runtime surfaces use the same configuration names and the same dependency contract.

## Idempotence and Recovery

All path and packaging changes in this plan should be additive and repeatable. Running `uv sync` repeatedly must converge on the same environment. Running the CLI help commands repeatedly must not mutate runtime state. Creating local directories such as `data/sessions` or `jobs` must be safe if they already exist.

If the packaging migration introduces breakage, keep a compatibility entrypoint so `python app.py ...` still works while `telekit ...` is introduced. If a dependency upgrade causes an unexpected runtime regression, revert only the dependency pin and keep the rest of the packaging structure intact so the repository does not lose the new unified contract.

If Docker validation cannot be completed because of daemon permissions on the remote host, note the failure in this plan and perform the image build locally. Do not change the remote server deployment as part of this plan unless separately requested.

## Artifacts and Notes

Important current evidence captured during planning:

    python3 app.py --help
    Traceback (most recent call last):
      ...
    ModuleNotFoundError: No module named 'dotenv'

    uv run --python 3.13 ... python app.py --help
    ...
    ModuleNotFoundError: No module named 'imghdr'

Key current file references:

- `app.py` defines the Typer CLI and default client command registration.
- `control.py` registers Telethon handlers and currently hardcodes `/app/data/sessions/`.
- `commands/ing_transcribe/ing_transcribe.py` defines the Telegram trigger syntax and text/file output behavior.
- `job_manager/voice_job.py` hardcodes `whisper-1` and contains the broken long-audio path.
- `job_manager/transcription_result.py` assumes `verbose_json` segment output.
- `utils.py` defines audio conversion and splitting helpers.
- `README.md`, `.env.example`, and `Dockerfile` define the current user-facing operator surface.

Parallel implementation ownership for asynchronous workers:

- Worker A owns packaging/runtime alignment and CLI contract. Files: `pyproject.toml`, `requirements.txt`, `app.py`, `control.py`, `Dockerfile`, new config module, and related tests.
- Worker B owns transcription engine normalization, configurable models, long-audio chunking, and long-text Telegram delivery. Files: `job_manager/voice_job.py`, `job_manager/transcription_result.py`, `utils.py`, `commands/ing_transcribe/ing_transcribe.py`, `control.py` delivery helpers, and related tests.
- Worker C owns user-facing docs and capability/help clarity. Files: `README.md`, `.env.example`, any additional docs, and any small help-surface edits that do not conflict with Worker A or B ownership.

The integrating agent owns this ExecPlan file, final conflict resolution, and final verification.

## Interfaces and Dependencies

The implementation must end with these stable interfaces or equivalent names that are documented in code and README:

In the shared configuration module, define a single settings object or dataclass that exposes:

    telegram_api_id: str
    telegram_api_hash: str
    openai_api_key: str
    session_dir: Path
    jobs_dir: Path
    transcription_model: str
    transcript_delivery_mode: str

In `job_manager/transcription_result.py`, define a normalized result type that can represent both timestamped and plain-text responses. The result type must expose methods equivalent to:

    get_plain_text() -> str
    get_segments() -> list
    supports_timestamps() -> bool

In `job_manager/voice_job.py`, define a transcription entrypoint that accepts model selection through configuration or an explicit argument rather than a hardcoded string.

In the Telegram delivery path, define one helper that takes a peer ID, transcript text, reply target, and mode, and decides whether to edit, reply in multiple chunks, or send a file.

Revision note (2026-03-07): Initial ExecPlan created to convert the earlier recommendation set into a repository-native implementation spec with explicit milestones, validation, worker ownership, and the additional long-transcript delivery fix requested after planning.
