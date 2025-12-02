"""Session lifecycle helpers for realtime workflows."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request

from services.realtime.opnote_generator import RealtimeOpnoteGenerator
from services.realtime.session_store import SessionStore


async def start_session(request: Request, auto_generate: bool) -> Dict[str, Any]:
	"""Create a new realtime session and return its id."""
	store: SessionStore = request.app.state.session_store
	state = store.create(auto_generate=auto_generate)
	return {"session_id": state.session_id, "auto_generate": state.auto_generate}


async def append_message(request: Request, session_id: str, text: str, role: str = "user") -> Dict[str, Any]:
	"""Add a message to the session conversation."""
	store: SessionStore = request.app.state.session_store
	try:
		state = store.add_message(session_id, role, text)
	except KeyError as exc:  # pragma: no cover - translated to HTTP
		raise HTTPException(status_code=404, detail=str(exc)) from exc
	return {"session_id": session_id, "message_count": len(state.messages)}


async def close_session(
	request: Request,
	session_id: str,
	base_note: Optional[str],
	auto_generate: Optional[bool] = None,
) -> Dict[str, Any]:
	"""Close a session and optionally trigger operative note generation."""
	store: SessionStore = request.app.state.session_store
	try:
		state = store.close(session_id)
	except KeyError as exc:  # pragma: no cover - translated to HTTP
		raise HTTPException(status_code=404, detail=str(exc)) from exc

	if auto_generate is not None:
		state.auto_generate = auto_generate

	result: Dict[str, Any] = {
		"session_id": session_id,
		"auto_generate": state.auto_generate,
		"closed": True,
	}

	if state.auto_generate:
		generator = RealtimeOpnoteGenerator(request.app.state.openai_client)
		note = await generator.generate(messages=state.messages, images=state.images, base_note=base_note)
		result["operative_note"] = note["markdown"]
		result["usage"] = note.get("usage")

	return result
