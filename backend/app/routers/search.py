"""Cross-session message search (command palette).

A case-insensitive substring match over message content. The corpus is small
(single owner), so an unanchored regex scan is used instead of a text index —
this keeps the endpoint working on any MongoDB backend with no index setup.
"""

from __future__ import annotations

import re

from bson import ObjectId
from fastapi import APIRouter

from ..deps import DatabaseDep, OwnerDep
from ..schemas import MessageSearchResultOut

router = APIRouter(tags=["search"])


def _snippet(content: str, query: str, radius: int = 60) -> str:
    text = " ".join(content.split())
    index = text.lower().find(query.lower())
    if index == -1:
        return text[: radius * 2].strip()
    start = max(0, index - radius)
    end = min(len(text), index + len(query) + radius)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


@router.get("/api/search/messages", response_model=list[MessageSearchResultOut])
async def search_messages(
    q: str, db: DatabaseDep, owner: OwnerDep, limit: int = 20
):
    query = q.strip()
    if not query:
        return []

    limit = max(1, min(limit, 50))
    cursor = (
        db.db.messages.find({"content": {"$regex": re.escape(query), "$options": "i"}})
        .sort("created_at", -1)
        .limit(limit)
    )
    messages = await cursor.to_list(length=limit)

    session_ids = list({m.get("session_id") for m in messages if m.get("session_id")})
    titles: dict[str, str] = {}
    if session_ids:
        async for session in db.db.sessions.find(
            {"_id": {"$in": [ObjectId(s) for s in session_ids]}}, {"title": 1}
        ):
            titles[str(session["_id"])] = session.get("title", "")

    return [
        MessageSearchResultOut(
            message_id=str(message["_id"]),
            chat_id=message["chat_id"],
            session_id=message.get("session_id", ""),
            session_title=titles.get(message.get("session_id", ""), ""),
            role=message["role"],
            snippet=_snippet(message.get("content", ""), query),
        )
        for message in messages
    ]
