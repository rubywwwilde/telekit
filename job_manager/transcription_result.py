from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TranscriptionSegment:
    start: float
    text: str


class TranscriptionResult:
    def __init__(self, segments: list[TranscriptionSegment] | None = None, has_timestamps: bool = False):
        self._segments = segments or []
        self._has_timestamps = has_timestamps

    @classmethod
    def from_response(
        cls,
        response: Any,
        *,
        start_offset: float = 0.0,
        fallback_duration: float = 0.0,
    ) -> "TranscriptionResult":
        payload = cls._coerce_payload(response)
        segments_payload = payload.get("segments")

        if isinstance(segments_payload, list) and segments_payload:
            segments = [
                TranscriptionSegment(
                    start=float(segment.get("start", 0.0)) + start_offset,
                    text=str(segment.get("text", "")),
                )
                for segment in segments_payload
                if str(segment.get("text", "")).strip()
            ]
            return cls(segments=segments, has_timestamps=True)

        text = cls._extract_text(payload, response)
        segments = [TranscriptionSegment(start=start_offset, text=text)] if text else []
        result = cls(segments=segments, has_timestamps=False)
        result._fallback_duration = fallback_duration
        return result

    @staticmethod
    def _coerce_payload(response: Any) -> dict[str, Any]:
        if hasattr(response, "to_dict_recursive"):
            return response.to_dict_recursive()
        if isinstance(response, dict):
            return response
        if isinstance(response, str):
            return {"text": response}
        return {}

    @staticmethod
    def _extract_text(payload: dict[str, Any], response: Any) -> str:
        text = payload.get("text") or payload.get("transcript") or payload.get("raw_text")
        if text is not None:
            return str(text).strip()
        if isinstance(response, str):
            return response.strip()
        return ""

    def append(
        self,
        response: Any,
        *,
        start_offset: float = 0.0,
        fallback_duration: float = 0.0,
    ) -> None:
        had_segments = bool(self._segments)
        next_result = self.from_response(
            response,
            start_offset=start_offset,
            fallback_duration=fallback_duration,
        )
        if (
            self._segments
            and next_result._segments
            and not next_result._has_timestamps
            and self._segments[-1].text
            and next_result._segments[0].text
            and not self._segments[-1].text.endswith((" ", "\n", "\t"))
            and not next_result._segments[0].text.startswith((" ", "\n", "\t", ".", ",", "!", "?", ":", ";"))
        ):
            next_result._segments[0].text = f" {next_result._segments[0].text}"
        self._segments.extend(next_result._segments)
        self._has_timestamps = (
            self._has_timestamps and next_result._has_timestamps
            if had_segments
            else next_result._has_timestamps
        )

    def get_plain_text(self) -> str:
        text = "".join(segment.text for segment in self._segments).strip()
        return text[1:] if text.startswith(" ") else text

    def get_segments(self) -> list[dict[str, Any]]:
        return [{"start": segment.start, "text": segment.text} for segment in self._segments]

    def supports_timestamps(self) -> bool:
        return self._has_timestamps

    def get_json(self) -> dict[str, Any]:
        return {"segments": self.get_segments()}
