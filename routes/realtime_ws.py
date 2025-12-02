"""WebSocket endpoint for realtime classification and dictation."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from starlette.websockets import WebSocketDisconnect

from services.realtime.session_store import SessionStore
from services.realtime.ws_session import RealtimeSessionHandler

router = APIRouter()


def _require_session_store(websocket: WebSocket) -> SessionStore:
	store = websocket.app.state.session_store
	if store is None:
		raise HTTPException(status_code=500, detail="Session store unavailable")
	return store


@router.websocket("/ws/{session_id}")
async def realtime_socket(websocket: WebSocket, session_id: str, store: SessionStore = Depends(_require_session_store)):
	"""Handle realtime image classification and dictation over one websocket."""
	await websocket.accept()
	try:
		store.get(session_id)
	except KeyError:
		await websocket.send_text(json.dumps({"type": "error", "detail": "Session not found"}))
		await websocket.close()
		return

	handler = RealtimeSessionHandler(store, websocket.app.state.openai_client, websocket.app.state.db_initializer)
	while True:
		try:
			raw = await websocket.receive_text()
		except WebSocketDisconnect:
			break
		except Exception:
			await websocket.send_text(json.dumps({"type": "error", "detail": "Invalid websocket frame"}))
			continue
		try:
			payload = json.loads(raw)
		except Exception:
			await websocket.send_text(json.dumps({"type": "error", "detail": "Payload must be JSON"}))
			continue
		await handler.handle(websocket, session_id, payload)
	try:
		await websocket.close()
	except Exception:
		pass
