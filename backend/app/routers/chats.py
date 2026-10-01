"""Chats: one conversation thread inside a session.

Nested list/create under a session; rename, delete, clear, and history by chat
id. Deleting a chat takes its messages but never the session's documents.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from ..deps import ChatModelDep, DatabaseDep, EmbedderDep, OwnerDep, SettingsDep, VectorStoreDep
from ..schemas import ChatCreate, ChatOut, ChatUpdate, MessageCreate, MessageOut
from ..services import cascade
from ..services.chat import stream_answer

router = APIRouter(tags=["chats"])

DEFAULT_TITLE = "New chat"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_id(value: str, detail: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _to_out(doc: dict) -> ChatOut:
    return ChatOut(
        id=str(doc["_id"]),
        session_id=doc["session_id"],
        title=doc["title"],
        created_at=doc["created_at"],
        last_active_at=doc["last_active_at"],
    )


async def _require_session(db, session_id: str) -> str:
    oid = _parse_id(session_id, "Session not found")
    if not await db.db.sessions.find_one({"_id": oid}, {"_id": 1}):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session_id


async def _require_chat(db, chat_id: str) -> dict:
    oid = _parse_id(chat_id, "Chat not found")
    doc = await db.db.chats.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return doc


@router.get("/api/sessions/{session_id}/chats", response_model=list[ChatOut])
async def list_chats(session_id: str, db: DatabaseDep, owner: OwnerDep):
    await _require_session(db, session_id)
    cursor = db.db.chats.find({"session_id": session_id}).sort(
        [("last_active_at", -1), ("created_at", -1)]
    )
    return [_to_out(doc) for doc in await cursor.to_list(length=None)]


@router.post(
    "/api/sessions/{session_id}/chats",
    response_model=ChatOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_chat(
    session_id: str, payload: ChatCreate, db: DatabaseDep, owner: OwnerDep
):
    await _require_session(db, session_id)
    now = _now()
    title = (payload.title or "").strip() or DEFAULT_TITLE
    doc = {"session_id": session_id, "title": title, "created_at": now, "last_active_at": now}
    result = await db.db.chats.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_out(doc)


@router.get("/api/chats/{chat_id}", response_model=ChatOut)
async def get_chat(chat_id: str, db: DatabaseDep, owner: OwnerDep):
    return _to_out(await _require_chat(db, chat_id))


@router.patch("/api/chats/{chat_id}", response_model=ChatOut)
async def rename_chat(
    chat_id: str, payload: ChatUpdate, db: DatabaseDep, owner: OwnerDep
):
    oid = _parse_id(chat_id, "Chat not found")
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Title is required")
    doc = await db.db.chats.find_one_and_update(
        {"_id": oid}, {"$set": {"title": title}}, return_document=True
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return _to_out(doc)


@router.delete("/api/chats/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(chat_id: str, db: DatabaseDep, owner: OwnerDep):
    doc = await _require_chat(db, chat_id)
    await cascade.delete_chat(db, chat_id, doc["session_id"])


@router.get("/api/chats/{chat_id}/messages", response_model=list[MessageOut])
async def list_messages(chat_id: str, db: DatabaseDep, owner: OwnerDep):
    await _require_chat(db, chat_id)
    cursor = db.db.messages.find({"chat_id": chat_id}).sort([("created_at", 1)])
    return [
        MessageOut(
            id=str(doc["_id"]),
            chat_id=doc["chat_id"],
            session_id=doc.get("session_id", ""),
            role=doc["role"],
            content=doc["content"],
            citations=doc.get("citations", []),
            created_at=doc["created_at"],
            model=doc.get("model"),
            finish_reason=doc.get("finish_reason"),
        )
        for doc in await cursor.to_list(length=None)
    ]


@router.delete("/api/chats/{chat_id}/messages", status_code=status.HTTP_204_NO_CONTENT)
async def clear_messages(
    chat_id: str,
    db: DatabaseDep,
    owner: OwnerDep,
    from_message_id: str | None = None,
):
    """Clear the thread, or truncate it from ``from_message_id`` onward."""
    await _require_chat(db, chat_id)

    if from_message_id is None:
        await cascade.clear_chat_messages(db, chat_id)
        return

    oid = _parse_id(from_message_id, "Message not found")
    message = await db.db.messages.find_one({"_id": oid, "chat_id": chat_id})
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    await db.db.messages.delete_many(
        {"chat_id": chat_id, "created_at": {"$gte": message["created_at"]}}
    )


@router.delete(
    "/api/chats/{chat_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_message(
    chat_id: str, message_id: str, db: DatabaseDep, owner: OwnerDep
):
    """Delete a message together with its pair (question <-> answer)."""
    await _require_chat(db, chat_id)
    oid = _parse_id(message_id, "Message not found")
    message = await db.db.messages.find_one({"_id": oid, "chat_id": chat_id})
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    ids = [message["_id"]]
    if message["role"] == "user":
        pair = await db.db.messages.find_one(
            {
                "chat_id": chat_id,
                "role": "assistant",
                "created_at": {"$gt": message["created_at"]},
            },
            sort=[("created_at", 1)],
        )
    else:
        pair = await db.db.messages.find_one(
            {
                "chat_id": chat_id,
                "role": "user",
                "created_at": {"$lt": message["created_at"]},
            },
            sort=[("created_at", -1)],
        )
    if pair:
        ids.append(pair["_id"])

    await db.db.messages.delete_many({"_id": {"$in": ids}})


def _sse(event: dict) -> str:
    return f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"


@router.post("/api/chats/{chat_id}/messages")
async def create_message(
    chat_id: str,
    payload: MessageCreate,
    db: DatabaseDep,
    vector_store: VectorStoreDep,
    embedder: EmbedderDep,
    chat_model: ChatModelDep,
    settings: SettingsDep,
    owner: OwnerDep,
):
    chat = await _require_chat(db, chat_id)
    question = payload.content.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Message is required"
        )

    async def events():
        async for event in stream_answer(
            chat_id,
            chat["session_id"],
            question,
            db=db,
            vector_store=vector_store,
            embedder=embedder,
            chat_model=chat_model,
            settings=settings,
        ):
            yield _sse(event)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
