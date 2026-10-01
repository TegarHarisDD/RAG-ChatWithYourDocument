"""MongoDB connection and index management."""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


class Database:
    """Thin wrapper around a Motor database handle."""

    def __init__(self, uri: str, name: str) -> None:
        self.client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000, tz_aware=True)
        self.db: AsyncIOMotorDatabase = self.client[name]

    async def ping(self) -> None:
        await self.client.admin.command("ping")

    async def ensure_indexes(self) -> None:
        # Sessions are listed ordered by most-recently-active.
        await self.db.sessions.create_index([("last_active_at", -1)])
        # Foreign-key reads for later tickets; harmless to create now.
        await self.db.chats.create_index([("session_id", 1), ("last_active_at", -1)])
        await self.db.messages.create_index([("chat_id", 1), ("created_at", 1)])
        await self.db.messages.create_index([("session_id", 1)])
        await self.db.documents.create_index([("session_id", 1)])
        await self.db.chunks.create_index([("session_id", 1), ("document_id", 1)])
        await self.db.chunks.create_index([("document_id", 1)])

    def close(self) -> None:
        self.client.close()
