"""Owner account and session-secret storage.

There is exactly one owner. On a fresh deployment no account exists yet, so the
first visitor creates one through the setup flow; from then on that stored
account is the only way to sign in. Credentials live in MongoDB (never in
`.env`), and the password is only ever persisted as a bcrypt hash.

The cookie-signing secret is likewise persisted (unless the operator pins
`SECRET_KEY`), so sessions survive restarts without any manual setup step.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from ..db import Database
from ..security import hash_password, verify_credentials

OWNER_ID = "owner"
SECRET_ID = "session_secret"


class OwnerExists(Exception):
    """Raised when setup is attempted after an owner already exists."""


class Accounts:
    def __init__(self, db: Database) -> None:
        self._db = db
        self._secret: str | None = None

    async def get_owner(self) -> dict | None:
        return await self._db.db.users.find_one({"_id": OWNER_ID})

    async def exists(self) -> bool:
        return await self.get_owner() is not None

    async def create_owner(self, username: str, password: str) -> dict:
        """Create the single owner. The fixed `_id` makes this atomic: a second
        concurrent setup attempt hits a duplicate key instead of overwriting."""
        doc = {
            "_id": OWNER_ID,
            "username": username,
            "password_hash": hash_password(password),
            "created_at": datetime.now(timezone.utc),
        }
        try:
            await self._db.db.users.insert_one(doc)
        except DuplicateKeyError as exc:
            raise OwnerExists() from exc
        return doc

    async def verify(self, username: str, password: str) -> bool:
        owner = await self.get_owner()
        return verify_credentials(
            username,
            password,
            owner["username"] if owner else "",
            owner["password_hash"] if owner else "",
        )

    async def session_secret(self, configured: str) -> str:
        """Return the cookie-signing secret.

        A non-empty configured value wins. Otherwise a random secret is created
        once and stored, so tokens stay valid across restarts.
        """
        if configured:
            return configured
        if self._secret:
            return self._secret

        meta = self._db.db.meta
        doc = await meta.find_one({"_id": SECRET_ID})
        if doc and doc.get("value"):
            self._secret = doc["value"]
            return self._secret

        value = secrets.token_urlsafe(48)
        try:
            await meta.insert_one({"_id": SECRET_ID, "value": value})
            self._secret = value
        except DuplicateKeyError:
            doc = await meta.find_one({"_id": SECRET_ID})
            self._secret = doc["value"]
        return self._secret
