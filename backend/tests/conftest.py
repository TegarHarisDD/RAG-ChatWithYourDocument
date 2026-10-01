"""Shared test fixtures.

Tests drive the real ASGI app over HTTP and run against a dedicated
``<MONGODB_DB>_test`` database on the configured cluster, dropped around each
test. No test imports an internal function or inspects raw Mongo documents for
its assertions.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.db import Database
from app.main import create_app
from app.security import hash_password
from app.services.accounts import OWNER_ID, Accounts

from .fakes import FakeEmbedder, ScriptedChatModel
from .helpers import TEST_PASSWORD, TEST_USERNAME

# Hashing is deliberately slow; do it once for the whole session and insert the
# resulting document directly, so seeding an owner per test stays cheap.
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


@pytest.fixture(scope="session")
def base_settings() -> Settings:
    return Settings()


@pytest.fixture
def test_db_name(base_settings: Settings) -> str:
    return f"{base_settings.mongodb_db}_test"


@pytest_asyncio.fixture
async def database(base_settings: Settings, test_db_name: str):
    db = Database(base_settings.mongodb_uri, test_db_name)
    await db.client.drop_database(test_db_name)
    # Most tests assume an owner already exists; the setup tests delete this.
    await db.db.users.insert_one(
        {
            "_id": OWNER_ID,
            "username": TEST_USERNAME,
            "password_hash": TEST_PASSWORD_HASH,
        }
    )
    yield db
    await db.client.drop_database(test_db_name)
    db.close()


@pytest.fixture
def settings(base_settings: Settings) -> Settings:
    return base_settings.model_copy(
        update={
            "secret_key": "test-secret-key",
            "session_max_age": 3600,
            "cookie_secure": True,
            "frontend_dist": None,
        }
    )


@pytest_asyncio.fixture
def chat_model() -> ScriptedChatModel:
    return ScriptedChatModel()


@pytest_asyncio.fixture
async def app(settings: Settings, database: Database, chat_model: ScriptedChatModel):
    # Hermetic by default: ingestion uses a deterministic embedder and chat uses
    # a scripted model, so tests never call a real provider.
    return create_app(
        settings=settings, db=database, embedder=FakeEmbedder(), chat_model=chat_model
    )


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://testserver") as c:
        yield c
