"""Streamed grounded answering (tickets 10-13).

Sequences: persist the user message, retrieve the session's chunks, short-
circuit on guardrails, stream the model with retry/backoff, resolve citations
server-side, and persist the assistant reply. Yields typed events for the SSE
endpoint to format.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import AsyncIterator

from bson import ObjectId

from ..config import Settings
from ..db import Database
from . import retrieval, titles
from .chat_model import ChatModelError
from .ports import ChatModel, Embedder, VectorStore
from .prompt import build_messages

_CITATION = re.compile(r"\[(\d+)\]")

GUARDRAIL_NO_DOCUMENTS = (
    "This session has no ready documents yet. Upload a document first, then ask again."
)
GUARDRAIL_NOTHING_RELEVANT = (
    "I could not find anything relevant in this session's documents to answer that."
)
MODEL_UNAVAILABLE = (
    "The model is unavailable right now. Your question was saved — please try again."
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _backoff(settings: Settings, attempt: int) -> float:
    return min(settings.model_retry_max_seconds, settings.model_retry_base_seconds * (2 ** (attempt - 1)))


async def _persist_user(db: Database, chat_id: str, session_id: str, content: str) -> dict:
    now = _now()
    doc = {
        "chat_id": chat_id,
        "session_id": session_id,
        "role": "user",
        "content": content,
        "citations": [],
        "model": None,
        "finish_reason": None,
        "created_at": now,
    }
    result = await db.db.messages.insert_one(doc)
    doc["_id"] = result.inserted_id
    await db.db.chats.update_one({"_id": ObjectId(chat_id)}, {"$set": {"last_active_at": now}})
    await db.db.sessions.update_one(
        {"_id": ObjectId(session_id)}, {"$set": {"last_active_at": now}}
    )
    await _maybe_autotitle(db, session_id, chat_id, content)
    return doc


async def _maybe_autotitle(
    db: Database, session_id: str, chat_id: str, content: str
) -> None:
    """Name an unnamed session from its first question."""
    if await db.db.messages.count_documents({"chat_id": chat_id}) != 1:
        return
    session = await db.db.sessions.find_one({"_id": ObjectId(session_id)}, {"title": 1})
    if not session or session.get("title") != titles.DEFAULT_TITLE:
        return
    await db.db.sessions.update_one(
        {"_id": ObjectId(session_id)}, {"$set": {"title": titles.derive_title(content)}}
    )


async def _persist_assistant(
    db: Database,
    chat_id: str,
    session_id: str,
    content: str,
    citations: list[dict],
    model: str | None,
    finish_reason: str,
) -> str:
    doc = {
        "chat_id": chat_id,
        "session_id": session_id,
        "role": "assistant",
        "content": content,
        "citations": citations,
        "model": model,
        "finish_reason": finish_reason,
        "created_at": _now(),
    }
    result = await db.db.messages.insert_one(doc)
    return str(result.inserted_id)


async def _ready_document_count(db: Database, session_id: str) -> int:
    return await db.db.documents.count_documents({"session_id": session_id, "status": "ready"})


async def _build_sources(db: Database, rows: list[dict], settings: Settings) -> list[dict]:
    document_ids = list({row["document_id"] for row in rows})
    names: dict[str, str] = {}
    if document_ids:
        cursor = db.db.documents.find({"_id": {"$in": [ObjectId(i) for i in document_ids]}})
        async for document in cursor:
            names[str(document["_id"])] = document["filename"]

    sources: list[dict] = []
    total = 0
    for row in rows:
        text = row["text"]
        if sources and total + len(text) > settings.rag_context_max_chars:
            break
        if not sources:
            text = text[: settings.rag_context_max_chars]
        sources.append(
            {
                "index": len(sources) + 1,
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "filename": names.get(row["document_id"], "document"),
                "chunk_index": row["chunk_index"],
                "locator": row.get("locator", {}),
                "text": text,
            }
        )
        total += len(text)
    return sources


def _public_source(source: dict) -> dict:
    return {
        "index": source["index"],
        "chunk_id": source["chunk_id"],
        "document_id": source["document_id"],
        "filename": source["filename"],
        "chunk_index": source["chunk_index"],
        "locator": source["locator"],
        "snippet": source["text"][:280],
    }


def resolve_citations(answer: str, sources: list[dict]) -> list[dict]:
    """Map ``[n]`` markers in the answer to the chunks actually supplied."""
    by_index = {source["index"]: source for source in sources}
    seen: list[int] = []
    for match in _CITATION.finditer(answer):
        index = int(match.group(1))
        if index in by_index and index not in seen:
            seen.append(index)
    return [
        {
            "index": index,
            "chunk_id": by_index[index]["chunk_id"],
            "document_id": by_index[index]["document_id"],
            "filename": by_index[index]["filename"],
            "chunk_index": by_index[index]["chunk_index"],
            "locator": by_index[index]["locator"],
            "snippet": by_index[index]["text"][:280],
        }
        for index in seen
    ]


async def _guardrail(
    db: Database, chat_id: str, session_id: str, reason: str, message: str
) -> AsyncIterator[dict]:
    message_id = await _persist_assistant(db, chat_id, session_id, message, [], None, reason)
    yield {"event": "guardrail", "data": {"reason": reason, "message": message, "message_id": message_id}}
    yield {"event": "done", "data": {"finish_reason": reason, "message_id": message_id}}


async def stream_answer(
    chat_id: str,
    session_id: str,
    question: str,
    *,
    db: Database,
    vector_store: VectorStore,
    embedder: Embedder,
    chat_model: ChatModel,
    settings: Settings,
) -> AsyncIterator[dict]:
    user_message = await _persist_user(db, chat_id, session_id, question)
    yield {
        "event": "user",
        "data": {
            "message_id": str(user_message["_id"]),
            "content": question,
            "created_at": user_message["created_at"].isoformat(),
        },
    }

    if await _ready_document_count(db, session_id) == 0:
        async for event in _guardrail(
            db, chat_id, session_id, "no_documents", GUARDRAIL_NO_DOCUMENTS
        ):
            yield event
        return

    try:
        rows = await retrieval.retrieve(
            db,
            vector_store,
            embedder,
            session_id,
            question,
            settings.retrieval_top_k,
            min_score=settings.retrieval_min_score,
        )
    except retrieval.RetrievalError as exc:
        yield {"event": "error", "data": {"reason": "retrieval_error", "message": str(exc)}}
        return

    if not rows:
        async for event in _guardrail(
            db, chat_id, session_id, "nothing_relevant", GUARDRAIL_NOTHING_RELEVANT
        ):
            yield event
        return

    sources = await _build_sources(db, rows, settings)
    yield {"event": "sources", "data": {"sources": [_public_source(s) for s in sources]}}

    messages = build_messages(question, sources)
    answer: list[str] = []
    attempts = 0

    try:
        while True:
            try:
                async for delta in chat_model.stream(messages):
                    answer.append(delta)
                    yield {"event": "token", "data": {"text": delta}}
                break
            except ChatModelError as exc:
                if exc.retryable and not answer and attempts < settings.model_max_retries:
                    attempts += 1
                    await asyncio.sleep(_backoff(settings, attempts))
                    continue
                message = MODEL_UNAVAILABLE if exc.retryable else str(exc)
                yield {"event": "error", "data": {"reason": "model_unavailable", "message": message}}
                return
            except Exception:
                if not answer and attempts < settings.model_max_retries:
                    attempts += 1
                    await asyncio.sleep(_backoff(settings, attempts))
                    continue
                yield {"event": "error", "data": {"reason": "model_unavailable", "message": MODEL_UNAVAILABLE}}
                return
    except (asyncio.CancelledError, GeneratorExit):
        partial = "".join(answer)
        if partial.strip():
            citations = resolve_citations(partial, sources)
            await _persist_assistant(db, chat_id, session_id, partial, citations, chat_model.model, "stopped")
        raise

    text = "".join(answer)
    citations = resolve_citations(text, sources)
    finish_reason = getattr(chat_model, "last_finish_reason", None) or "stop"
    message_id = await _persist_assistant(
        db, chat_id, session_id, text, citations, chat_model.model, finish_reason
    )
    yield {"event": "citations", "data": {"citations": citations}}
    yield {"event": "done", "data": {"finish_reason": finish_reason, "message_id": message_id}}
