"""Session domain models for realtime workflows."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SessionMessage:
	"""Structured message used to build realtime context."""

	role: str
	content: str
	created_at: float = field(default_factory=lambda: time.time())


@dataclass
class SessionImage:
	"""Lightweight view of a classified image for conversation context."""

	id: int
	label: Optional[str]
	reasoning: Optional[str]
	description: Optional[str]


@dataclass
class SessionState:
	"""In-memory session tracking for realtime interactions."""

	session_id: str
	auto_generate: bool
	messages: List[SessionMessage] = field(default_factory=list)
	images: List[SessionImage] = field(default_factory=list)
	closed: bool = False
