"""FastAPI routes for image labeling."""

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from controllers.image_label_controller import ImageLabelController
from services.image_store import save_image_and_thumbnail

router = APIRouter(prefix="/api/image-label", tags=["image-label"])
controller = ImageLabelController()


def _get_db_client(request: Request):
    """Retrieve the shared database client from the app state."""
    db_client = getattr(request.app.state, "db_client", None)
    if db_client is None:
        raise HTTPException(status_code=500, detail="Database client not initialized.")
    return db_client


def _get_openai_client(request: Request):
    """Retrieve the shared OpenAI client from the app state."""
    openai_client = getattr(request.app.state, "openai_client", None)
    if openai_client is None:
        raise HTTPException(status_code=500, detail="OpenAI client not initialized.")
    return openai_client


@router.post("", summary="Label an uploaded GI image")
async def label_image(request: Request, image: UploadFile = File(...), prompt: str | None = Form(None)):
    """Handle image upload and return the selected diagram label and rationale.

    Args:
        request: The FastAPI request containing application state.
        image: Uploaded gastrointestinal image to label.
        prompt: Optional prompt to guide labeling.

    Returns:
        Labeling result combined with the persisted segment id.

    Raises:
        HTTPException: If the upload cannot be read, labeled, or saved.
    """
    try:
        image_bytes = await image.read()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise HTTPException(status_code=400, detail="Unable to read uploaded image.") from exc

    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")

    mime_type = image.content_type or "image/jpeg"

    try:
        openai_client = _get_openai_client(request)
        result = await controller.label_image(image_bytes, prompt, mime_type, openai_client=openai_client)
        segment_key = result.get("segment_key") or "uploaded_image"
        db_client = _get_db_client(request)
        segment_id, _, _ = await save_image_and_thumbnail(
            db_client, image_bytes, mime_type, segment_key, label_json=result.get("mapping") or None
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise HTTPException(status_code=500, detail="Failed to process image.") from exc

    return {"id": segment_id, **result}
