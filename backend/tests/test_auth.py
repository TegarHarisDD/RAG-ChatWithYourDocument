import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import create_app

from .helpers import TEST_PASSWORD, TEST_USERNAME, login

PROTECTED_ROUTES = [
    ("GET", "/api/auth/me"),
    ("POST", "/api/auth/logout"),
    ("GET", "/api/sessions"),
    ("POST", "/api/sessions"),
    ("POST", "/api/sessions/bulk-delete"),
    ("GET", "/api/sessions/000000000000000000000000"),
    ("PATCH", "/api/sessions/000000000000000000000000"),
    ("DELETE", "/api/sessions/000000000000000000000000"),
    ("GET", "/api/sessions/000000000000000000000000/chats"),
    ("POST", "/api/sessions/000000000000000000000000/chats"),
    ("GET", "/api/chats/000000000000000000000000"),
    ("PATCH", "/api/chats/000000000000000000000000"),
    ("DELETE", "/api/chats/000000000000000000000000"),
    ("GET", "/api/chats/000000000000000000000000/messages"),
    ("POST", "/api/chats/000000000000000000000000/messages"),
    ("DELETE", "/api/chats/000000000000000000000000/messages"),
    ("GET", "/api/chunks/000000000000000000000000"),
    ("GET", "/api/sessions/000000000000000000000000/documents"),
    ("POST", "/api/sessions/000000000000000000000000/documents"),
    ("POST", "/api/sessions/000000000000000000000000/search"),
    ("GET", "/api/documents/000000000000000000000000"),
    ("PATCH", "/api/documents/000000000000000000000000"),
    ("DELETE", "/api/documents/000000000000000000000000"),
    ("POST", "/api/documents/000000000000000000000000/reprocess"),
]


@pytest_asyncio.fixture
async def fresh_client(client, database):
    """A client whose database has no owner yet (setup not completed)."""
    await database.db.users.delete_many({})
    return client


async def test_status_requires_setup_on_a_fresh_install(fresh_client):
    response = await fresh_client.get("/api/auth/status")
    assert response.status_code == 200
    assert response.json() == {"setup_required": True}


async def test_status_reports_setup_complete_once_owner_exists(client):
    response = await client.get("/api/auth/status")
    assert response.status_code == 200
    assert response.json() == {"setup_required": False}


async def test_setup_creates_owner_signs_in_and_is_one_time(fresh_client, database):
    response = await fresh_client.post(
        "/api/auth/setup", json={"username": "reader", "password": "a-strong-one"}
    )
    assert response.status_code == 201
    assert response.json() == {"username": "reader"}

    set_cookie = response.headers["set-cookie"]
    assert "session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "samesite=lax" in set_cookie.lower()

    # The owner is now signed in...
    assert (await fresh_client.get("/api/auth/me")).json() == {"username": "reader"}
    # ...a password hash (not the plaintext) is stored...
    owner = await database.db.users.find_one({"_id": "owner"})
    assert owner["password_hash"] != "a-strong-one"
    assert owner["password_hash"].startswith("$2")
    # ...and setup cannot be run again.
    again = await fresh_client.post(
        "/api/auth/setup", json={"username": "someone", "password": "another-one"}
    )
    assert again.status_code == 409


async def test_setup_rejects_weak_or_missing_credentials(fresh_client):
    short_pass = await fresh_client.post(
        "/api/auth/setup", json={"username": "reader", "password": "short"}
    )
    short_user = await fresh_client.post(
        "/api/auth/setup", json={"username": "ab", "password": "a-strong-one"}
    )
    assert short_pass.status_code == 422
    assert short_user.status_code == 422


async def test_login_success_sets_hardened_cookie(client):
    response = await login(client)
    assert response.status_code == 200
    assert response.json() == {"username": TEST_USERNAME}
    assert TEST_PASSWORD not in response.text

    set_cookie = response.headers["set-cookie"]
    assert "session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "samesite=lax" in set_cookie.lower()


async def test_login_before_setup_is_rejected(fresh_client):
    response = await login(fresh_client)
    assert response.status_code == 401


async def test_wrong_username_and_password_are_indistinguishable(client):
    wrong_user = await login(client, username="not-the-owner", password=TEST_PASSWORD)
    wrong_pass = await login(client, username=TEST_USERNAME, password="wrong-password")
    assert wrong_user.status_code == 401
    assert wrong_pass.status_code == 401
    assert wrong_user.json() == wrong_pass.json()


@pytest.mark.parametrize("method,path", PROTECTED_ROUTES)
async def test_protected_routes_reject_unauthenticated(client, method, path):
    response = await client.request(method, path)
    assert response.status_code == 401


async def test_login_health_and_status_are_public(client):
    assert (await client.get("/api/health")).status_code == 200
    assert (await client.get("/api/auth/status")).status_code == 200
    assert (await login(client)).status_code == 200


async def test_tampered_cookie_is_rejected(client):
    client.cookies.set("session", "not-a-real-token")
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


async def test_logout_clears_cookie_and_end_session(client):
    await login(client)
    assert (await client.get("/api/auth/me")).status_code == 200

    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 204

    assert (await client.get("/api/auth/me")).status_code == 401


async def test_expired_token_is_rejected(settings, database):
    short_life = settings.model_copy(update={"session_max_age": 1})
    app = create_app(settings=short_life, db=database)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://testserver") as client:
        await login(client)
        assert (await client.get("/api/auth/me")).status_code == 200
        await asyncio.sleep(1.1)
        assert (await client.get("/api/auth/me")).status_code == 401


async def test_repeated_failures_are_rate_limited_then_clear(settings, database):
    limited = settings.model_copy(
        update={"login_rate_limit_attempts": 2, "login_rate_limit_window_seconds": 1}
    )
    app = create_app(settings=limited, db=database)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://testserver") as client:
        assert (await login(client, password="wrong")).status_code == 401
        assert (await login(client, password="wrong")).status_code == 401
        assert (await login(client, password="wrong")).status_code == 429

        await asyncio.sleep(1.1)
        # Window has passed; the limiter no longer blocks.
        assert (await login(client, password="wrong")).status_code == 401


async def test_password_is_never_stored_in_plaintext(database):
    owner = await database.db.users.find_one({"_id": "owner"})
    assert owner["password_hash"] != TEST_PASSWORD
    assert owner["password_hash"].startswith("$2")
