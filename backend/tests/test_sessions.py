from datetime import datetime, timedelta, timezone

from httpx import ASGITransport, AsyncClient

from app.main import create_app

from .helpers import login


def _titles(sessions: list[dict]) -> list[str]:
    return [s["title"] for s in sessions]


async def test_list_is_empty_initially(client):
    await login(client)
    response = await client.get("/api/sessions")
    assert response.status_code == 200
    assert response.json() == []


async def test_create_without_title_gets_a_default(client):
    await login(client)
    response = await client.post("/api/sessions", json={})
    assert response.status_code == 201
    body = response.json()
    assert body["title"]
    assert body["document_count"] == 0
    assert body["id"]


async def test_create_with_title_uses_it(client):
    await login(client)
    response = await client.post("/api/sessions", json={"title": "Biology papers"})
    assert response.status_code == 201
    assert response.json()["title"] == "Biology papers"


async def test_created_session_appears_at_top_without_refresh(client):
    await login(client)
    first = (await client.post("/api/sessions", json={"title": "First"})).json()
    second = (await client.post("/api/sessions", json={"title": "Second"})).json()

    listed = (await client.get("/api/sessions")).json()
    assert _titles(listed)[:2] == ["Second", "First"]
    assert {s["id"] for s in listed} == {first["id"], second["id"]}


async def test_activity_moves_a_session_to_the_top(client, database):
    await login(client)
    first = (await client.post("/api/sessions", json={"title": "First"})).json()
    await client.post("/api/sessions", json={"title": "Second"})

    future = datetime.now(timezone.utc) + timedelta(hours=1)
    from bson import ObjectId

    await database.db.sessions.update_one(
        {"_id": ObjectId(first["id"])}, {"$set": {"last_active_at": future}}
    )

    listed = (await client.get("/api/sessions")).json()
    assert listed[0]["title"] == "First"


async def test_session_shows_document_count(client, database):
    await login(client)
    session = (await client.post("/api/sessions", json={"title": "With docs"})).json()

    await database.db.documents.insert_many(
        [
            {"session_id": session["id"], "filename": "a.txt"},
            {"session_id": session["id"], "filename": "b.txt"},
            {"session_id": "some-other-session", "filename": "c.txt"},
        ]
    )

    listed = (await client.get("/api/sessions")).json()
    assert listed[0]["document_count"] == 2


async def test_read_session_by_id(client):
    await login(client)
    created = (await client.post("/api/sessions", json={"title": "Readable"})).json()

    response = await client.get(f"/api/sessions/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["title"] == "Readable"


async def test_read_missing_session_is_not_found(client):
    await login(client)
    response = await client.get("/api/sessions/000000000000000000000000")
    assert response.status_code == 404


async def test_read_malformed_session_id_is_not_found(client):
    await login(client)
    response = await client.get("/api/sessions/not-an-id")
    assert response.status_code == 404


async def test_sessions_survive_a_backend_restart(client, database, settings):
    await login(client)
    created = (await client.post("/api/sessions", json={"title": "Persistent"})).json()

    restarted_app = create_app(settings=settings, db=database)
    transport = ASGITransport(app=restarted_app)
    async with AsyncClient(transport=transport, base_url="https://testserver") as fresh:
        await login(fresh)
        listed = (await fresh.get("/api/sessions")).json()
        assert _titles(listed) == ["Persistent"]
        assert listed[0]["id"] == created["id"]
