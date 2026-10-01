"""Explicit, ordered cascade deletes.

MongoDB has no cascading foreign keys; deleting a parent is the application's
responsibility. These functions are the single place that responsibility lives,
so later entities plug into them instead of inventing their own ordering.
"""

from __future__ import annotations

from ..db import Database
from .ports import VectorStore


async def delete_chat(db: Database, chat_id: str, session_id: str) -> None:
    """Remove a chat and its messages; leave the session's documents alone."""
    await db.db.messages.delete_many({"chat_id": chat_id})
    await db.db.chats.delete_one({"_id": _oid(chat_id), "session_id": session_id})


async def clear_chat_messages(db: Database, chat_id: str) -> None:
    await db.db.messages.delete_many({"chat_id": chat_id})


async def delete_document(db: Database, vector_store: VectorStore, document_id: str) -> None:
    await vector_store.delete_document(document_id)
    await db.db.documents.delete_one({"_id": _oid(document_id)})


async def delete_session(db: Database, vector_store: VectorStore, session_id: str) -> None:
    """Delete a session and everything it owns.

    Order: messages, chats, documents, chunks, then the session itself.
    """
    await db.db.messages.delete_many({"session_id": session_id})
    await db.db.chats.delete_many({"session_id": session_id})
    await db.db.documents.delete_many({"session_id": session_id})
    await vector_store.delete_session(session_id)
    await db.db.sessions.delete_one({"_id": _oid(session_id)})


def _oid(value: str):
    from bson import ObjectId

    return ObjectId(value)
