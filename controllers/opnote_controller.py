from fastapi import Request, HTTPException
from typing import List, Dict, Any

from services.openai.annotation_gen import OperativeNoteGenerator
from dal.image_dal import ImageDAL
from models.image_record import ImageRecord


async def generate_opnote(request: Request, base_opnote: str, image_ids: List[int]) -> Dict[str, Any]:
    """Generate an operative note from a base note and a list of image ids.

    This controller retrieves the `ImageRecord`s for the provided ids,
    invokes the `OperativeNoteGenerator`, and returns the generated
    operative note as markdown.

    Args:
        request: FastAPI Request (used to access shared clients/state).
        base_opnote: Partial or empty operative note text provided by the client.
        image_ids: List of integer image ids to include as context.

    Returns:
        A dict containing the generated operative note under the key
        `operative_note`.

    Raises:
        HTTPException(404) if any image id is not found.
    """
    db_initializer = request.app.state.db_initializer
    openai_client = request.app.state.openai_client

    image_dal = ImageDAL(db_initializer)

    images: List[ImageRecord] = []
    for iid in image_ids:
        rec = await image_dal.get_image_by_id(int(iid))
        if rec is None:
            raise HTTPException(status_code=404, detail=f"Image id {iid} not found")
        images.append(rec)

    generator = OperativeNoteGenerator(openai_client)
    opnote_md = await generator.generate_opnote(
        images=images, base_opnote=base_opnote, template=base_opnote
    )

    return {"operative_note": opnote_md}
