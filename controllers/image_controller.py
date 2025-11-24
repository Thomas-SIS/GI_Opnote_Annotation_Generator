from fastapi import Request, UploadFile, HTTPException
from fastapi.responses import Response
from typing import Dict, Any
import base64

from services.openai.image_classifier import ImageClassifier
from services.thumbnail_generator import ThumbnailGenerator
from services.openai.cost_generator import CostGenerator
from dal.image_dal import ImageDAL
from models.image_record import ImageRecord


async def upload_image(request: Request, file: UploadFile) -> Dict[str, Any]:
    """Controller to handle image upload, classification, thumbnailing, storage, and cost.

    Args:
        request: FastAPI Request object (used to access app.state for shared clients).
        file: Uploaded file (expected to be base64-encoded JPEG payload as bytes or uploaded file).

    Returns:
        A dict containing: id, label, reasoning, image_description, input_tokens, output_tokens, latency, cost
    """

    # Read file bytes. Expect the client to send base64-encoded image data as file body.
    raw = await file.read()

    # If client sent a file with binary image, convert to base64 string for classifier which expects base64 string
    try:
        # Heuristic: if the uploaded payload looks like base64 (contains only base64 chars / padding), use as-is
        raw.decode("utf-8")
        b64_input = raw
    except Exception:
        # Binary image -> base64 encode
        b64_input = base64.b64encode(raw)

    # Acquire shared resources from app.state
    openai_client = request.app.state.openai_client
    db_initializer = request.app.state.db_initializer

    # Services
    classifier = ImageClassifier(openai_client)
    thumb_gen = ThumbnailGenerator()
    cost_gen = CostGenerator()
    image_dal = ImageDAL(db_initializer)

    # Classify image
    classification = await classifier.classify_image(b64_input)

    label = classification.get("label")
    reasoning = classification.get("reasoning")
    image_description = classification.get("image_description")
    input_tokens_raw = classification.get("input_tokens")
    output_tokens_raw = classification.get("output_tokens")
    input_tokens = int(input_tokens_raw) if input_tokens_raw is not None else 0
    output_tokens = int(output_tokens_raw) if output_tokens_raw is not None else 0
    latency = classification.get("latency") or 0.0

    # Create thumbnail (returns base64 PNG string)
    thumbnail_b64 = thumb_gen.create_thumbnail_from_base64(b64_input)

    # Persist record
    record = ImageRecord(
        id=None,
        image_filename=file.filename or "uploaded_image",
        image_description=image_description,
        image_thumbnail=base64.b64decode(thumbnail_b64),
        label=label,
    )
    image_id = await image_dal.create_image(record)

    # Compute cost estimate (assume model 'gpt-5')
    try:
        cost = cost_gen.estimate(input_tokens=input_tokens, output_tokens=output_tokens, model="gpt-5")
    except ValueError:
        # Fall back to a zeroed-out cost structure if pricing fails (e.g., missing usage)
        cost = {
            "model": "gpt-5",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": 0.0,
            "output_cost": 0.0,
            "total_cost": 0.0,
        }

    return {
        "id": image_id,
        "label": label,
        "reasoning": reasoning,
        "image_description": image_description,
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "latency": float(latency),
        "cost": cost,
    }


async def get_thumbnail(request: Request, image_id: int) -> Response:
    """Controller to fetch the thumbnail bytes for a stored image.

    Args:
        request: FastAPI Request (to access app.state.db_initializer).
        image_id: Integer id of the image row.

    Returns:
        FastAPI `Response` with `content` set to raw PNG bytes and
        `media_type` set to `image/png`.

    Raises:
        HTTPException(404) if the image or thumbnail is not found.
    """
    db_initializer = request.app.state.db_initializer
    image_dal = ImageDAL(db_initializer)

    record = await image_dal.get_image_by_id(int(image_id))
    if record is None:
        raise HTTPException(status_code=404, detail="Image not found")

    if not record.image_thumbnail:
        raise HTTPException(status_code=404, detail="Thumbnail not available for this image")

    # Stored thumbnails are raw PNG bytes; return them directly
    return Response(content=record.image_thumbnail, media_type="image/png")
