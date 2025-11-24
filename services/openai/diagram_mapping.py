"""Helpers for diagram mapping data used by the image labeling service."""

import json
from typing import Any, Dict, List


def load_diagram_mapping(mapping_path: str) -> Dict[str, Dict[str, Any]]:
    """Load the diagram mapping JSON file from disk.

    Args:
        mapping_path: Filesystem path to the mapping JSON.

    Returns:
        Parsed diagram mapping keyed by label identifiers.
    """
    with open(mapping_path, "r", encoding="utf-8") as mapping_file:
        return json.load(mapping_file)


def build_tool_schema(diagram_mapping: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create the tool schema for selecting a diagram label via OpenAI.

    Args:
        diagram_mapping: Mapping of label keys to diagram metadata.

    Returns:
        A list containing one function tool definition for label selection.
    """
    mapping_keys = list(diagram_mapping.keys())
    return [
        {
            "type": "function",
            "function": {
                "name": "select_diagram_label",
                "description": "Select the best matching region label from the diagram mapping.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "label_key": {
                            "type": "string",
                            "enum": mapping_keys,
                            "description": "Key from the diagram_mapping.json that best matches the image.",
                        },
                        "rationale": {
                            "type": "string",
                            "description": "Reasoning for why the label matches what is visible in the image.",
                        },
                    },
                    "required": ["label_key", "rationale"],
                },
            },
        }
    ]
