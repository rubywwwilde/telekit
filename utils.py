import math
import os
from dataclasses import dataclass

from pydub import AudioSegment
from telethon import types
from telethon.extensions import markdown


@dataclass
class AudioChunk:
    path: str
    duration_seconds: float


class AudioHelper:
    MP3_EXPORT_BITRATE = "64k"

    @staticmethod
    async def convert_media_to_mp3(file_path):
        input_format = os.path.splitext(file_path)[1][1:]
        output_path = os.path.splitext(file_path)[0] + ".mp3"
        AudioSegment.from_file(file_path, input_format).export(
            output_path,
            format="mp3",
            bitrate=AudioHelper.MP3_EXPORT_BITRATE,
        )
        return output_path

    @staticmethod
    async def get_size_mb(file_path):
        size_in_bytes = os.path.getsize(file_path)
        return size_in_bytes / (1024 * 1024)

    @staticmethod
    def split_audio(file_path, output_dir, max_size_mb=2) -> list[AudioChunk]:
        audio = AudioSegment.from_mp3(file_path)
        os.makedirs(output_dir, exist_ok=True)

        bytes_per_ms = AudioHelper._bitrate_bytes_per_ms(AudioHelper.MP3_EXPORT_BITRATE)
        fragment_duration_ms = max(1, math.floor((max_size_mb * 1024 * 1024) / bytes_per_ms))

        chunks = []
        start = 0
        index = 0
        duration = len(audio)

        while start < duration:
            end = min(start + fragment_duration_ms, duration)
            chunk = audio[start:end]
            chunk_path = os.path.join(output_dir, f"chunk_{index:03d}.mp3")
            chunk.export(
                chunk_path,
                format="mp3",
                bitrate=AudioHelper.MP3_EXPORT_BITRATE,
            )
            chunks.append(AudioChunk(path=chunk_path, duration_seconds=len(chunk) / 1000))
            start = end
            index += 1

        return chunks

    @staticmethod
    def _bitrate_bytes_per_ms(bitrate: str) -> float:
        normalized = bitrate.strip().lower()
        if normalized.endswith("k"):
            bits_per_second = int(normalized[:-1]) * 1000
        elif normalized.endswith("m"):
            bits_per_second = int(normalized[:-1]) * 1_000_000
        else:
            bits_per_second = int(normalized)
        return bits_per_second / 8 / 1000


class CustomMarkdown:
    @staticmethod
    def parse(text):
        text, entities = markdown.parse(text)
        for i, e in enumerate(entities):
            if isinstance(e, types.MessageEntityTextUrl):
                if e.url == "spoiler":
                    entities[i] = types.MessageEntitySpoiler(e.offset, e.length)
                elif e.url.startswith("emoji/"):
                    entities[i] = types.MessageEntityCustomEmoji(e.offset, e.length, int(e.url.split("/")[1]))
        return text, entities

    @staticmethod
    def unparse(text, entities):
        for i, e in enumerate(entities or []):
            if isinstance(e, types.MessageEntityCustomEmoji):
                entities[i] = types.MessageEntityTextUrl(e.offset, e.length, f"emoji/{e.document_id}")
            if isinstance(e, types.MessageEntitySpoiler):
                entities[i] = types.MessageEntityTextUrl(e.offset, e.length, "spoiler")
        return markdown.unparse(text, entities)
