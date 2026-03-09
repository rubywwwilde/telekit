from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re

from dotenv import load_dotenv

load_dotenv()

DEFAULT_COMMANDS = ("IngTranscribeCommand", "IngGPTCommand")
SUPPORTED_TRANSCRIPTION_MODELS = (
    "whisper-1",
    "gpt-4o-transcribe",
    "gpt-4o-mini-transcribe",
)
SESSION_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    data_dir: Path
    clients_file: Path
    sessions_dir: Path
    jobs_dir: Path
    api_id: str | None
    api_hash: str | None
    openai_api_key: str | None
    transcription_model: str


def load_settings(
    *,
    root_dir: Path | None = None,
    data_dir: Path | None = None,
    clients_file: Path | None = None,
    sessions_dir: Path | None = None,
    jobs_dir: Path | None = None,
    transcription_model: str | None = None,
) -> Settings:
    root = (root_dir or Path.cwd()).resolve()
    configured_data_dir = _resolve_path(
        data_dir or os.getenv("TELEKIT_DATA_DIR") or "data",
        root,
    )
    configured_clients_file = _resolve_path(
        clients_file or os.getenv("TELEKIT_CLIENTS_FILE") or configured_data_dir / "clients.json",
        root,
    )
    configured_sessions_dir = _resolve_path(
        sessions_dir
        or os.getenv("TELEKIT_SESSIONS_DIR")
        or os.getenv("TELEKIT_SESSION_DIR")
        or configured_data_dir / "sessions",
        root,
    )
    configured_jobs_dir = _resolve_path(
        jobs_dir or os.getenv("TELEKIT_JOBS_DIR") or "jobs",
        root,
    )
    selected_model = transcription_model or os.getenv("TELEKIT_TRANSCRIPTION_MODEL") or "whisper-1"

    return Settings(
        root_dir=root,
        data_dir=configured_data_dir,
        clients_file=configured_clients_file,
        sessions_dir=configured_sessions_dir,
        jobs_dir=configured_jobs_dir,
        api_id=os.getenv("API_ID"),
        api_hash=os.getenv("API_HASH"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        transcription_model=selected_model,
    )


def ensure_runtime_paths(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)
    settings.jobs_dir.mkdir(parents=True, exist_ok=True)
    settings.clients_file.parent.mkdir(parents=True, exist_ok=True)
    if not settings.clients_file.exists():
        settings.clients_file.write_text("[]\n", encoding="utf-8")


def validate_startup_settings(settings: Settings) -> list[str]:
    missing = []
    if not settings.api_id:
        missing.append("API_ID")
    if not settings.api_hash:
        missing.append("API_HASH")
    if not settings.openai_api_key:
        missing.append("OPENAI_API_KEY")
    if settings.transcription_model not in SUPPORTED_TRANSCRIPTION_MODELS:
        missing.append(
            "TELEKIT_TRANSCRIPTION_MODEL must be one of: "
            + ", ".join(SUPPORTED_TRANSCRIPTION_MODELS)
        )
    return missing


def validate_session_name(session_name: str | None) -> str:
    if not session_name:
        raise ValueError("Session name cannot be empty.")
    if Path(session_name).name != session_name or Path(session_name).is_absolute():
        raise ValueError(f"Invalid session name: {session_name!r}")
    if not SESSION_NAME_PATTERN.fullmatch(session_name):
        raise ValueError(
            "Invalid session name: "
            f"{session_name!r}. Use only letters, numbers, hyphens, and underscores."
        )
    return session_name


def _resolve_path(value: str | Path, root_dir: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root_dir / path
    return path.resolve()
