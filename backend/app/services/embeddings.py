"""OpenRouter embedding adapter (OpenAI-shaped ``/embeddings`` endpoint)."""

from __future__ import annotations

import httpx

from ..config import Settings


class EmbeddingError(Exception):
    """The embedding provider could not produce vectors."""


class OpenRouterEmbedder:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions
        self._api_key = (settings.openrouter_api_key or "").strip()
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        self._client = httpx.AsyncClient(
            base_url=settings.openrouter_base_url,
            timeout=settings.embedding_timeout_seconds,
            headers=headers,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self._api_key:
            raise EmbeddingError(
                "OPENROUTER_API_KEY is not configured. Set it in .env to embed documents."
            )
        vectors: list[list[float]] = []
        batch_size = max(1, self._settings.embedding_batch_size)
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            # No "dimensions" parameter: it is OpenAI-proprietary and free
            # models (e.g. NVIDIA Nemotron) reject it. The model's native
            # dimension is detected from the response instead.
            response = await self._client.post(
                "/embeddings",
                json={"model": self.model, "input": batch},
            )
            if response.status_code >= 400:
                raise EmbeddingError(
                    f"Embedding provider returned {response.status_code}: {response.text[:200]}"
                )
            payload = response.json()
            data = sorted(payload.get("data", []), key=lambda row: row.get("index", 0))
            batch_vectors = [row["embedding"] for row in data]
            if batch_vectors and not self.dimensions:
                self.dimensions = len(batch_vectors[0])
            vectors.extend(batch_vectors)
        return vectors

    async def aclose(self) -> None:
        await self._client.aclose()
