"""Atlas Vector Search adapter (ticket 09).

Reads the same ``chunks`` collection the local adapter writes, through the
``$vectorSearch`` aggregation stage. Session scoping is a filter on the search
itself rather than a post-filter, so a query can never cross into another
session's chunks. Selected by ``VECTOR_STORE_BACKEND=atlas``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..db import Database


class AtlasVectorStore:
    def __init__(self, db: Database, index_name: str, num_candidates: int = 100) -> None:
        self._db = db
        self._index = index_name
        self._num_candidates = num_candidates

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
        pipeline = [
            {
                "$vectorSearch": {
                    "index": self._index,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": max(self._num_candidates, k),
                    "limit": k,
                    "filter": {"session_id": session_id},
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "document_id": 1,
                    "chunk_index": 1,
                    "text": 1,
                    "locator": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        return [
            {
                "chunk_id": str(row["_id"]),
                "document_id": row["document_id"],
                "chunk_index": row["chunk_index"],
                "text": row["text"],
                "locator": row.get("locator", {}),
                "score": row.get("score", 0.0),
            }
            async for row in self._db.db.chunks.aggregate(pipeline)
        ]
