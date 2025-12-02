"""Realtime image classification using OpenAI streaming Responses."""
from __future__ import annotations
import time
from typing import Any, Dict, Optional

from openai import AsyncOpenAI

from services.realtime.labels import IMAGE_LABELS
from services.realtime.prompts import classifier_system_prompt, classifier_user_prompt
from services.realtime.response_parser import extract_usage, parse_tool_output

FUNCTION_NAME = "classify_endoscopic_image"

FUNCTION_DEFINITION: Dict[str, Any] = {
	"type": "function",
	"name": FUNCTION_NAME,
	"description": "Return the anatomical label, reasoning, and description for the classification.",
	"parameters": {
		"type": "object",
		"properties": {
			"label": {"type": "string", "enum": IMAGE_LABELS},
			"reasoning": {"type": "string"},
			"image_description": {"type": "string"},
		},
		"required": ["label", "reasoning", "image_description"],
		"additionalProperties": False,
	},
	"strict": True,
}

def _data_url(image_bytes: bytes) -> str:
	decoded = image_bytes.decode("utf-8")
	return f"data:image/jpeg;base64,{decoded}"

class RealtimeImageClassifier:
	"""Classify images while streaming tokens via the Realtime Responses API."""

	def __init__(self, client: AsyncOpenAI) -> None:
		if client is None:
			raise ValueError("AsyncOpenAI client is required.")
		self.client = client

	async def classify(
		self,
		*,
		image_b64: bytes,
		conversation_text: str,
		images_summary: str = "",
		text_hint: Optional[str] = None,
		model: str = "gpt-4o-realtime-preview-2024-12-17",
	) -> Dict[str, Any]:
		"""Return label, reasoning, description, and usage for an image.

		Args:
			image_b64: Base64-encoded image bytes.
			conversation_text: Rolling conversation transcript.
			images_summary: Short summary of previously seen anatomy.
			text_hint: Optional clinician-provided note to inject.
			model: OpenAI realtime model to use.
		"""
		system_prompt = classifier_system_prompt()
		user_prompt = classifier_user_prompt(conversation_text, images_summary)
		image_url = _data_url(image_b64)

		inputs = [
			{"type": "message", "role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
			{"type": "message", "role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
			{"type": "message", "role": "user", "content": [{"type": "input_image", "image_url": image_url}]},
		]
		if text_hint:
			inputs.append(
				{
					"type": "message",
					"role": "user",
					"content": [{"type": "input_text", "text": f"Clinician note: {text_hint}"}],
				}
			)

		start = time.time()
		async with self.client.responses.stream(
			model=model,
			input=inputs,
			tools=[FUNCTION_DEFINITION],
			tool_choice={"type": "function", "name": FUNCTION_NAME},
		) as stream:
			async for _ in stream:
				# Stream tokens to keep the connection warm; output parsed after final response.
				pass
			getter = getattr(stream, "get_final_response", None)
			if getter:
				response = await getter()
			else:
				response = getattr(stream, "response", None)
			if response is None:
				raise RuntimeError("No response returned from OpenAI stream")

		result = parse_tool_output(response, FUNCTION_NAME)
		result["latency"] = time.time() - start
		result.update(extract_usage(response))
		return result
