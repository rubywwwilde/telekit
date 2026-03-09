import datetime
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from control import ClientHandler
from commands.ing_transcribe.ing_transcribe import IngTranscribeCommand
from job_manager.transcription_result import TranscriptionResult
from job_manager.voice_job import VoiceJob
from utils import AudioChunk


class FakeClient:
    def __init__(self):
        self.parse_mode = None
        self.edits = []
        self.messages = []

    async def edit_message(self, peer_id, message_id, new_text, **kwargs):
        self.edits.append((peer_id, message_id, new_text, kwargs))

    async def send_message(self, peer_id, message, **kwargs):
        self.messages.append((peer_id, message, kwargs))


class DummyClientHandler:
    def __init__(self, downloaded_path):
        self.downloaded_path = downloaded_path

    async def download_media(self, message, file, progress_callback=None):
        return self.downloaded_path


class TranscriptionResultTests(unittest.TestCase):
    def test_whisper_verbose_json_keeps_segments(self):
        result = TranscriptionResult.from_response(
            {
                "duration": 2.0,
                "segments": [
                    {"start": 0.0, "text": " Hello"},
                    {"start": 1.2, "text": " world"},
                ],
            }
        )

        self.assertTrue(result.supports_timestamps())
        self.assertEqual("Hello world", result.get_plain_text())
        self.assertEqual(
            [
                {"start": 0.0, "text": " Hello"},
                {"start": 1.2, "text": " world"},
            ],
            result.get_segments(),
        )

    def test_gpt_json_falls_back_to_plain_text_segment(self):
        result = TranscriptionResult.from_response({"text": "Plain transcript"}, start_offset=5.0)

        self.assertFalse(result.supports_timestamps())
        self.assertEqual("Plain transcript", result.get_plain_text())
        self.assertEqual([{"start": 5.0, "text": "Plain transcript"}], result.get_segments())

    def test_append_preserves_offsets(self):
        result = TranscriptionResult.from_response(
            {"duration": 1.0, "segments": [{"start": 0.0, "text": " One"}]}
        )
        result.append(
            {"duration": 1.0, "segments": [{"start": 0.0, "text": " two"}]},
            start_offset=1.5,
        )

        self.assertEqual(
            [
                {"start": 0.0, "text": " One"},
                {"start": 1.5, "text": " two"},
            ],
            result.get_segments(),
        )


class VoiceJobTests(unittest.IsolatedAsyncioTestCase):
    async def test_long_audio_path_uses_real_chunk_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_path = os.path.join(tmpdir, "sample.ogg")
            converted_path = os.path.join(tmpdir, "sample.mp3")
            chunk_one = os.path.join(tmpdir, "chunk-1.mp3")
            chunk_two = os.path.join(tmpdir, "chunk-2.mp3")

            for path in (original_path, converted_path, chunk_one, chunk_two):
                with open(path, "wb") as handle:
                    handle.write(b"test")

            handler = DummyClientHandler(original_path)
            message = SimpleNamespace(voice=True)
            job = VoiceJob(handler, message, model="gpt-4o-mini-transcribe")

            responses = [{"text": "First"}, {"text": " second"}]
            mock_transcribe = AsyncMock(side_effect=responses)

            with patch("job_manager.voice_job.AudioHelper.convert_media_to_mp3", AsyncMock(return_value=converted_path)), \
                patch("job_manager.voice_job.AudioHelper.get_size_mb", AsyncMock(return_value=25)), \
                patch(
                    "job_manager.voice_job.AudioHelper.split_audio",
                    return_value=[
                        AudioChunk(path=chunk_one, duration_seconds=3.0),
                        AudioChunk(path=chunk_two, duration_seconds=2.0),
                    ],
                ), \
                patch("job_manager.voice_job.openai.Audio.atranscribe", mock_transcribe):
                result = await job.process_job()

            self.assertEqual("First second", result.get_plain_text())
            self.assertFalse(result.supports_timestamps())
            self.assertEqual(chunk_one, mock_transcribe.await_args_list[0].args[1].name)
            self.assertEqual(chunk_two, mock_transcribe.await_args_list[1].args[1].name)

    async def test_model_resolution_prefers_env_then_falls_back(self):
        message = SimpleNamespace(voice=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = DummyClientHandler(os.path.join(tmpdir, "sample.ogg"))

            with patch.dict(os.environ, {"TELEKIT_TRANSCRIPTION_MODEL": "gpt-4o-transcribe"}, clear=False):
                job = VoiceJob(handler, message)
                self.assertEqual("gpt-4o-transcribe", job._model)

            with patch.dict(os.environ, {"TELEKIT_TRANSCRIPTION_MODEL": "not-a-real-model"}, clear=False):
                job = VoiceJob(handler, message)
                self.assertEqual(VoiceJob.DEFAULT_MODEL, job._model)

    async def test_small_audio_path_uses_converted_mp3(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_path = os.path.join(tmpdir, "sample.ogg")
            converted_path = os.path.join(tmpdir, "sample.mp3")
            for path in (original_path, converted_path):
                with open(path, "wb") as handle:
                    handle.write(b"test")

            handler = DummyClientHandler(original_path)
            message = SimpleNamespace(voice=True)
            job = VoiceJob(handler, message, model="gpt-4o-mini-transcribe")
            mock_transcribe = AsyncMock(return_value={"text": "done"})

            with patch("job_manager.voice_job.AudioHelper.convert_media_to_mp3", AsyncMock(return_value=converted_path)), \
                patch("job_manager.voice_job.AudioHelper.get_size_mb", AsyncMock(return_value=1)), \
                patch("job_manager.voice_job.openai.Audio.atranscribe", mock_transcribe):
                await job.process_job()

            self.assertEqual(converted_path, mock_transcribe.await_args.args[1].name)


class ClientHandlerTranscriptTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_transcript_splits_long_edit_into_edit_and_replies(self):
        client = FakeClient()
        handler = ClientHandler(client, [])
        text = "word " * 1200

        await handler.send_transcript(
            peer_id=1,
            text=text,
            edit_message_id=42,
            reply_to=42,
            prepend_message="prefix\n\n",
            prefer_edit=True,
        )

        self.assertEqual(1, len(client.edits))
        self.assertGreaterEqual(len(client.messages), 1)
        self.assertTrue(client.edits[0][2].startswith("prefix"))

    async def test_send_transcript_replies_for_media_overflow_instead_of_file(self):
        client = FakeClient()
        handler = ClientHandler(client, [])
        text = "word " * 1200

        await handler.send_transcript(
            peer_id=1,
            text=text,
            edit_message_id=99,
            reply_to=99,
            prepend_message="prefix\n\n",
            prefer_edit=True,
            is_media_message=True,
        )

        self.assertEqual(1, len(client.edits))
        self.assertIn("Transcription continues below.", client.edits[0][2])
        self.assertGreaterEqual(len(client.messages), 1)


class IngTranscribeCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_client_settings_model_is_used_when_flag_is_absent(self):
        event = SimpleNamespace(
            message=SimpleNamespace(
                peer_id=1,
                voice=True,
                id=10,
                date=datetime.datetime.now(datetime.timezone.utc),
            )
        )
        client_handler = SimpleNamespace(
            settings=SimpleNamespace(transcription_model="gpt-4o-mini-transcribe"),
            edit_message=AsyncMock(),
        )
        command = IngTranscribeCommand(event, client_handler)
        fake_result = SimpleNamespace(get_plain_text=lambda: "done")

        with patch("commands.ing_transcribe.ing_transcribe.VoiceJob") as mock_voice_job, \
            patch.object(command, "send_result", AsyncMock()):
            mock_voice_job.return_value.process_job = AsyncMock(return_value=fake_result)
            await command.handle_voice_message()

        self.assertEqual(mock_voice_job.call_args.kwargs["model"], "gpt-4o-mini-transcribe")


if __name__ == "__main__":
    unittest.main()
