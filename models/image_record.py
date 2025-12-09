from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ImageRecord:
    """In-memory representation of a row in the IMAGE table.

    Attributes:
        id: Primary key (None for new records).
        image_filename: Filename stored for the image.
        image_description: Optional textual description.
        image_thumbnail: Optional thumbnail bytes.
        label: Optional anatomical label classified from the image.
        created_at: Unix timestamp (seconds) when the row was inserted.
    """

    id: Optional[int]
    image_filename: str
    image_description: Optional[str] = None
    image_thumbnail: Optional[bytes] = None
    label: Optional[str] = None
    created_at: Optional[int] = None
