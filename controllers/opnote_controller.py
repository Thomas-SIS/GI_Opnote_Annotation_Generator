"""Controller for generating operative notes from session context."""

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request

from services.realtime.opnote_generator import RealtimeOpnoteGenerator
from services.realtime.session_store import SessionStore


async def generate_opnote(request: Request, session_id: str, base_opnote: Optional[str]) -> Dict[str, Any]:
	"""Generate an operative note using the current session context."""
	store: SessionStore = request.app.state.session_store
	try:
		session = store.get(session_id)
	except KeyError as exc:  # pragma: no cover - translated to HTTP
		raise HTTPException(status_code=404, detail=str(exc)) from exc

	generator = RealtimeOpnoteGenerator(request.app.state.openai_client)
	result = await generator.generate(messages=session.messages, images=session.images, base_note=base_opnote)

	return {"operative_note": result["markdown"], "usage": result.get("usage")}
