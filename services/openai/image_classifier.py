"""
Description: Image classification service using OpenAI's Responses API.
"""

import logging
import time
import json
from typing import Any, Dict

from openai import AsyncOpenAI  # modern SDK


class ImageClassifier:
    """
    Class for classifying images using OpenAI's gpt-5 model (Responses API).
    """

    def __init__(self, client: AsyncOpenAI) -> None:
        """
        Initialize the ImageClassifier with an OpenAI async client.

        Args:
            client: An instance of openai.AsyncOpenAI.
        """
        if client is None:
            raise ValueError("OpenAI client must be provided.")
        self.client = client

        # Labels for classification
        self.labels = [
            "Proximal esophagus",
            "Mid esophagus",
            "Distal esophagus",
            "Z-line",
            "Gastroesophageal junction (GEJ)",
            "Cardia",
            "Fundus",
            "Body",
            "Incisura angularis",
            "Antrum",
            "Pylorus",
            "Duodenal bulb (D1)",
            "Second portion of duodenum (D2)",
            "Third portion (D3)",
            "Fourth portion (D4)",
            "Cecum",
            "Ascending colon",
            "Hepatic flexure",
            "Transverse colon",
            "Splenic flexure",
            "Descending colon",
            "Sigmoid colon",
            "Rectum",
            "Terminal ileum",
            "Anorectal junction",
        ]

        # System prompt defining the model's behavior
        self.system_prompt = (
            "You are an expert gastroenterologist specializing in endoscopy. "
            "You are careful, conservative, and avoid over-calling pathology."
        )

        # User prompt
        self.user_prompt = (
            "Classify the following endoscopic image into one of the predefined anatomical locations. "
            "Provide the label and a concise clinical reasoning for your choice. "
            "Include a written description of the image for annotation and findings documentation."
        )

        # Name for the function tool
        self.tool_name: str = "classify_endoscopic_image"

        # JSON Schema for the function parameters (flattened as required by Responses API)
        self.function_parameters: Dict[str, Any] = {
            "type": "object",
            "properties": {
                "label": {
                    "type": "string",
                    "description": "One of the predefined anatomical locations.",
                    "enum": self.labels,
                },
                "reasoning": {
                    "type": "string",
                    "description": "Concise clinical reasoning supporting the chosen label.",
                },
                "image_description": {
                    "type": "string",
                    "description": "A written description of the image for annotation purposes.",
                },
            },
            "required": ["label", "reasoning", "image_description"],
            "additionalProperties": False,
        }

    # end of __init__

    async def classify_image(self, image_bytes: bytes) -> dict:
        """
        Use OpenAI's GPT-5 model to classify the endoscopic image via the Responses API.

        Args:
            image_bytes: base64-encoded bytes of the image to classify.

        Returns:
            {
                "label": str,
                "reasoning": str,
                "image_description": str,
                "input_tokens": int | None,
                "output_tokens": int | None,
                "latency": float,
            }
        """
        start_time = time.time()

        # Convert base64 bytes -> data URL for vision input
        try:
            b64_str = image_bytes.decode("utf-8")
        except Exception as e:
            logging.error(f"Failed to decode image bytes as UTF-8/base64 string: {e}")
            raise

        data_url = f"data:image/jpeg;base64,{b64_str}"

        try:
            # Modern Responses API: `input` is an array of input items (messages, images, etc.)
            response = await self.client.responses.create(
                model="gpt-5",
                input=[
                    {
                        "type": "message",
                        "role": "system",
                        "content": [
                            {"type": "input_text", "text": self.system_prompt},
                        ],
                    },
                    {
                        "type": "message",
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": self.user_prompt},
                            {
                                "type": "input_image",
                                "image_url": data_url,
                            },
                        ],
                    },
                ],
                tools=[
                    {
                        "type": "function",
                        "name": self.tool_name,
                        "description": (
                            "Return the anatomical label, reasoning, and description "
                            "for the classification."
                        ),
                        "parameters": self.function_parameters,
                        "strict": True,
                    }
                ],
                # Force the model to call this specific function/tool.
                # ToolChoiceFunction shape: { "type": "function", "name": "<tool name>" }
                tool_choice={
                    "type": "function",
                    "name": self.tool_name,
                },
            )
        except Exception as e:
            logging.error(f"Error during OpenAI Responses API call: {e}")
            raise

        latency = time.time() - start_time

        # Parse function_call output from Responses API
        try:
            function_call = None
            for item in response.output:
                if getattr(item, "type", None) == "function_call" and getattr(
                    item, "name", None
                ) == self.tool_name:
                    function_call = item
                    break

            if function_call is None:
                raise RuntimeError(
                    "No function_call output for "
                    f"'{self.tool_name}' found in Responses API output."
                )

            # `arguments` is a JSON string per the function-calling docs.
            args = json.loads(function_call.arguments or "{}")
            label = args.get("label", "")
            reasoning = args.get("reasoning", "")
            image_description = args.get("image_description", "")

            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "input_tokens", None) if usage else None
            output_tokens = getattr(usage, "output_tokens", None) if usage else None

        except Exception as e:
            logging.error(f"Error parsing OpenAI response: {e}")
            logging.error(f"Full response object: {response!r}")
            raise

        if not label or not reasoning or not image_description:
            logging.error("Incomplete classification output received from OpenAI.")
            # Keep this print if you like, or swap to logging.debug
            print(response)

        return {
            "label": label,
            "reasoning": reasoning,
            "image_description": image_description,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency": latency,
        }

    # end of classify_image

# end of ImageClassifier
