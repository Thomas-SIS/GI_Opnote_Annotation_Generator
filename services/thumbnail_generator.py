"""Thumbnail generator service.

Provides a small OOP wrapper around Pillow to create thumbnails
from image bytes (expected base64-encoded input). The resulting
thumbnail will fit within 160x160 pixels and is returned as a
base64-encoded PNG byte string.

Public class: `ThumbnailGenerator`

Example:
    tg = ThumbnailGenerator(max_size=(160, 160))
    thumb_b64 = tg.create_thumbnail_from_base64(b64_input)
"""
from __future__ import annotations

import base64
import io
from typing import Tuple

from PIL import Image


class ThumbnailGenerator:
    """Generate thumbnails from image bytes.

    This class accepts base64-encoded image bytes (str or bytes) and
    returns a base64-encoded PNG thumbnail that fits within the
    configured `max_size` while preserving aspect ratio.

    Args:
        max_size: Maximum width and height for the thumbnail. Defaults to (160, 160).
        background: Optional background color used when converting images with alpha to RGB.
            If None, images with alpha are flattened against white.
    """

    def __init__(self, max_size: Tuple[int, int] = (160, 160), background: Tuple[int, int, int] | None = None):
        self.max_size = max_size
        self.background = background or (255, 255, 255)

    def create_thumbnail_from_base64(self, data: str | bytes) -> str:
        """Create a thumbnail from base64-encoded image data.

        Args:
            data: Base64-encoded image data (either `str` or `bytes`).

        Returns:
            A base64-encoded PNG string of the thumbnail (UTF-8 string).

        Raises:
            ValueError: If the provided data cannot be decoded or opened as an image.
        """
        if isinstance(data, str):
            data_bytes = data.encode("utf-8")
        else:
            data_bytes = data

        try:
            raw = base64.b64decode(data_bytes, validate=True)
        except Exception as exc:
            raise ValueError("Invalid base64 data provided") from exc

        try:
            src = Image.open(io.BytesIO(raw))
        except Exception as exc:
            raise ValueError("Decoded bytes are not a supported image format") from exc

        # Convert to RGBA to preserve alpha if present, then flatten to RGB
        if src.mode not in ("RGBA", "RGB"):
            src = src.convert("RGBA")
        else:
            src = src.convert("RGBA")

        src.thumbnail(self.max_size, Image.LANCZOS)

        # Flatten alpha against the background color
        background = Image.new("RGB", src.size, self.background)
        background.paste(src, mask=src.split()[3])

        out_io = io.BytesIO()
        background.save(out_io, format="PNG", optimize=True)
        out_bytes = out_io.getvalue()

        return base64.b64encode(out_bytes).decode("utf-8")
