"""Image labeling via OpenAI with diagram mapping constraints."""

import base64
import json
import logging
import os
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from services.openai.diagram_mapping import build_tool_schema, load_diagram_mapping
from services.openai.response_utils import extract_first_tool_call, serialize_response

LOGGER = logging.getLogger(__name__)
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
DEFAULT_PROMPT = (
    "Identify the gastrointestinal anatomy region shown. Choose the single best "
    "label from the provided options and explain your reasoning succinctly."
)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
MAPPING_PATH = os.path.join(BASE_DIR, "public", "data", "diagram_mapping.json")


class ImageLabelService:
    """Service for sending image labeling requests to OpenAI."""

    def __init__(self, mapping_path: str = MAPPING_PATH, client: Optional[AsyncOpenAI] = None) -> None:
        """Initialize the service with a diagram mapping and OpenAI client.

        Args:
            mapping_path: Location of the diagram mapping JSON.
            client: Optional async OpenAI client instance for dependency injection.
        """
        self.mapping_path = mapping_path
        self.client = client
        self.diagram_mapping = load_diagram_mapping(self.mapping_path)

    def _encode_image(self, image_bytes: bytes, mime_type: str) -> str:
        """Encode image bytes to a base64 data URL string."""
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    def _build_input(self, prompt_text: str, encoded_image: str) -> List[Dict[str, Any]]:
        """Build the model input payload for the responses API."""
        system_prompt = (
            "You are a GI endoscopy assistant. Analyze the provided image and select the region "
            "label that best matches the anatomy. Only choose labels provided in the tool schema."
        )
        return [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}],
            },
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt_text},
                    {
                        "type": "input_text",
                        "text": "Available labels: "
                        + ", ".join(
                            f"{key} ({value.get('display_name', key)})" for key, value in self.diagram_mapping.items()
                        ),
                    },
                    {"type": "input_image", "image_url": {"url": encoded_image}},
                ],
            },
        ]

    def _resolve_client(self, client: Optional[AsyncOpenAI]) -> AsyncOpenAI:
        """Return a usable OpenAI client or raise if missing."""
        resolved = client or self.client
        if resolved is None:
            raise ValueError("OpenAI client is not configured.")
        return resolved

    async def label_image(
        self,
        image_bytes: bytes,
        prompt: Optional[str] = None,
        mime_type: str = "image/jpeg",
        client: Optional[AsyncOpenAI] = None,
    ) -> Dict[str, Any]:
        """Request an image label and rationale from OpenAI using the responses API.

        Args:
            image_bytes: Raw bytes of the uploaded image.
            prompt: Optional user-provided prompt; falls back to a default instruction.
            mime_type: MIME type for the provided image bytes (e.g., image/jpeg).
            client: Optional async OpenAI client to use for the call.

        Returns:
            A dictionary containing the selected label, rationale, and raw response content.

        Raises:
            ValueError: If the request cannot be fulfilled or a valid label is not returned.
        """
        if not image_bytes:
            raise ValueError("Image content is required for labeling.")

        encoded_image = self._encode_image(image_bytes, mime_type)
        prompt_text = prompt or DEFAULT_PROMPT
        openai_client = self._resolve_client(client)

        response = await openai_client.responses.create(
            model=DEFAULT_MODEL,
            input=self._build_input(prompt_text, encoded_image),
            tools=build_tool_schema(self.diagram_mapping),
            tool_choice={"type": "function", "function": {"name": "select_diagram_label"}},
        )

        LOGGER.info("Image label response received: %s", response)

        tool_call = extract_first_tool_call(response)
        if not tool_call:
            raise ValueError("No tool call was returned by the labeling model.")

        try:
            arguments = json.loads(tool_call["function"]["arguments"])
        except (KeyError, json.JSONDecodeError) as exc:
            raise ValueError("Unable to parse the model's tool arguments.") from exc

        label_key = arguments.get("label_key")
        if label_key not in self.diagram_mapping:
            raise ValueError("Model returned an unknown label key.")

        return {
            "label_key": label_key,
            "rationale": arguments.get("rationale"),
            "mapping": self.diagram_mapping[label_key],
            "raw_response": serialize_response(response),
        }
