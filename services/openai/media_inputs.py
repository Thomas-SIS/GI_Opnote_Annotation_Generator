"""Utilities to build multimodal input payloads for the Responses API."""

from typing import Any, Dict, List, Optional


def to_image_data_url(image_bytes: bytes) -> str:
    """Convert base64 image bytes into a data URL suitable for vision input."""
    try:
        b64_str = image_bytes.decode("utf-8")
    except Exception as exc:
        raise ValueError("Image bytes must be base64-encoded UTF-8.") from exc
    # Debug: indicate that an image was provided and converted
    if b64_str:
        print("image added")
    return f"data:image/jpeg;base64,{b64_str}"


def build_user_content(
    image_url: str, text_input: Optional[str], audio_transcript: Optional[str]
) -> List[Dict[str, Any]]:
    """Compose user messages so each modality is a distinct input entry."""
    messages: List[Dict[str, Any]] = []
    if text_input:
        # Debug: indicate that text input was provided
        print("Text added")
        messages.append(
            {"type": "message", "role": "user", "content": [{"type": "input_text", "text": text_input}]}
        )
    if audio_transcript:
        print("Audio transcript added")
        messages.append(
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": f"Audio narration (transcribed): {audio_transcript}"}],
            },
        )

    messages.append(
        {"type": "message", "role": "user", "content": [{"type": "input_image", "image_url": image_url}]}
    )
    return messages


def build_inputs(
    system_prompt: str,
    user_prompt: str,
    *,
    text_input: Optional[str],
    audio_transcript: Optional[str],
    image_bytes: bytes,
) -> List[Dict[str, Any]]:
    """Build the Responses API input array with each modality separated."""
    image_url = to_image_data_url(image_bytes)
    inputs: List[Dict[str, Any]] = [
        {
            "type": "message",
            "role": "system",
            "content": [{"type": "input_text", "text": system_prompt}],
        },
        {"type": "message", "role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
    ]
    inputs.extend(build_user_content(image_url, text_input, audio_transcript))
    return inputs
