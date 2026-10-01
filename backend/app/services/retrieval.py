"""Retrieval: embed a question and pull the session's top-k chunks.

Session scoping happens inside the vector store's query (a filter for Atlas, a
session match for the local adapter), never as a post-filter over results.
"""

from __future__ import annotations

from ..db import Database
from .ports import Embedder, VectorStore


class RetrievalError(Exception):
    """Retrieval cannot proceed — surfaced to the caller with a clear reason."""


async def _check_dimensions(db: Database, dimension: int) -> None:
    """Refuse to query when the query vector cannot match the stored index."""
    meta = await db.db.meta.find_one({"_id": "embedding"})
    if not meta:
        return
    recorded = meta.get("dimensions")
    if recorded and recorded != dimension:
        raise RetrievalError(
            "The configured embedding model produces "
            f"{dimension} dimensions but the stored index was built with "
            f"{recorded}; re-process this session's documents before querying."
        )


async def retrieve(
    db: Database,
    vector_store: VectorStore,
    embedder: Embedder,
    session_id: str,
    query: str,
    k: int,
    min_score: float = 0.0,
) -> list[dict]:
    vectors = await embedder.embed([query])
    if not vectors:
        return []
    await _check_dimensions(db, len(vectors[0]))
    results = await vector_store.query(session_id, vectors[0], k)
    return [row for row in results if float(row.get("score", 0.0)) >= min_score]
