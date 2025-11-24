"""Thumbnail generation service.

Provides a function to generate thumbnails from larger images.
The final thumbnail will be less than 150x150 pixels.
"""

from PIL import Image
import os

def generate_thumbnail(input_path: str, output_path: str, size: tuple = (150, 150)) -> None:
    """Generate a thumbnail from a larger image and save it.

    Args:
        input_path: Path to the source image file.
        output_path: Path to save the generated thumbnail.
        size: Maximum size (width, height) for the thumbnail (default: (150, 150)).

    Raises:
        FileNotFoundError: If the input file does not exist.
        OSError: If the image cannot be opened or saved.
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    with Image.open(input_path) as img:
        img.thumbnail(size, Image.LANCZOS)
        img.save(output_path)
