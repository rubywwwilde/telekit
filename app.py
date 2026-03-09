from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO)

import typer
from control import ClientFactory
from telekit_config import (
    DEFAULT_COMMANDS,
    SUPPORTED_TRANSCRIPTION_MODELS,
    ensure_runtime_paths,
    load_settings,
    validate_session_name,
    validate_startup_settings,
)

app = typer.Typer(
    help=(
        "Telekit is a Telegram self-automation client. It runs under your own "
        "Telegram account, watches outgoing messages, and can transcribe voice "
        "notes using the configured OpenAI transcription model."
    ),
    no_args_is_help=True,
)


def load_client_data(*, root_dir: Path | None = None) -> tuple[list[dict], object]:
    settings = load_settings(root_dir=root_dir)
    ensure_runtime_paths(settings)
    with settings.clients_file.open("r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Malformed client registry: {settings.clients_file}. "
                "Fix or replace the file before continuing."
            ) from exc
    if not isinstance(data, list):
        raise ValueError(
            f"Malformed client registry: {settings.clients_file}. "
            "Expected a JSON list of client definitions."
        )
    return data, settings


def save_client_data(client_data: list[dict], *, settings) -> None:
    with settings.clients_file.open("w", encoding="utf-8") as handle:
        json.dump(client_data, handle, indent=4)


def default_client_config(session: str) -> dict:
    return {
        "session_name": session,
        "commands": list(DEFAULT_COMMANDS),
    }


@app.command()
def add_client(session: str):
    """
    Register a Telegram session name inside data/clients.json.
    """
    client_data, settings = load_client_data()
    session = validate_session_name(session)
    if any(client.get("session_name") == session for client in client_data):
        typer.echo(f"Session '{session}' is already registered.", err=True)
        raise typer.Exit(code=2)
    new_client = default_client_config(session)
    client_data.append(new_client)
    save_client_data(client_data, settings=settings)
    print(f"Added new client with session name: {session}")


@app.command()
def delete_client():
    """Remove a previously registered Telegram session."""
    client_data, settings = load_client_data()
    print("Here are the available clients:")
    for index, client in enumerate(client_data, start=1):
        print(f"{index}. {client['session_name']}")

    session = typer.prompt("Please enter the session name of the client you want to delete")
    client_data[:] = [client for client in client_data if client.get("session_name") != session]
    save_client_data(client_data, settings=settings)
    print(f"Deleted client with session name: {session}")


@app.command()
def start_program(
    transcription_model: Optional[str] = typer.Option(
        None,
        "--transcription-model",
        help=(
            "Default transcription model for this process. Supported values: "
            + ", ".join(SUPPORTED_TRANSCRIPTION_MODELS)
        ),
    ),
):
    """
    Start the long-running Telethon client process.
    """
    settings = load_settings(transcription_model=transcription_model)
    ensure_runtime_paths(settings)
    validation_errors = validate_startup_settings(settings)
    if validation_errors:
        for error in validation_errors:
            typer.echo(f"Configuration error: {error}", err=True)
        raise typer.Exit(code=2)

    try:
        asyncio.run(main(settings))
    except KeyboardInterrupt:
        typer.echo("Telekit stopped.")


async def main(settings) -> None:
    client_data, _ = load_client_data(root_dir=settings.root_dir)
    for config in client_data:
        client = ClientFactory.create_client(config, settings=settings)
        await client.start()
    print("bot started")
    await do_nothing()


async def do_nothing():
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    app()
