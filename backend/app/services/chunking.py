"""Chunking: slices extracted text into retrieval units.

Each chunk carries its order within the document and the locator of the block
it came from, so a later citation can point at a real place in the file.
"""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from .extraction import TextBlock


def build_splitter(chunk_size: int, chunk_overlap: int) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )


def chunk_blocks(
    blocks: list[TextBlock],
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict]:
    splitter = build_splitter(chunk_size, chunk_overlap)
    chunks: list[dict] = []
    index = 0
    for block in blocks:
        for piece in splitter.split_text(block.text):
            piece = piece.strip()
            if not piece:
                continue
            chunks.append(
                {
                    "chunk_index": index,
                    "text": piece,
                    "locator": dict(block.locator),
                }
            )
            index += 1
    return chunks
