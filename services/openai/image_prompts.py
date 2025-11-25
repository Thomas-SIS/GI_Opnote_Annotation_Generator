"""Prompt builders for multimodal endoscopic classification."""

def build_system_prompt() -> str:
    """Return the system prompt for the classifier."""
    return (
        "You are an expert gastroenterologist specializing in endoscopy. "
        "You are careful, conservative, and avoid over-calling pathology. "
        "Use every modality provided (text notes, audio narration, and the image) "
        "to ground the classification. "
    )


def build_user_prompt(text_present: bool, audio_present: bool) -> str:
    """Return the user prompt tailored to available modalities."""
    supplements = []
    if text_present:
        supplements.append("text notes")
    if audio_present:
        supplements.append("audio narration")

    if supplements:
        supplement_text = f" along with the {', '.join(supplements)} provided"
    else:
        supplement_text = ""

    return (
        "Classify the following endoscopic image into one of the predefined anatomical locations. "
        "Provide the label and a concise clinical reasoning for your choice. "
        "Include a written description of the image for annotation and findings documentation. "
        f"Use the image{supplement_text} to inform your decision."
    )
