"""Ticket 04: rename and delete sessions, with the shared cascade."""

from __future__ import annotations

from datetime import datetime, timezone

from .helpers import login


async def _create(client, title: str = "Topic") -> dict:
    return (await client.post("/api/sessions", json={"title": title})).json()


async def test_rename_persists_and_shows_in_list(client):
    await login(client)
    session = await _create(client, "Old name")

    response = await client.patch(f"/api/sessions/{session['id']}", json={"title": "New name"})
    assert response.status_code == 200
    assert response.json()["title"] == "New name"

    listed = (await client.get("/api/sessions")).json()
    assert listed[0]["title"] == "New name"


async def test_rename_rejects_blank_title(client):
    await login(client)
    session = await _create(client)
    response = await client.patch(f"/api/sessions/{session['id']}", json={"title": "   "})
    assert response.status_code == 422


async def test_rename_missing_session_is_not_found(client):
    await login(client)
    response = await client.patch(
        "/api/sessions/000000000000000000000000", json={"title": "Nope"}
    )
    assert response.status_code == 404


async def test_delete_empty_session_succeeds(client):
    await login(client)
    session = await _create(client)

    response = await client.delete(f"/api/sessions/{session['id']}")
    assert response.status_code == 204

    assert (await client.get("/api/sessions")).json() == []
    assert (await client.get(f"/api/sessions/{session['id']}")).status_code == 404


async def test_delete_cascades_to_chats_messages_documents_and_chunks(client, database):
    await login(client)
    session = await _create(client, "Doomed")

    chat = (
        await client.post(f"/api/sessions/{session['id']}/chats", json={"title": "Thread"})
    ).json()
    await database.db.messages.insert_one(
        {
            "chat_id": chat["id"],
            "session_id": session["id"],
            "role": "user",
            "content": "hello",
            "citations": [],
            "created_at": datetime.now(timezone.utc),
        }
    )
    await client.post(
        f"/api/sessions/{session['id']}/documents",
        files=[("files", ("notes.txt", b"Some text about biology.", "text/plain"))],
    )
    assert await database.db.chunks.count_documents({"session_id": session["id"]}) > 0

    response = await client.delete(f"/api/sessions/{session['id']}")
    assert response.status_code == 204

    assert (await client.get(f"/api/sessions/{session['id']}")).status_code == 404
    assert (await client.get(f"/api/chats/{chat['id']}")).status_code == 404
    assert (await client.get(f"/api/sessions/{session['id']}/documents")).status_code == 404

    assert await database.db.chats.count_documents({"session_id": session["id"]}) == 0
    assert await database.db.messages.count_documents({"session_id": session["id"]}) == 0
    assert await database.db.documents.count_documents({"session_id": session["id"]}) == 0
    assert await database.db.chunks.count_documents({"session_id": session["id"]}) == 0


async def test_delete_missing_session_is_not_found(client):
    await login(client)
    response = await client.delete("/api/sessions/000000000000000000000000")
    assert response.status_code == 404
