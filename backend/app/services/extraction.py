"""Per-format text extraction, isolated behind one registry.

Ticket 06 ships the text formats (TXT, Markdown, JSON). Later tickets register
PDF and DOCX extractors here without touching the ingestion pipeline.

Detection sniffs the *content*, never the client-supplied extension: a ``.txt``
file whose bytes start with ``%PDF-`` is treated as a PDF, not as text.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable

_MAGIC: list[tuple[bytes, str]] = [
    (b"%PDF-", "pdf"),
    (b"PK\x03\x04", "docx"),
]

CONTENT_TYPES = {
    "text": "text/plain",
    "markdown": "text/markdown",
    "json": "application/json",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

_MD_HEADING = re.compile(r"(?m)^#{1,6}\s+\S")
_MD_FENCE = re.compile(r"(?m)^```")
_ATX = re.compile(r"^(#{1,6})\s+(.*)$")


class UnsupportedFileType(Exception):
    """The sniffed content is a type we cannot ingest."""


class NoExtractableText(Exception):
    """The content was understood but yielded nothing usable."""


@dataclass(frozen=True)
class TextBlock:
    text: str
    locator: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Extraction:
    kind: str
    content_type: str
    blocks: list[TextBlock]


def decode_text(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UnsupportedFileType("File is not UTF-8 text (binary content rejected)") from exc


def detect_kind(content: bytes) -> str:
    for magic, kind in _MAGIC:
        if content.startswith(magic):
            return kind

    text = decode_text(content)
    stripped = text.lstrip()
    if stripped[:1] in ("{", "["):
        try:
            json.loads(text)
        except ValueError as exc:
            raise UnsupportedFileType("File looks like JSON but is not valid JSON") from exc
        return "json"
    if _MD_HEADING.search(text) or _MD_FENCE.search(text):
        return "markdown"
    return "text"


def _extract_text(content: bytes, filename: str) -> list[TextBlock]:
    return [TextBlock(text=decode_text(content).strip(), locator={})]


def _extract_markdown(content: bytes, filename: str) -> list[TextBlock]:
    text = decode_text(content)
    blocks: list[TextBlock] = []
    heading: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        section = "\n".join(buffer).strip()
        if section:
            locator = {"section": heading} if heading else {}
            blocks.append(TextBlock(text=section, locator=locator))

    for line in text.splitlines():
        match = _ATX.match(line)
        if match:
            flush()
            heading = match.group(2).strip()
            buffer = [heading]
        else:
            buffer.append(line)
    flush()
    return blocks


def _flatten(node, prefix: str, out: list[tuple[str, object]]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            _flatten(value, f"{prefix}.{key}" if prefix else str(key), out)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _flatten(value, f"{prefix}[{index}]", out)
    else:
        out.append((prefix, node))


def _render(value: object) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def _extract_json(content: bytes, filename: str) -> list[TextBlock]:
    data = json.loads(decode_text(content))
    leaves: list[tuple[str, object]] = []
    _flatten(data, "", leaves)
    return [TextBlock(text=f"{path}: {_render(value)}", locator={"path": path}) for path, value in leaves]


_EXTRACTORS: dict[str, Callable[[bytes, str], list[TextBlock]]] = {
    "text": _extract_text,
    "markdown": _extract_markdown,
    "json": _extract_json,
}


def register_extractor(kind: str, extractor: Callable[[bytes, str], list[TextBlock]]) -> None:
    """Add a format (e.g. PDF, DOCX) without editing the ingestion pipeline."""
    _EXTRACTORS[kind] = extractor


def is_supported(kind: str) -> bool:
    return kind in _EXTRACTORS


def extract(content: bytes, filename: str = "") -> Extraction:
    kind = detect_kind(content)
    extractor = _EXTRACTORS.get(kind)
    if extractor is None:
        raise UnsupportedFileType(f"Unsupported file type: {kind.upper()}")

    blocks = [b for b in extractor(content, filename) if b.text and b.text.strip()]
    if not blocks:
        raise NoExtractableText("No extractable text — this file may be a scan")
    return Extraction(kind=kind, content_type=CONTENT_TYPES[kind], blocks=blocks)


# Import for the side effect of registering the PDF/DOCX extractors. Kept last
# to avoid a circular import at module load.
from . import pdf_docx  # noqa: E402,F401
