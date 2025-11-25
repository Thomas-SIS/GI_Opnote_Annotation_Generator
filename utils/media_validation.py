"""Validation helpers for uploaded multimedia content."""

import base64
from fastapi import HTTPException, UploadFile

ALLOWED_AUDIO_TYPES = {"audio/wav", "audio/x-wav"}


def ensure_base64_image(raw: bytes) -> bytes:
    """Return base64-encoded image bytes, encoding binary input when necessary."""
    try:
        raw.decode("utf-8")
        return raw
    except Exception:
        return base64.b64encode(raw)


def validate_audio_file(audio_file: UploadFile) -> None:
    """Validate that the uploaded audio file is WAV format."""
    if not (audio_file.filename and audio_file.filename.lower().endswith(".wav")):
        raise HTTPException(status_code=400, detail="Audio must be a .wav file.")
    if audio_file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=415, detail="Unsupported audio content type; expected audio/wav."
        )


async def read_audio_bytes(audio_file: UploadFile) -> bytes:
    """Read validated audio bytes, ensuring the upload is not empty."""
    validate_audio_file(audio_file)
    audio_bytes = await audio_file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")
    return audio_bytes
