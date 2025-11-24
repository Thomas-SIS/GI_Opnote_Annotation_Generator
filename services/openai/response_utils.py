"""Utilities for parsing and serializing OpenAI image label responses."""

from typing import Any, Dict, Optional


def extract_first_tool_call(response: Any) -> Optional[Dict[str, Any]]:
    """Return the first tool call from a responses API payload if present.

    Args:
        response: Response object returned by `OpenAI.responses.create`.

    Returns:
        The first tool call dictionary, or None when unavailable.
    """
    output = getattr(response, "output", None)
    if not output:
        return None

    contents = getattr(output[0], "content", None)
    if not contents:
        return None

    for content in contents:
        if getattr(content, "type", None) == "tool_calls":
            tool_calls = getattr(content, "tool_calls", None) or []
            return tool_calls[0] if tool_calls else None

    return None


def serialize_response(response: Any) -> Any:
    """Convert a response object into a serializable structure."""
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if hasattr(response, "to_dict"):
        return response.to_dict()
    return str(response)
