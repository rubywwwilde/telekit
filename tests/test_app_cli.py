from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from app import app, load_client_data


runner = CliRunner()


def test_add_client_creates_local_client_registry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TELEKIT_DATA_DIR", raising=False)
    monkeypatch.delenv("TELEKIT_CLIENTS_FILE", raising=False)
    monkeypatch.delenv("TELEKIT_SESSIONS_DIR", raising=False)
    monkeypatch.delenv("TELEKIT_SESSION_DIR", raising=False)
    monkeypatch.delenv("TELEKIT_JOBS_DIR", raising=False)

    result = runner.invoke(app, ["add-client", "demo-session"])

    assert result.exit_code == 0
    clients_path = tmp_path / "data" / "clients.json"
    assert clients_path.exists()
    assert json.loads(clients_path.read_text(encoding="utf-8")) == [
        {
            "session_name": "demo-session",
            "commands": ["IngTranscribeCommand", "IngGPTCommand"],
        }
    ]


def test_add_client_rejects_duplicate_session(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TELEKIT_DATA_DIR", raising=False)
    monkeypatch.delenv("TELEKIT_CLIENTS_FILE", raising=False)
    monkeypatch.delenv("TELEKIT_SESSIONS_DIR", raising=False)
    monkeypatch.delenv("TELEKIT_SESSION_DIR", raising=False)
    monkeypatch.delenv("TELEKIT_JOBS_DIR", raising=False)

    assert runner.invoke(app, ["add-client", "demo-session"]).exit_code == 0
    result = runner.invoke(app, ["add-client", "demo-session"])

    assert result.exit_code == 2
    assert "already registered" in result.stderr


def test_load_client_data_rejects_malformed_registry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TELEKIT_DATA_DIR", raising=False)
    monkeypatch.delenv("TELEKIT_CLIENTS_FILE", raising=False)
    monkeypatch.delenv("TELEKIT_SESSIONS_DIR", raising=False)
    monkeypatch.delenv("TELEKIT_SESSION_DIR", raising=False)
    monkeypatch.delenv("TELEKIT_JOBS_DIR", raising=False)
    clients_path = tmp_path / "data" / "clients.json"
    clients_path.parent.mkdir(parents=True, exist_ok=True)
    clients_path.write_text("{not valid json", encoding="utf-8")

    try:
        load_client_data(root_dir=tmp_path)
    except ValueError as exc:
        assert "Malformed client registry" in str(exc)
    else:
        raise AssertionError("Expected load_client_data to raise ValueError for malformed JSON")


def test_help_explains_cli_surface():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Telekit is a Telegram self-automation client" in result.stdout
    assert "start-program" in result.stdout


def test_start_program_help_mentions_transcription_model():
    result = runner.invoke(app, ["start-program", "--help"])

    assert result.exit_code == 0
    assert "--transcription-model" in result.stdout
    assert "gpt-4o-mini-" in result.stdout
    assert "transcribe" in result.stdout
