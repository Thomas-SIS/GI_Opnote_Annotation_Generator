"""Handle dictation audio events coming over the realtime websocket."""
from __future__ import annotations

from typing import Any, Dict

from services.realtime.dictation_transcriber import DictationTranscriber
from services.realtime.session_store import SessionStore


class DictationMessageHandler:
	"""Transcribe audio and persist dictation snippets."""

	def __init__(self, store: SessionStore, client) -> None:
		self.store = store
		self.transcriber = DictationTranscriber(client)

	async def transcribe(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
		"""Return the transcript for a single audio chunk."""
		state = self.store.get(session_id)
		if state.closed:
			raise RuntimeError("Session is closed; start a new session.")
		audio_b64 = payload.get("audio_b64") or ""
		if not audio_b64:
			raise ValueError("Audio payload is required for dictation.")
		mime_type = payload.get("mime_type") or "audio/webm"
		transcript = await self.transcriber.transcribe(audio_b64, mime_type)
		if transcript:
			state = self.store.add_message(session_id, "dictation", transcript)
		return {
			"type": "dictation.transcript",
			"text": transcript,
			"message_count": len(state.messages),
		}
