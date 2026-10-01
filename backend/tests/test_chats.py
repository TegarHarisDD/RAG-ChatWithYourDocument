"""Ticket 05: chats inside a session."""

from __future__ import annotations

from datetime import datetime, timezone

from .helpers import login


async def _session(client, title: str = "Topic") -> dict:
    return (await client.post("/api/sessions", json={"title": title})).json()


async def _chat(client, session_id: str, title: str | None = None) -> dict:
    payload = {} if title is None else {"title": title}
    return (await client.post(f"/api/sessions/{session_id}/chats", json=payload)).json()


async def _message(database, chat_id: str, session_id: str, content: str, role: str = "user"):
    await database.db.messages.insert_one(
        {
            "chat_id": chat_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "citations": [],
            "created_at": datetime.now(timezone.utc),
        }
    )


async def test_opening_a_session_lists_its_chats(client):
    await login(client)
    session = await _session(client)
    await _chat(client, session["id"], "First")
    await _chat(client, session["id"], "Second")

    listed = (await client.get(f"/api/sessions/{session['id']}/chats")).json()
    assert {c["title"] for c in listed} == {"First", "Second"}


async def test_create_chat_adds_it_and_returns_it(client):
    await login(client)
    session = await _session(client)
    response = await client.post(f"/api/sessions/{session['id']}/chats", json={"title": "Angles"})
    assert response.status_code == 201
    assert response.json()["session_id"] == session["id"]


async def test_chat_without_title_gets_a_default(client):
    await login(client)
    session = await _session(client)
    chat = await _chat(client, session["id"])
    assert chat["title"]
    assert chat["title"] == "New chat"


async def test_rename_chat_persists_in_listing(client):
    await login(client)
    session = await _session(client)
    chat = await _chat(client, session["id"], "Vague")

    response = await client.patch(f"/api/chats/{chat['id']}", json={"title": "Clearer"})
    assert response.status_code == 200
    assert response.json()["title"] == "Clearer"

    listed = (await client.get(f"/api/sessions/{session['id']}/chats")).json()
    assert listed[0]["title"] == "Clearer"


async def test_delete_chat_removes_messages_but_keeps_documents(client, database):
    await login(client)
    session = await _session(client)
    await client.post(
        f"/api/sessions/{session['id']}/documents",
        files=[("files", ("notes.txt", b"Biology notes about cells.", "text/plain"))],
    )
    chat = await _chat(client, session["id"], "Doomed")
    await _message(database, chat["id"], session["id"], "keep me not")

    response = await client.delete(f"/api/chats/{chat['id']}")
    assert response.status_code == 204

    assert (await client.get(f"/api/chats/{chat['id']}")).status_code == 404
    assert (await client.get(f"/api/chats/{chat['id']}/messages")).status_code == 404
    assert await database.db.messages.count_documents({"chat_id": chat["id"]}) == 0

    documents = (await client.get(f"/api/sessions/{session['id']}/documents")).json()
    assert len(documents) == 1
    assert documents[0]["status"] == "ready"


async def test_clear_messages_empties_thread_but_keeps_chat(client, database):
    await login(client)
    session = await _session(client)
    chat = await _chat(client, session["id"])
    await _message(database, chat["id"], session["id"], "one")
    await _message(database, chat["id"], session["id"], "two")

    assert len((await client.get(f"/api/chats/{chat['id']}/messages")).json()) == 2

    response = await client.delete(f"/api/chats/{chat['id']}/messages")
    assert response.status_code == 204

    assert (await client.get(f"/api/chats/{chat['id']}/messages")).json() == []
    assert (await client.get(f"/api/chats/{chat['id']}")).status_code == 200


async def test_several_chats_keep_independent_history(client, database):
    await login(client)
    session = await _session(client)
    first = await _chat(client, session["id"], "First")
    second = await _chat(client, session["id"], "Second")
    await _message(database, first["id"], session["id"], "first-only")
    await _message(database, second["id"], session["id"], "second-only")

    first_messages = (await client.get(f"/api/chats/{first['id']}/messages")).json()
    second_messages = (await client.get(f"/api/chats/{second['id']}/messages")).json()
    assert [m["content"] for m in first_messages] == ["first-only"]
    assert [m["content"] for m in second_messages] == ["second-only"]


async def test_chats_belonging_to_one_session_are_not_listed_in_another(client):
    await login(client)
    alpha = await _session(client, "Alpha")
    beta = await _session(client, "Beta")
    await _chat(client, alpha["id"], "Alpha chat")

    listed = (await client.get(f"/api/sessions/{beta['id']}/chats")).json()
    assert listed == []


async def test_create_chat_under_missing_session_is_not_found(client):
    await login(client)
    response = await client.post(
        "/api/sessions/000000000000000000000000/chats", json={"title": "Nope"}
    )
    assert response.status_code == 404
