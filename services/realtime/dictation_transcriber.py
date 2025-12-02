"""Transcribe audio buffers for realtime dictation capture."""

from __future__ import annotations

import base64
import io
import os
import tempfile
from openai import AsyncOpenAI


def _filename_for_mime(mime_type: str) -> str:
	"""Return a filename for a given audio MIME type.

	Map common audio MIME types to extensions accepted by the transcription
	service. If the MIME type is unknown, raise a ValueError so callers can
	handle the error instead of sending an unsupported format to the API.
	"""
	# Strip any MIME parameters (e.g. 'audio/webm;codecs=opus') and normalize
	mime = (mime_type or "").lower().split(";", 1)[0].strip()
	mapping = {
		"audio/webm": "webm",
		"audio/wav": "wav",
		"audio/x-wav": "wav",
		"audio/mpeg": "mp3",
		"audio/mp3": "mp3",
		"audio/mp4": "mp4",
		"audio/aac": "m4a",
		"audio/ogg": "oga",
		"audio/opus": "ogg",
		"audio/flac": "flac",
		"audio/x-flac": "flac",
	}
	# Fallback: try to pick extension from the suffix of the mime type
	if mime in mapping:
		suffix = mapping[mime]
	else:
		if "/" in mime and mime.split("/")[-1] in {"webm", "wav", "mp3", "mp4", "mpeg", "mpga", "oga", "ogg", "flac", "m4a"}:
			suffix = mime.split("/")[-1]
		else:
			raise ValueError(f"Unsupported or unknown audio MIME type: '{mime_type}'")
	return f"dictation.{suffix}"


class DictationTranscriber:
	"""Convert base64 audio chunks into text transcripts."""

	def __init__(self, client: AsyncOpenAI) -> None:
		if client is None:
			raise ValueError("AsyncOpenAI client is required.")
		self.client = client

	async def transcribe(self, audio_b64: str, mime_type: str = "audio/webm") -> str:
		"""Return a whitespace-trimmed transcript for the provided audio chunk.

		Args:
			audio_b64: Base64-encoded audio payload.
			mime_type: Optional MIME type hint for file naming.

		Returns:
			The transcript text returned by Whisper.
		"""
		audio_bytes = base64.b64decode(audio_b64)

		# Create a temporary file with the correct extension so the HTTP
		# multipart upload includes a real filename and the client library
		# can infer the correct content-type. Some client implementations
		# don't pick up the name from BytesIO objects reliably which can
		# cause the API to reject the file format.
		tmp_file = None
		try:
			filename = _filename_for_mime(mime_type)
			suffix = os.path.splitext(filename)[1]
			with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
				tf.write(audio_bytes)
				tmp_file = tf.name

			with open(tmp_file, "rb") as fh:
				try:
					response = await self.client.audio.transcriptions.create(
						model="whisper-1",
						file=fh,
						response_format="text",
					)
				except Exception as exc:
					raise RuntimeError(f"Transcription failed: {exc}") from exc
		finally:
			if tmp_file and os.path.exists(tmp_file):
				try:
					os.remove(tmp_file)
				except Exception:
					pass

		return (response or "").strip()
