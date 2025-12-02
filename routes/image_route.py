from fastapi import APIRouter, HTTPException, Request

from controllers.image_controller import get_thumbnail

router = APIRouter()


@router.get("/images/{image_id}/thumbnail")
async def get_image_thumbnail(request: Request, image_id: int):
	"""Return the PNG thumbnail bytes for the specified image id."""
	try:
		return await get_thumbnail(request, image_id)
	except HTTPException:
		raise
	except Exception as exc:
		raise HTTPException(status_code=500, detail=str(exc))
