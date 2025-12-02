"""Operative note generator built on OpenAI streaming Responses."""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from openai import AsyncOpenAI

from models.session_models import SessionImage, SessionMessage
from services.realtime.prompts import opnote_system_prompt, opnote_user_prompt
from services.realtime.response_parser import extract_text, extract_usage


def _conversation_block(messages: Iterable[SessionMessage]) -> str:
	lines = [f"{msg.role.upper()}: {msg.content}" for msg in messages]
	return "\n".join(lines) if lines else "No clinician messages recorded."


def _images_block(images: Iterable[SessionImage]) -> str:
	rows = []
	for img in images:
		label = img.label or "Unlabeled site"
		desc = img.description or "No description."
		reasoning = img.reasoning or "No reasoning provided."
		rows.append(f"{img.id}. {label} - {desc} | Reasoning: {reasoning}")
	return "\n".join(rows) if rows else "No images classified."


class RealtimeOpnoteGenerator:
	"""Use GPT-5 to author a Markdown operative note from session context."""

	def __init__(self, client: AsyncOpenAI) -> None:
		if client is None:
			raise ValueError("AsyncOpenAI client is required.")
		self.client = client

	async def generate(
		self,
		*,
		messages: List[SessionMessage],
		images: List[SessionImage],
		base_note: Optional[str] = None,
		model: str = "gpt-5",
		max_tokens: int = 2000,
	) -> Dict[str, object]:
		"""Return markdown, usage, and supporting metadata."""
		context = _conversation_block(messages)
		images_text = _images_block(images)
		context_note = base_note.strip() if base_note else ""

		content = (
			(f"Existing operative note draft:\n{context_note}\n\n" if context_note else "")
			+ f"Conversation log:\n{context}\n\n"
			+ f"Images and annotations:\n{images_text}"
		)

		response = await self.client.responses.create(
			model=model,
			input=[
				{"type": "message", "role": "system", "content": [{"type": "input_text", "text": opnote_system_prompt()}]},
				{"type": "message", "role": "user", "content": [{"type": "input_text", "text": opnote_user_prompt()}]},
				{"type": "message", "role": "user", "content": [{"type": "input_text", "text": content}]},
			],
			max_output_tokens=max_tokens,
		)

		return {
			"markdown": extract_text(response),
			"usage": extract_usage(response),
		}
