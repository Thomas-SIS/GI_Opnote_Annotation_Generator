"""Simple in-memory store for realtime sessions."""

from __future__ import annotations

from typing import Dict, Iterable
from uuid import uuid4

from models.session_models import SessionImage, SessionMessage, SessionState


class SessionStore:
	"""Manage realtime sessions, messages, and classified images."""

	def __init__(self) -> None:
		self._sessions: Dict[str, SessionState] = {}

	def create(self, auto_generate: bool) -> SessionState:
		"""Create a new session with the requested auto-generate flag."""
		session_id = uuid4().hex
		state = SessionState(session_id=session_id, auto_generate=auto_generate)
		self._sessions[session_id] = state
		return state

	def get(self, session_id: str) -> SessionState:
		"""Return a session or raise KeyError if missing."""
		state = self._sessions.get(session_id)
		if state is None:
			raise KeyError(f"Session {session_id} not found")
		return state

	def add_message(self, session_id: str, role: str, content: str) -> SessionState:
		"""Append a message to the session conversation."""
		state = self.get(session_id)
		state.messages.append(SessionMessage(role=role, content=content.strip()))
		return state

	def add_image(
		self,
		session_id: str,
		image_id: int,
		label: str | None,
		reasoning: str | None,
		description: str | None,
	) -> SessionState:
		"""Record a classified image for later opnote generation."""
		state = self.get(session_id)
		state.images.append(
			SessionImage(id=image_id, label=label, reasoning=reasoning, description=description)
		)
		return state

	def close(self, session_id: str) -> SessionState:
		"""Mark a session as closed while keeping its contents for generation."""
		state = self.get(session_id)
		state.closed = True
		return state

	def messages_as_text(self, session_id: str, limit: int = 15) -> str:
		"""Return the most recent messages as a text transcript."""
		state = self.get(session_id)
		slice_: Iterable[SessionMessage] = state.messages[-limit:] if limit else state.messages
		lines = [f"{msg.role.upper()}: {msg.content}" for msg in slice_]
		return "\n".join(lines)

	def context_summary(self, session_id: str, limit: int = 15) -> str:
		"""Return recent conversation with a short summary of labeled images."""
		state = self.get(session_id)
		slice_: Iterable[SessionMessage] = state.messages[-limit:] if limit else state.messages
		lines = [f"{msg.role.upper()}: {msg.content}" for msg in slice_]
		if state.images:
			lines.append("IMAGES SEEN:")
			for image in state.images:
				label = image.label or "Unlabeled site"
				description = image.description or "No description."
				lines.append(f"{image.id}: {label} - {description}")
		return "\n".join(lines)

	def images_summary(self, session_id: str) -> str:
		"""Return a short summary of all labeled images for grounding prompts."""
		state = self.get(session_id)
		return "\n".join(
			f"{image.id}: {image.label or 'Unlabeled site'} - {image.description or ''}" for image in state.images
		)
