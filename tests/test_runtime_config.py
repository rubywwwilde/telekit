from __future__ import annotations

from pathlib import Path

from telekit_config import ensure_runtime_paths, load_settings, validate_startup_settings
from control import ClientFactory


class DummyTelegramClient:
    def __init__(self, session_path, api_id, api_hash):
        self.session_path = session_path
        self.api_id = api_id
        self.api_hash = api_hash
        self.parse_mode = None


def test_load_settings_uses_local_relative_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TELEKIT_DATA_DIR", raising=False)
    monkeypatch.delenv("TELEKIT_CLIENTS_FILE", raising=False)
    monkeypatch.delenv("TELEKIT_SESSIONS_DIR", raising=False)
    monkeypatch.delenv("TELEKIT_SESSION_DIR", raising=False)
    monkeypatch.delenv("TELEKIT_JOBS_DIR", raising=False)
    monkeypatch.delenv("TELEKIT_TRANSCRIPTION_MODEL", raising=False)

    settings = load_settings()

    assert settings.data_dir == (tmp_path / "data").resolve()
    assert settings.clients_file == (tmp_path / "data" / "clients.json").resolve()
    assert settings.sessions_dir == (tmp_path / "data" / "sessions").resolve()
    assert settings.jobs_dir == (tmp_path / "jobs").resolve()


def test_ensure_runtime_paths_creates_expected_directories(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = load_settings()

    ensure_runtime_paths(settings)

    assert settings.data_dir.is_dir()
    assert settings.sessions_dir.is_dir()
    assert settings.jobs_dir.is_dir()
    assert settings.clients_file.exists()
    assert settings.clients_file.read_text(encoding="utf-8").strip() == "[]"


def test_load_settings_accepts_singular_session_dir_env_alias(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TELEKIT_SESSIONS_DIR", raising=False)
    monkeypatch.setenv("TELEKIT_SESSION_DIR", "./custom-sessions")

    settings = load_settings()

    assert settings.sessions_dir == (tmp_path / "custom-sessions").resolve()


def test_validate_startup_settings_reports_missing_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("API_ID", raising=False)
    monkeypatch.delenv("API_HASH", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("TELEKIT_TRANSCRIPTION_MODEL", raising=False)

    errors = validate_startup_settings(load_settings())

    assert errors == ["API_ID", "API_HASH", "OPENAI_API_KEY"]


def test_client_factory_uses_configured_sessions_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("API_ID", "123")
    monkeypatch.setenv("API_HASH", "hash")
    monkeypatch.setattr("control.TelegramClient", DummyTelegramClient)

    settings = load_settings()
    handler = ClientFactory.create_client(
        {"session_name": "demo", "commands": ["IngGPTCommand"]},
        settings=settings,
    )

    assert handler.client.session_path == str((tmp_path / "data" / "sessions" / "demo.session").resolve())
    assert handler.client.api_id == "123"
    assert handler.client.api_hash == "hash"


def test_client_factory_rejects_invalid_session_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("API_ID", "123")
    monkeypatch.setenv("API_HASH", "hash")

    try:
        ClientFactory.create_client(
            {"session_name": "../escape", "commands": ["IngGPTCommand"]},
            settings=load_settings(),
        )
    except ValueError as exc:
        assert "Invalid session name" in str(exc)
    else:
        raise AssertionError("Expected invalid session name to be rejected")


def test_client_factory_rejects_unknown_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("API_ID", "123")
    monkeypatch.setenv("API_HASH", "hash")

    try:
        ClientFactory.create_client(
            {"session_name": "demo", "commands": ["NopeCommand"]},
            settings=load_settings(),
        )
    except ValueError as exc:
        assert "Unknown command" in str(exc)
    else:
        raise AssertionError("Expected unknown commands to be rejected")
