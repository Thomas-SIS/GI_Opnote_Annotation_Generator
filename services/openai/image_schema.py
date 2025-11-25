"""Schema definitions for the endoscopic image classification tool."""

from typing import Any, Dict

from services.openai.image_labels import IMAGE_LABELS

FUNCTION_NAME = "classify_endoscopic_image"

FUNCTION_DEFINITION: Dict[str, Any] = {
    "type": "function",
    "name": FUNCTION_NAME,
    "description": (
        "Return the anatomical label, reasoning, and description for the classification."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "label": {
                "type": "string",
                "description": "One of the predefined anatomical locations.",
                "enum": IMAGE_LABELS,
            },
            "reasoning": {
                "type": "string",
                "description": "Concise clinical reasoning supporting the chosen label.",
            },
            "image_description": {
                "type": "string",
                "description": "A written description of the image for annotation purposes.",
            },
        },
        "required": ["label", "reasoning", "image_description"],
        "additionalProperties": False,
    },
    "strict": True,
}
