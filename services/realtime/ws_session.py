"""Dispatch realtime websocket events to the appropriate handlers."""
from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import WebSocket

from services.realtime.session_store import SessionStore
from services.realtime.ws_dictation import DictationMessageHandler
from services.realtime.ws_image import ImageMessageHandler


class RealtimeSessionHandler:
	"""Route websocket messages for a single realtime procedure session."""

	def __init__(self, store: SessionStore, client, db_initializer) -> None:
		self.store = store
		self.image_handler = ImageMessageHandler(store, client, db_initializer)
		self.dictation_handler = DictationMessageHandler(store, client)

	async def handle(self, websocket: WebSocket, session_id: str, payload: Dict[str, Any]) -> None:
		"""Process a single inbound websocket payload."""
		request_id = payload.get("request_id")
		message_type = payload.get("type")
		try:
			if message_type == "conversation.append":
				result = self._append_conversation(session_id, payload)
			elif message_type == "image.classify":
				result = await self.image_handler.classify(session_id, payload)
			elif message_type == "dictation.audio":
				result = await self.dictation_handler.transcribe(session_id, payload)
			else:
				raise ValueError("Unsupported message type.")
			if result is not None:
				result["request_id"] = request_id
				await self._send(websocket, result)
		except Exception as exc:
			await self._send_error(websocket, request_id, str(exc))

	def _append_conversation(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
		"""Persist a text snippet into the session conversation."""
		text = (payload.get("text") or "").strip()
		role = (payload.get("role") or "user").strip() or "user"
		state = self.store.get(session_id)
		if state.closed:
			raise RuntimeError("Session is closed; start a new session.")
		if not text:
			raise ValueError("Conversation text is required.")
		state = self.store.add_message(session_id, role, text)
		return {"type": "conversation.ack", "message_count": len(state.messages)}

	async def _send_error(self, websocket: WebSocket, request_id: Any, detail: str) -> None:
		await self._send(websocket, {"type": "error", "request_id": request_id, "detail": detail})

	async def _send(self, websocket: WebSocket, payload: Dict[str, Any]) -> None:
		await websocket.send_text(json.dumps(payload))
