"""Sessions: the topic workspace that owns documents and chats.

Ticket 03 covers create, list, and read; ticket 04 adds rename and the cascade
delete that later entities plug into.
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, status

from ..deps import DatabaseDep, OwnerDep, VectorStoreDep
from ..schemas import SessionCreate, SessionOut, SessionUpdate
from ..services import cascade
from ..services.titles import DEFAULT_TITLE

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

DEFAULT_CHAT_TITLE = "Conversation"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_id(session_id: str) -> ObjectId:
    try:
        return ObjectId(session_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")


async def _existing_chat_id(db, session_id: str) -> str | None:
    """The session's current conversation: the most recently active chat."""
    chat = await db.db.chats.find_one(
        {"session_id": session_id},
        sort=[("last_active_at", -1), ("created_at", -1)],
    )
    return str(chat["_id"]) if chat else None


async def _resolve_chat_id(db, session_id: str) -> str:
    """Return the session's conversation, creating it if the session predates
    the one-conversation-per-session flow."""
    existing = await _existing_chat_id(db, session_id)
    if existing:
        return existing
    now = _now()
    result = await db.db.chats.insert_one(
        {
            "session_id": session_id,
            "title": DEFAULT_CHAT_TITLE,
            "created_at": now,
            "last_active_at": now,
        }
    )
    return str(result.inserted_id)


async def _to_out(
    db, doc: dict, document_count: int | None = None, chat_id: str | None = None
) -> SessionOut:
    if document_count is None:
        document_count = await db.db.documents.count_documents({"session_id": str(doc["_id"])})
    return SessionOut(
        id=str(doc["_id"]),
        title=doc["title"],
        created_at=doc["created_at"],
        last_active_at=doc["last_active_at"],
        document_count=document_count,
        chat_id=chat_id,
    )


@router.get("", response_model=list[SessionOut])
async def list_sessions(db: DatabaseDep, owner: OwnerDep):
    cursor = db.db.sessions.find({}).sort([("last_active_at", -1), ("created_at", -1)])
    sessions = await cursor.to_list(length=None)
    counts = await _document_counts(db, [str(s["_id"]) for s in sessions])
    return [
        SessionOut(
            id=str(s["_id"]),
            title=s["title"],
            created_at=s["created_at"],
            last_active_at=s["last_active_at"],
            document_count=counts.get(str(s["_id"]), 0),
        )
        for s in sessions
    ]


async def _document_counts(db, session_ids: list[str]) -> dict[str, int]:
    if not session_ids:
        return {}
    pipeline = [
        {"$match": {"session_id": {"$in": session_ids}}},
        {"$group": {"_id": "$session_id", "count": {"$sum": 1}}},
    ]
    return {
        row["_id"]: row["count"]
        async for row in db.db.documents.aggregate(pipeline)
    }


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreate, db: DatabaseDep, owner: OwnerDep):
    now = _now()
    title = (payload.title or "").strip() or DEFAULT_TITLE
    doc = {"title": title, "created_at": now, "last_active_at": now}
    result = await db.db.sessions.insert_one(doc)
    doc["_id"] = result.inserted_id
    return SessionOut(
        id=str(result.inserted_id),
        title=title,
        created_at=now,
        last_active_at=now,
        document_count=0,
    )


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: str, db: DatabaseDep, owner: OwnerDep):
    oid = _parse_id(session_id)
    doc = await db.db.sessions.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    chat_id = await _resolve_chat_id(db, session_id)
    return await _to_out(db, doc, chat_id=chat_id)


@router.patch("/{session_id}", response_model=SessionOut)
async def rename_session(
    session_id: str, payload: SessionUpdate, db: DatabaseDep, owner: OwnerDep
):
    oid = _parse_id(session_id)
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Title is required")
    doc = await db.db.sessions.find_one_and_update(
        {"_id": oid}, {"$set": {"title": title}}, return_document=True
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    chat_id = await _existing_chat_id(db, session_id)
    return await _to_out(db, doc, chat_id=chat_id)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str, db: DatabaseDep, vector_store: VectorStoreDep, owner: OwnerDep):
    oid = _parse_id(session_id)
    doc = await db.db.sessions.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    await cascade.delete_session(db, vector_store, session_id)
