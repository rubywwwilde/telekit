# this bot is inteded to transcribe all voice and video messages sent by user, using telethon
import json
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')


import logging

logging.basicConfig(level=logging.INFO)

from commands import IngTranscribeCommand, IngGPTCommand, ExportChatCommand

from control import ClientHandler, ClientFactory
import typer

app = typer.Typer()

# Ensure the 'data' directory exists
data_dir = 'data'
os.makedirs(data_dir, exist_ok=True)
clients_file_path = os.path.join(data_dir, 'clients.json') # path/to/clients.json

if not os.path.exists(clients_file_path):
    with open(clients_file_path, 'w') as f:
        json.dump([], f)
else:
    with open(clients_file_path, 'r') as f:
        try:
            client_data = json.load(f)
        except json.JSONDecodeError:
            client_data = []


@app.command()
def add_client(session: str):
    """
    Add a client to the client data based on user input for a session name. The commands will be standard.

    :param session: str The session name for the new client.
    :return: None
    """
    new_client = {
        "session_name": session,
        "commands": ["IngTranscribeCommand", "IngGPTCommand", "ExportChatCommand"]
    }
    client_data.append(new_client)
    # save json
    with open(clients_file_path, 'w') as f:
        json.dump(client_data, f, indent=4)

    print(f"Added new client with session name: {session}")

@app.command()
def delete_client():
    print("Here are the available clients:")
    for index, client in enumerate(client_data, start=1):
        print(f"{index}. {client['session_name']}")

    session = typer.prompt("Please enter the session name of the client you want to delete")
    client_data[:] = [client for client in client_data if client.get("session_name") != session]
    print(client_data)

    with open(clients_file_path, 'w') as f:
        json.dump(client_data, f, indent=4)
    print(f"Deleted client with session name: {session}")


@app.command()
def start_program():
    """
    Starts the main program after updating the client_data with added and/or deleted clients
    :return: None
    """
    loop = asyncio.get_event_loop()

    try:
        # Schedule the main coroutine and the do_nothing coroutine
        asyncio.ensure_future(main())
        asyncio.ensure_future(do_nothing())

        loop.run_forever()
    except KeyboardInterrupt:
        loop.stop()


async def main():
    client_handlers = {}
    for config in client_data:
        client = ClientFactory.create_client(config)
        await client.start()
    print("bot started")


async def do_nothing():
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    app()

