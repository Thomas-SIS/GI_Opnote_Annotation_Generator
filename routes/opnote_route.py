from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List

from controllers.opnote_controller import generate_opnote

router = APIRouter()


class OpnoteRequest(BaseModel):
    base_opnote: str = ""
    image_ids: List[int] = []


@router.post("/opnotes")
async def post_opnote(request: Request, payload: OpnoteRequest):
    """Generate an operative note from the provided base note and image ids."""
    try:
        result = await generate_opnote(request, payload.base_opnote, payload.image_ids)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return result
