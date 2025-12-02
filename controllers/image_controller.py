"""Controllers for image thumbnail retrieval."""

from fastapi import HTTPException, Request
from fastapi.responses import Response

from dal.image_dal import ImageDAL


async def get_thumbnail(request: Request, image_id: int) -> Response:
	"""Return the PNG thumbnail for an image record."""
	db_initializer = request.app.state.db_initializer
	record = await ImageDAL(db_initializer).get_image_by_id(int(image_id))
	if record is None:
		raise HTTPException(status_code=404, detail="Image not found")
	if not record.image_thumbnail:
		raise HTTPException(status_code=404, detail="Thumbnail not available for this image")
	return Response(content=record.image_thumbnail, media_type="image/png")
