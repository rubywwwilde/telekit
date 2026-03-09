import datetime
import logging

from telethon.tl.types import Message

from commands.base import Command
from job_manager.voice_job import VoiceJob


class IngTranscribeCommand(Command):
    """
    This command transcribes a voice message or a reply to a message.
    """

    command_name = "@ingTranscribe"
    aliases = ["@"]

    def __init__(self, event, client_handler):
        super().__init__(event, client_handler)
        self.peer_id = self.event.message.peer_id

        self.format = "text"
        self.model = None
        self.summarize = False
        self.create_chapters = False
        self._edit_existing = True
        self._send_as_new = None
        self._prepend_message = not self.is_voice_message()

        self._message_to_prepend = f"[🐾](emoji/5460768917901285539) __{self.command_name}__\n\n"
        self._status_message = "[❤️](emoji/5321387857527447505) __Transcribing...__[✨](emoji/5278352839272309494)"

    @property
    def message_to_prepend(self):
        return self._message_to_prepend if self._prepend_message else ""

    @property
    def edit_existing(self):
        return self._edit_existing if not self._send_as_new else False

    async def execute(self):
        if self.is_voice_message():
            await self.handle_voice_message()
        else:
            await self.handle_text_message()

    def is_voice_message(self):
        return hasattr(self.event.message, "voice") and self.event.message.voice

    async def handle_voice_message(self):
        is_recent = lambda msg_date: (datetime.datetime.now(datetime.timezone.utc) - msg_date).total_seconds() <= 10

        if not is_recent(self.event.message.date):
            logging.info("Ignoring old message")
            return

        await self.client_handler.edit_message(self.peer_id, self.event.message.id, self._status_message)

        selected_model = self.model or self.client_handler.settings.transcription_model
        voice_job = VoiceJob(self.client_handler, self.event.message, model=selected_model)
        result = await voice_job.process_job()
        await self.send_result(result)

    def is_from_peer(self):
        return self.peer_id == self.event.message.from_id or self.event.message.from_id is None

    async def send_result(self, result):
        if self.format == "file":
            await self.client_handler.send_text_as_file(self.peer_id, result.get_plain_text(), "transcription.txt")
            await self.remove_command_message()
            return

        if self.format == "vtt":
            if not result.supports_timestamps():
                await self.client_handler.reply_message(
                    self.peer_id,
                    "VTT output requires `whisper-1` timestamp support. Sending plain text instead.",
                    reply_to=self.event.message.reply_to_msg_id or self.event.message.id,
                )
            else:
                await self.client_handler.reply_message(
                    self.peer_id,
                    "VTT output is not implemented yet. Sending plain text instead.",
                    reply_to=self.event.message.reply_to_msg_id or self.event.message.id,
                )

        if self.is_voice_message():
            await self.client_handler.send_transcript(
                self.peer_id,
                result.get_plain_text(),
                edit_message_id=self.event.message.id,
                reply_to=self.event.message.id,
                prepend_message=self.message_to_prepend,
                prefer_edit=True,
                is_media_message=True,
            )
            return

        if self.format == "text":
            if self.edit_existing and self.is_from_peer():
                await self.client_handler.send_transcript(
                    self.peer_id,
                    result.get_plain_text(),
                    edit_message_id=self.event.message.reply_to_msg_id,
                    reply_to=self.event.message.reply_to_msg_id,
                    prepend_message=self.message_to_prepend,
                    prefer_edit=True,
                )
            else:
                await self.client_handler.send_transcript(
                    self.peer_id,
                    result.get_plain_text(),
                    reply_to=self.event.message.reply_to_msg_id,
                    prepend_message=self.message_to_prepend,
                )

        await self.remove_command_message()

    async def set_status(self, status, message: Message, toReplace=False):
        if toReplace:
            await self.client_handler.edit_message(self.peer_id, self.event.message.id, status)
        else:
            await self.client_handler.edit_message(self.peer_id, self.event.message.id, status + "\n\n" + message.raw_text)

    async def remove_command_message(self):
        if self.is_voice_message():
            return
        await self.client_handler.delete_message(self.peer_id, self.event.message.id)

    async def handle_text_message(self):
        await self.set_status(self._status_message, self.event.message, toReplace=True)
        args = self.event.message.message.split()
        await self.parse_args(args)

        message_to_transcribe = await self.client_handler.get_message_by_id(
            self.peer_id,
            self.event.message.reply_to_msg_id,
        )
        selected_model = self.model or self.client_handler.settings.transcription_model
        voice_job = VoiceJob(self.client_handler, message_to_transcribe, model=selected_model)
        result = await voice_job.process_job()
        await self.send_result(result)

    async def parse_args(self, args):
        for i, arg in enumerate(args):
            if arg in ("-f", "--format") and i + 1 < len(args):
                self.format = args[i + 1]
            elif arg in ("-m", "--model") and i + 1 < len(args):
                requested_model = args[i + 1]
                self.model = VoiceJob.resolve_model(requested_model)
                if self.model != requested_model:
                    logging.warning(
                        "Unsupported transcription model %s requested. Falling back to %s.",
                        requested_model,
                        self.model,
                    )
            elif arg in ("-s", "--summarize"):
                self.summarize = True
            elif arg in ("-c", "--chapters"):
                self.create_chapters = True
            elif arg in ("-n", "--new"):
                self._send_as_new = True
            elif arg in ("-e", "--existing"):
                self._edit_existing = True
