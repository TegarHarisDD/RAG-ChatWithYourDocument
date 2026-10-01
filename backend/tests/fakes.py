"""Deterministic test doubles for the injected ports.

The fake embedder maps text to a stable vector, so the same input always
produces the same vector and similarity ordering is reproducible without
calling a real provider.
"""

from __future__ import annotations

import asyncio
import hashlib
import math

from app.services.chat_model import ChatModelError


class FakeEmbedder:
    def __init__(self, model: str = "fake-embedding", dimensions: int = 64) -> None:
        self.model = model
        self.dimensions = dimensions
        self.calls: list[list[str]] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            vector[digest[0] % self.dimensions] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class FlakyEmbedder(FakeEmbedder):
    """Fails the first ``failures`` calls, then behaves like FakeEmbedder."""

    def __init__(self, failures: int = 1, **kwargs) -> None:
        super().__init__(**kwargs)
        self.remaining_failures = failures

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if self.remaining_failures > 0:
            self.remaining_failures -= 1
            raise RuntimeError("embedding provider temporarily unavailable")
        return await super().embed(texts)


class ScriptedChatModel:
    """Records the prompt it was given and emits a canned stream."""

    model = "scripted-model"

    def __init__(
        self,
        script: list[str] | None = None,
        fail_attempts: int = 0,
        error: Exception | None = None,
        fail_after: int | None = None,
        delay: float = 0.0,
    ) -> None:
        self.script = script if script is not None else ["The answer is ", "in the context [1]."]
        self.remaining_failures = fail_attempts
        self.error = error or ChatModelError("rate limited", status=429, retryable=True)
        self.fail_after = fail_after
        self.delay = delay
        self.prompts: list[list[dict]] = []
        self.last_finish_reason: str | None = None

    async def stream(self, messages: list[dict]):
        self.prompts.append(messages)
        self.last_finish_reason = None
        if self.remaining_failures > 0:
            self.remaining_failures -= 1
            raise self.error
        for index, piece in enumerate(self.script):
            if self.delay:
                await asyncio.sleep(self.delay)
            if self.fail_after is not None and index == self.fail_after:
                raise self.error
            yield piece
        self.last_finish_reason = "stop"
