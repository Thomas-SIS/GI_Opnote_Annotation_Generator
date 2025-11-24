"""Helpers for saving original images, generating thumbnails, and storing records.

This service coordinates saving the original file to disk (under
`database/images/`), generating a thumbnail using the existing
`services.thumbnail_gen.generate_thumbnail`, inserting a record into the
`image_segments` table, and storing the thumbnail bytes in the DB blob.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from services.thumbnail_gen import generate_thumbnail


async def save_image_and_thumbnail(db_client, image_bytes: bytes, mime_type: str, segment_key: str, label_json: Optional[Dict[str, Any]] = None) -> Tuple[str, str, str]:
    """Save the image to disk, generate a thumbnail, and persist database records.

    Args:
        db_client: Asynchronous database client handling file and blob writes.
        image_bytes: Raw bytes of the uploaded image.
        mime_type: MIME type of the uploaded image (e.g., image/jpeg).
        segment_key: Stable identifier derived from the selected label.
        label_json: Optional label metadata to store alongside the record.

    Returns:
        A tuple of `(id, original_path, thumbnail_path)`.

    Raises:
        ValueError: If image bytes are missing.
    """
    if not image_bytes:
        raise ValueError("Image bytes are required for saving.")
    # Generate an id for the segment
    segment_id = str(uuid.uuid4())

    # Determine extension from mime_type
    ext = "jpg"
    if mime_type and "/" in mime_type:
        candidate = mime_type.split("/")[-1]
        if candidate in ("jpeg", "jpg", "png", "webp", "bmp"):
            ext = "jpg" if candidate == "jpeg" else candidate

    filename = f"{segment_id}.{ext}"
    thumb_filename = f"{segment_id}_thumb.{ext}"

    # Save original using DAL helper which writes under database/images/
    original_path = await db_client.save_original_file(filename, image_bytes)

    # Generate thumbnail in the same directory
    thumb_path = str(Path(original_path).with_name(thumb_filename))

    # thumbnail generation is blocking -> run in thread
    await asyncio.to_thread(generate_thumbnail, original_path, thumb_path)

    # Read thumbnail bytes
    # Use the DB client to insert the record first (so we have a row with id)
    await db_client.insert_image_segment(segment_key=segment_key, original_url=original_path, thumbnail_url=thumb_path, label_json=label_json, id=segment_id)

    # Read thumbnail bytes and save into blob column
    # Opening file using standard IO in thread to keep async code non-blocking
    def _read_bytes(path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    thumb_bytes = await asyncio.to_thread(_read_bytes, thumb_path)
    await db_client.save_thumbnail_blob(segment_id, thumb_bytes)

    return segment_id, original_path, thumb_path
