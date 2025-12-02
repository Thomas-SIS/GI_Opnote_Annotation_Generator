"""FastAPI routes for realtime sessions and operative notes."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from controllers.opnote_controller import generate_opnote
from controllers.session_controller import append_message, close_session, start_session

router = APIRouter(prefix="/sessions")


class StartPayload(BaseModel):
	auto_generate: bool = True


class MessagePayload(BaseModel):
	text: str
	role: str = "user"


class ClosePayload(BaseModel):
	base_note: Optional[str] = None
	auto_generate: Optional[bool] = None


class OpnotePayload(BaseModel):
	base_note: Optional[str] = None


@router.post("")
async def start_session_route(request: Request, payload: StartPayload):
	try:
		return await start_session(request, payload.auto_generate)
	except HTTPException:
		raise
	except Exception as exc:
		raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{session_id}/messages")
async def post_message_route(request: Request, session_id: str, payload: MessagePayload):
	try:
		return await append_message(request, session_id, payload.text, payload.role)
	except HTTPException:
		raise
	except Exception as exc:
		raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{session_id}/close")
async def close_session_route(request: Request, session_id: str, payload: ClosePayload):
	try:
		return await close_session(request, session_id, payload.base_note, payload.auto_generate)
	except HTTPException:
		raise
	except Exception as exc:
		raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{session_id}/opnote")
async def manual_opnote_route(request: Request, session_id: str, payload: OpnotePayload):
	try:
		return await generate_opnote(request, session_id, payload.base_note)
	except HTTPException:
		raise
	except Exception as exc:
		raise HTTPException(status_code=500, detail=str(exc))
