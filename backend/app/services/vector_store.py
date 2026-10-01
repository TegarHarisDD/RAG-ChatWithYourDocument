"""Local vector store adapter.

Stores chunks (with their vectors) in the ``chunks`` collection and removes
them on cascade. Ticket 09 adds an Atlas adapter behind the same port; the
local adapter stays selectable for environments without an Atlas index.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from ..db import Database


class LocalVectorStore:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def index_document(
        self,
        session_id: str,
        document_id: str,
        chunks: list[dict],
        embedding_model: str,
    ) -> None:
        if not chunks:
            return
        now = datetime.now(timezone.utc)
        documents = [
            {
                "session_id": session_id,
                "document_id": document_id,
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"],
                "locator": chunk.get("locator", {}),
                "embedding": chunk["embedding"],
                "embedding_model": embedding_model,
                "created_at": now,
            }
            for chunk in chunks
        ]
        await self._db.db.chunks.insert_many(documents)

    async def delete_document(self, document_id: str) -> None:
        await self._db.db.chunks.delete_many({"document_id": document_id})

    async def delete_session(self, session_id: str) -> None:
        await self._db.db.chunks.delete_many({"session_id": session_id})

    async def query(self, session_id: str, query_embedding: list[float], k: int) -> list[dict]:
        cursor = self._db.db.chunks.find({"session_id": session_id})
        scored: list[tuple[float, dict]] = []
        async for chunk in cursor:
            score = _cosine(query_embedding, chunk.get("embedding") or [])
            scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "chunk_id": str(chunk["_id"]),
                "document_id": chunk["document_id"],
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"],
                "locator": chunk.get("locator", {}),
                "score": score,
            }
            for score, chunk in scored[:k]
        ]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(length))
    norm_a = math.sqrt(sum(value * value for value in a))
    norm_b = math.sqrt(sum(value * value for value in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)

