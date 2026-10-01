"""Session title helpers.

The default title marks a session the user has not named yet; the first
question then supplies a readable label automatically.
"""

from __future__ import annotations

DEFAULT_TITLE = "Untitled session"


def derive_title(question: str, max_length: int = 60) -> str:
    """A short, single-line label drawn from the first question."""
    text = " ".join(question.split())
    if not text:
        return DEFAULT_TITLE
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    if " " in truncated:
        truncated = truncated[: truncated.rfind(" ")]
    return truncated.rstrip() + "…"
