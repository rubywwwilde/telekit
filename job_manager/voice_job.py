import os

import openai

from .job import BaseJob
from job_manager.transcription_result import TranscriptionResult
from utils import AudioHelper

import logging

logger = logging.getLogger(__name__)


class VoiceJob(BaseJob):
    SIZE_LIMIT = 20
    DEFAULT_MODEL = "whisper-1"
    SUPPORTED_MODELS = {
        "whisper-1",
        "gpt-4o-transcribe",
        "gpt-4o-mini-transcribe",
    }

    def __init__(self, client_handler, message, model=None):
        super().__init__(client_handler, message)
        self._job_directory = self._create_job_directory()
        self._prompt = ""
        self._client_handler = client_handler
        self._model = self.resolve_model(model)

    @classmethod
    def resolve_model(cls, model=None):
        selected_model = (
            model
            or os.getenv("TELEKIT_TRANSCRIPTION_MODEL")
            or os.getenv("TRANSCRIPTION_MODEL")
            or cls.DEFAULT_MODEL
        )
        if selected_model not in cls.SUPPORTED_MODELS:
            logger.warning("Unsupported transcription model %s, falling back to %s", selected_model, cls.DEFAULT_MODEL)
            return cls.DEFAULT_MODEL
        return selected_model

    def get_file_path(self):
        return os.path.join(self._job_directory, f"{self._id}.ogg")

    def get_chunk_directory(self):
        return os.path.join(self._job_directory, "chunks")

    def get_response_format(self):
        return "verbose_json" if self._model == self.DEFAULT_MODEL else "json"

    async def process_job(self) -> TranscriptionResult:
        downloaded_media_path = await self.manage_download()
        converted_media_path = await AudioHelper.convert_media_to_mp3(downloaded_media_path)

        size = await AudioHelper.get_size_mb(converted_media_path)
        if size > self.SIZE_LIMIT:
            logger.info("Audio file is too large (%s MB), splitting into smaller segments", size)
            return await self.transcribe_chunks(converted_media_path)

        return await self.transcribe(converted_media_path)

    async def transcribe_chunks(self, file_path) -> TranscriptionResult:
        audio_chunks = AudioHelper.split_audio(file_path, self.get_chunk_directory())
        result = TranscriptionResult()
        chunk_offset = 0.0
        prior_text = ""

        for audio_chunk in audio_chunks:
            response = await self._transcribe_file(audio_chunk.path, prompt=prior_text)
            result.append(
                response,
                start_offset=chunk_offset,
                fallback_duration=audio_chunk.duration_seconds,
            )
            prior_text = result.get_plain_text()
            chunk_offset += audio_chunk.duration_seconds

        return result

    async def manage_download(self):
        if not self._message.voice:
            raise TypeError("Message is not a voice message")

        filename = f"{self._id}.ogg"
        client = self._client_handler
        return await client.download_media(self._message, file=os.path.join(self._job_directory, filename))

    async def transcribe(self, file_path) -> TranscriptionResult:
        response = await self._transcribe_file(file_path, prompt=self._prompt)
        return TranscriptionResult.from_response(response)

    async def _transcribe_file(self, file_path, prompt=""):
        with open(file_path, "rb") as file:
            return await openai.Audio.atranscribe(
                self._model,
                file,
                response_format=self.get_response_format(),
                prompt=prompt,
            )
