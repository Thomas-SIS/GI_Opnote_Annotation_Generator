"""Controller for handling image labeling requests."""

from typing import Any, Dict, Optional

from openai import AsyncOpenAI

from fastapi import HTTPException

from services.openai.image_label import ImageLabelService


class ImageLabelController:
    """Coordinate image labeling requests between the API layer and OpenAI service."""

    def __init__(self, service: Optional[ImageLabelService] = None) -> None:
        """Initialize the controller with an image labeling service.

        Args:
            service: Optional preconfigured ImageLabelService instance.
        """
        self.service = service or ImageLabelService()

    async def label_image(
        self,
        image_bytes: bytes,
        prompt: Optional[str],
        mime_type: str,
        openai_client: AsyncOpenAI | None = None,
    ) -> Dict[str, Any]:
        """Validate input and request an image label from the service.

        Args:
            image_bytes: Raw bytes from the uploaded image.
            prompt: Optional prompt string provided by the user.
            mime_type: MIME type for the uploaded image.
            openai_client: Optional async OpenAI client passed from application state.

        Returns:
            A dictionary containing the service response.

        Raises:
            HTTPException: If validation fails or the service raises an unexpected error.
        """
        if image_bytes is None:
            raise HTTPException(status_code=400, detail="Image bytes are required.")
        try:
            result = await self.service.label_image(image_bytes, prompt, mime_type, client=openai_client)
            # Derive a segment_key from the label_key when available
            label_key = result.get("label_key")
            result["segment_key"] = label_key or "uploaded_image"
            return result
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pylint: disable=broad-exception-caught
            raise HTTPException(status_code=500, detail="Failed to label the image.") from exc
