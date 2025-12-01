"""Description: Multimodal image classification service using OpenAI's Responses API."""

import logging
import time
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from services.openai.dictation_service import DictationService
from services.openai.image_prompts import build_system_prompt, build_user_prompt
from services.openai.image_schema import FUNCTION_DEFINITION, FUNCTION_NAME
from services.openai.media_inputs import build_inputs
from services.openai.response_parser import extract_usage, parse_function_call


class ImageClassifier:
    """Class for classifying images with optional text and audio context."""

    def __init__(self, client: AsyncOpenAI) -> None:
        """Initialize the ImageClassifier with an OpenAI async client."""
        if client is None:
            raise ValueError("OpenAI client must be provided.")
        self.client = client
        self.system_prompt = build_system_prompt()
        self.dictation = DictationService(client)

    async def classify_media(
        self,
        image_bytes: bytes,
        *,
        text_input: Optional[str] = None,
        audio_bytes: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """Classify an image using optional text and audio context."""
        start_time = time.time()
        audio_transcript: Optional[str] = None
        audio_present = bool(audio_bytes)
        if audio_bytes:
            audio_transcript = await self.dictation.transcribe(audio_bytes)

        user_prompt = build_user_prompt(bool(text_input), audio_present)
        inputs = build_inputs(
            self.system_prompt,
            user_prompt,
            text_input=text_input,
            audio_transcript=audio_transcript,
            image_bytes=image_bytes,
        )
        response = await self._create_response(inputs)
        result = self._parse_response(response)
        result["latency"] = time.time() - start_time
        result.update(extract_usage(response))
        return result

    async def _create_response(self, inputs: List[Dict[str, Any]]) -> Any:
        """Send the multimodal request to the OpenAI Responses API."""
        try:
            return await self.client.responses.create(
                model="gpt-5",
                input=inputs,
                tools=[FUNCTION_DEFINITION],
                tool_choice={"type": "function", "name": FUNCTION_NAME},
            )
        except Exception as exc:
            logging.error("Error during OpenAI Responses API call: %s", exc)
            raise

    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """Parse the classification output from the model."""
        try:
            result = parse_function_call(response, tool_name=FUNCTION_NAME)
        except Exception as exc:
            logging.error("Error parsing OpenAI response: %s", exc)
            logging.error("Full response object: %r", response)
            raise

        if not all(result.values()):
            logging.error("Incomplete classification output received from OpenAI.")
        return result

# end of ImageClassifier
