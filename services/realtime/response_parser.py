"""Helpers to extract structured data from Realtime/Responses output."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


def parse_tool_output(response: Any, tool_name: str) -> Dict[str, str]:
	"""Return the arguments for the specified tool call."""
	for item in getattr(response, "output", []):
		if getattr(item, "type", None) != "function_call":
			continue
		if getattr(item, "name", None) != tool_name:
			continue
		args = json.loads(getattr(item, "arguments", "{}") or "{}")
		return {
			"label": args.get("label", ""),
			"reasoning": args.get("reasoning", ""),
			"description": args.get("image_description", ""),
		}
	raise RuntimeError(f"No function_call output for '{tool_name}' found in response.")


def extract_text(response: Any) -> str:
	"""Extract the first output_text entry from the response."""
	for item in getattr(response, "output", []):
		if getattr(item, "type", None) != "message":
			continue
		for content in getattr(item, "content", []):
			if content.get("type") == "output_text":
				return content.get("text", "")
	return getattr(response, "output_text", "") or ""


def extract_usage(response: Any) -> Dict[str, Optional[int]]:
	"""Return token usage if present."""
	usage = getattr(response, "usage", None)
	return {
		"input_tokens": getattr(usage, "input_tokens", None) if usage else None,
		"output_tokens": getattr(usage, "output_tokens", None) if usage else None,
	}
