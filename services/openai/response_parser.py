"""Helpers to parse Responses API outputs."""

import json
from typing import Any, Dict, Optional


def parse_function_call(response: Any, *, tool_name: str) -> Dict[str, str]:
    """Extract the function call arguments for the specified tool name."""
    for item in getattr(response, "output", []):
        if getattr(item, "type", None) == "function_call" and getattr(item, "name", None) == tool_name:
            args = json.loads(getattr(item, "arguments", "{}") or "{}")
            return {
                "label": args.get("label", ""),
                "reasoning": args.get("reasoning", ""),
                "image_description": args.get("image_description", ""),
            }
    raise RuntimeError(f"No function_call output for '{tool_name}' found in Responses API output.")


def extract_usage(response: Any) -> Dict[str, Optional[int]]:
    """Return token usage information from the response, if present."""
    usage = getattr(response, "usage", None)
    return {
        "input_tokens": getattr(usage, "input_tokens", None) if usage else None,
        "output_tokens": getattr(usage, "output_tokens", None) if usage else None,
    }
