"""OpenRouter chat model adapter (OpenAI-shaped ``/chat/completions``, SSE)."""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from ..config import Settings


class ChatModelError(Exception):
    """Upstream chat model failed. ``retryable`` marks 429 / 5xx / transport."""

    def __init__(self, message: str, *, status: int | None = None, retryable: bool = False) -> None:
        super().__init__(message)
        self.status = status
        self.retryable = retryable


def _is_retryable_status(status: int) -> bool:
    return status == 429 or 500 <= status <= 599


class OpenRouterChatModel:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.model = settings.chat_model
        self.last_finish_reason: str | None = None
        self._api_key = (settings.openrouter_api_key or "").strip()
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        self._client = httpx.AsyncClient(
            base_url=settings.openrouter_base_url,
            timeout=settings.chat_timeout_seconds,
            headers=headers,
        )

    async def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        self.last_finish_reason = None
        if not self._api_key:
            raise ChatModelError(
                "OPENROUTER_API_KEY is not configured. Set it in .env to ask questions.",
                retryable=False,
            )
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": self._settings.chat_temperature,
            "max_tokens": self._settings.chat_max_tokens,
        }
        try:
            async with self._client.stream("POST", "/chat/completions", json=payload) as response:
                if response.status_code >= 400:
                    body = (await response.aread()).decode("utf-8", "replace")
                    raise ChatModelError(
                        f"Chat model returned {response.status_code}: {body[:200]}",
                        status=response.status_code,
                        retryable=_is_retryable_status(response.status_code),
                    )
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if chunk.get("error"):
                        raise ChatModelError(str(chunk["error"]), retryable=True)
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    choice = choices[0]
                    if choice.get("finish_reason"):
                        self.last_finish_reason = choice["finish_reason"]
                    delta = choice.get("delta") or {}
                    text = delta.get("content")
                    if text:
                        yield text
        except httpx.HTTPError as exc:
            raise ChatModelError(f"Could not reach the chat model: {exc}", retryable=True) from exc

    async def aclose(self) -> None:
        await self._client.aclose()
