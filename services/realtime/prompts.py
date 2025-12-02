"""Prompt helpers for realtime classification and opnote generation."""

from __future__ import annotations


def classifier_system_prompt() -> str:
	"""Return the safety-focused classifier system prompt."""
	return (
		"You are an expert gastroenterologist using OpenAI Realtime to classify endoscopic frames. "
		"Lean on the rolling conversation for context, avoid over-calling pathology, and keep labels conservative. "
		"Remember prior anatomy to stay consistent across the procedure."
	)


def classifier_user_prompt(conversation: str, images_seen: str) -> str:
	"""Return the user prompt that grounds the model in current context."""
	context_block = f"Conversation so far:\n{conversation}" if conversation else "No prior context provided."
	images_block = f"Images seen so far:\n{images_seen}" if images_seen else "No prior images provided."
	return (
		f"{context_block}\n\n{images_block}\n\n"
		"Classify the incoming image into the predefined GI anatomy list, provide a concise reasoning, "
		"identify any suspected abnormalities, and author a one-line description suitable for the anatomy diagram."
	)


def opnote_system_prompt() -> str:
	"""Return the operative note system prompt."""
	return (
		"You are an experienced GI endoscopist and skilled medical writer. "
		"Given realtime conversation notes and image summaries, craft a clear, structured operative note in Markdown."
	)


def opnote_user_prompt() -> str:
	"""Return the operative note user guidance text."""
	return (
		"You will receive the running conversation from the case plus labeled images with descriptions. "
		"Preserve any clinician-provided text, keep Findings and Assessment concise, "
		"and include a numbered 'Images and Annotations' section listing id, label, description, and key findings."
	)
