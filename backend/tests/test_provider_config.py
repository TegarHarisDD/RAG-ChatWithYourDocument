"""A missing OpenRouter key must fail clearly, not with a header error."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.services.chat_model import ChatModelError, OpenRouterChatModel
from app.services.embeddings import EmbeddingError, OpenRouterEmbedder


async def test_embedder_without_key_reports_a_clear_reason():
    embedder = OpenRouterEmbedder(Settings(openrouter_api_key=""))
    with pytest.raises(EmbeddingError) as excinfo:
        await embedder.embed(["hello"])
    assert "OPENROUTER_API_KEY" in str(excinfo.value)
    await embedder.aclose()


async def test_chat_model_without_key_reports_a_clear_reason():
    model = OpenRouterChatModel(Settings(openrouter_api_key=""))
    with pytest.raises(ChatModelError) as excinfo:
        async for _ in model.stream([{"role": "user", "content": "hi"}]):
            pass
    assert "OPENROUTER_API_KEY" in str(excinfo.value)
    await model.aclose()
