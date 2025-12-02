"""Validation helpers for uploaded multimedia content."""

import base64
from fastapi import HTTPException, UploadFile

ALLOWED_AUDIO_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/aac",
    "audio/ogg",
    "audio/opus",
    "audio/flac",
}


def ensure_base64_image(raw: bytes) -> bytes:
    """Return base64-encoded image bytes, encoding binary input when necessary."""
    try:
        raw.decode("utf-8")
        return raw
    except Exception:
        return base64.b64encode(raw)


def validate_audio_file(audio_file: UploadFile) -> None:
    """Validate that the uploaded audio file is a supported audio format.

    The real-time dictation pipeline accepts several audio container formats
    (webm, wav, mp3, mp4, ogg, flac). Previously the code required WAV files
    only which caused clients sending `audio/webm` to be rejected. This helper
    now checks the content type against a broader allowed set and only
    enforces a filename when the content type is missing.
    """
    if not audio_file.filename:
        raise HTTPException(status_code=400, detail="Audio file must have a filename.")
    if audio_file.content_type:
        content_type = audio_file.content_type.lower().split(";", 1)[0].strip()
        if content_type not in ALLOWED_AUDIO_TYPES:
            raise HTTPException(status_code=415, detail=f"Unsupported audio content type: {audio_file.content_type}")
    else:
        # If content_type is missing, at least check extension for a known type
        if not any(audio_file.filename.lower().endswith(ext) for ext in (
            ".wav",
            ".webm",
            ".mp3",
            ".mp4",
            ".m4a",
            ".ogg",
            ".flac",
        )):
            raise HTTPException(status_code=415, detail="Unsupported or missing audio content type.")


async def read_audio_bytes(audio_file: UploadFile) -> bytes:
    """Read validated audio bytes, ensuring the upload is not empty."""
    validate_audio_file(audio_file)
    audio_bytes = await audio_file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")
    return audio_bytes
