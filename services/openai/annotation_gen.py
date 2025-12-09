"""Operative note helper using the OpenAI Responses API.

Given a set of image records and a user-provided operative note template,
this module assembles a clear, clinician-friendly operative note in
Markdown. The generator leans on the image descriptions and user
documentation to fill in missing details while preserving the provided
template structure.
"""

import logging
import time
from typing import List, Optional

from openai import AsyncOpenAI

from models.image_record import ImageRecord


class OperativeNoteGenerator:
    """Create an operative note from images and a user template."""

    SYSTEM_PROMPT = (
        "You are an experienced GI endoscopist and skilled medical writer. "
        "When provided with image details and a user template, produce a clear, "
        "structured operative note in Markdown."
    )

    USER_INSTRUCTIONS = """You'll get two things:
        1) An operative note template from the user (may be empty or partial)
        2) A list of images, each with generated label, description, reasoning, and any user-provided documentation.

        Please:
        - Use the template as the base structure. Preserve existing content and headings.
        - Keep Findings and Assessment concise and grounded in the supplied data.
        - Under 'Images and Annotations' include the supplied image details.
        - Return only the Markdown note (no explanatory text).
        """

    def __init__(self, client: AsyncOpenAI) -> None:
        if client is None:
            raise ValueError("OpenAI AsyncOpenAI client is required.")
        self.client = client

    async def generate_opnote(
        self,
        images: List[ImageRecord],
        base_opnote: Optional[str] = None,
        template: Optional[str] = None,
    ) -> str:
        """Generate a completed operative note from image records.

        Args:
            images: List of ImageRecord objects.
            base_opnote: User-provided operative note text (used as the template).
            template: Optional template override (defaults to base_opnote).
            max_output_tokens: LLM token limit.

        Returns:
            A final operative note in markdown.
        """
        start = time.time()

        template_text = (template if template is not None else base_opnote) or ""
        template_text = template_text.strip()

        image_sections = [
            self._format_image_block(index, image) for index, image in enumerate(images, start=1)
        ]
        image_details = "\n\n".join(image_sections) if image_sections else "No images provided."

        context_parts = []
        if template_text:
            context_parts.append("## User-Provided Operative Note Template\n" + template_text)
        context_parts.append("## Image Details\n" + image_details)

        context_note = "\n\n".join(context_parts)

        try:
            response = await self.client.responses.create(
                model="gpt-5",
                input=[
                    {
                        "type": "message",
                        "role": "system",
                        "content": [{"type": "input_text", "text": self.SYSTEM_PROMPT}],
                    },
                    {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": self.USER_INSTRUCTIONS}],
                    },
                    {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": context_note}],
                    },
                ],
            )
        except Exception as exc:
            logging.error(f"OpenAI Responses API error: {exc}")
            raise

        md_output = self._extract_markdown(response)

        latency = time.time() - start
        logging.info(f"Operative note generation latency: {latency:.3f}s")

        return md_output

    @staticmethod
    def _extract_markdown(response) -> str:
        """Pull the markdown text out of a Responses API result."""
        try:
            for item in response.output:
                if getattr(item, "type", None) != "message":
                    continue
                for content in getattr(item, "content", []):
                    if content.get("type") == "output_text":
                        return content.get("text")
        except Exception as exc:
            logging.error(f"Error parsing response output: {exc}")

        return getattr(response, "output_text", None) or str(response)

    @staticmethod
    def _format_image_block(index: int, image: ImageRecord) -> str:
        """Format a single image entry for the model context."""
        label = image.label or "Not provided"
        description = image.image_description or "Not provided"
        reasoning = image.reasoning or "Not provided"
        documentation = image.user_documentation or "Not provided"
        image_id = f" (ID {image.id})" if image.id is not None else ""

        lines = [
            f"Image {index}{image_id}",
            f"Generated Label: {label}",
            f"Generated Description: {description}",
            f"Generated Reasoning: {reasoning}",
            f"User Provided Documentation: {documentation}",
        ]
        return "\n".join(lines)
