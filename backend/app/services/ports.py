"""Dependency ports for ingestion and retrieval.

These protocols are the seams the application is built around. Production wires
the OpenRouter embedder and the Mongo-backed vector store; tests can inject
deterministic fakes without a second test seam.
"""

from __future__ import annotations

from typing import AsyncIterator, Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    """Turns text into vectors with one fixed model."""

    model: str
    dimensions: int

    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...


@runtime_checkable
class VectorStore(Protocol):
    """Stores and removes chunk vectors, scoped to sessions and documents."""

    async def index_document(
        self,
        session_id: str,
        document_id: str,
        chunks: list[dict],
        embedding_model: str,
    ) -> None:
        ...

    async def delete_document(self, document_id: str) -> None:
        ...

    async def delete_session(self, session_id: str) -> None:
        ...

    async def query(
        self, session_id: str, query_embedding: list[float], k: int
    ) -> list[dict]:
        """Return the top-k chunks for one session, best match first."""
        ...


@runtime_checkable
class ChatModel(Protocol):
    """Streams an answer token by token for a chat prompt."""

    model: str

    def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        ...

