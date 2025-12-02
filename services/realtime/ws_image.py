"""Classify images delivered over the realtime websocket."""
from __future__ import annotations

import base64
from typing import Any, Dict

from dal.image_dal import ImageDAL
from models.image_record import ImageRecord
from services.realtime.image_classifier import RealtimeImageClassifier
from services.realtime.session_store import SessionStore
from services.thumbnail_generator import ThumbnailGenerator
from utils.media_validation import ensure_base64_image


class ImageMessageHandler:
	"""Classify and persist an image for a realtime session."""

	def __init__(self, store: SessionStore, client, db_initializer) -> None:
		self.store = store
		self.classifier = RealtimeImageClassifier(client)
		self.db_initializer = db_initializer

	async def classify(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
		"""Return a structured response after classifying an image."""
		state = self.store.get(session_id)
		if state.closed:
			raise RuntimeError("Session is closed; start a new session.")
		image_b64_text = (payload.get("image_b64") or "").strip()
		if not image_b64_text:
			raise ValueError("Image payload is required.")
		text_hint = (payload.get("text_hint") or "").strip()
		if text_hint:
			self.store.add_message(session_id, "user", text_hint)
		image_b64 = ensure_base64_image(image_b64_text.encode("utf-8"))
		classification = await self.classifier.classify(
			image_b64=image_b64,
			conversation_text=self.store.messages_as_text(session_id),
			images_summary=self.store.images_summary(session_id),
			text_hint=text_hint or None,
		)
		thumb_b64 = ThumbnailGenerator().create_thumbnail_from_base64(image_b64)
		record = ImageRecord(
			id=None,
			image_filename=payload.get("filename") or "upload",
			image_description=classification["description"],
			image_thumbnail=base64.b64decode(thumb_b64),
			label=classification["label"],
		)
		image_id = await ImageDAL(self.db_initializer).create_image(record)
		self.store.add_image(
			session_id,
			image_id=image_id,
			label=classification["label"],
			reasoning=classification["reasoning"],
			description=classification["description"],
		)
		self.store.add_message(
			session_id,
			"assistant",
			f"Image {image_id} labeled {classification['label']}: {classification['description']}",
		)
		return {
			"type": "image.classified",
			"client_image_id": payload.get("client_image_id"),
			"image_id": image_id,
			"label": classification["label"],
			"reasoning": classification["reasoning"],
			"image_description": classification["description"],
			"latency": float(classification.get("latency") or 0.0),
			"input_tokens": int(classification.get("input_tokens") or 0),
			"output_tokens": int(classification.get("output_tokens") or 0),
		}
