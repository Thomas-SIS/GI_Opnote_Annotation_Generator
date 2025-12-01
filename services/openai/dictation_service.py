"""Audio transcription helper built on OpenAI's transcription models."""

import io
import logging

from openai import AsyncOpenAI

TRANSCRIBE_MODEL = "gpt-4o-transcribe"


class DictationService:
    """Create text transcriptions from audio recordings."""

    def __init__(self, client: AsyncOpenAI) -> None:
        """Initialize the service with a shared OpenAI client."""
        if client is None:
            raise ValueError("OpenAI client is required for dictation.")
        self.client = client

    async def transcribe(self, audio_bytes: bytes, *, filename: str = "audio.wav") -> str:
        """Transcribe WAV audio bytes into text using OpenAI."""
        if not audio_bytes:
            raise ValueError("audio_bytes must contain data for transcription.")

        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename

        try:
            response = await self.client.audio.transcriptions.create(
                model=TRANSCRIBE_MODEL,
                file=audio_file,
            )
        except Exception as exc:
            logging.error("OpenAI transcription request failed: %s", exc)
            raise

        transcript = getattr(response, "text", None)
        if not transcript:
            raise RuntimeError("Transcription response did not include text.")
        return transcript
