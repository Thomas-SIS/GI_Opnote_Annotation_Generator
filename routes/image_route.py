from fastapi import APIRouter, UploadFile, File, Request, HTTPException, Form
from controllers.image_controller import upload_image, get_thumbnail

router = APIRouter()


@router.post("/images")
async def post_image(
    request: Request,
    file: UploadFile = File(...),
    text_input: str = Form(None),
    audio_file: UploadFile = File(None),
):
    """Accept an uploaded image file and optional text/audio, then return classification + metadata."""
    try:
        result = await upload_image(request, file, text_input, audio_file)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return result



@router.get("/images/{image_id}/thumbnail")
async def get_image_thumbnail(request: Request, image_id: int):
    """Return the PNG thumbnail bytes for the specified image id."""
    try:
        return await get_thumbnail(request, image_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
