"""One continuous conversation per session (flow change).

Opening a session resolves its conversation automatically, so there is no
separate "create a chat" step.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from .helpers import login


async def _session(client, title: str = "Topic") -> dict:
    return (await client.post("/api/sessions", json={"title": title})).json()


async def test_opening_a_session_provides_a_conversation(client, database):
    await login(client)
    session = await _session(client)

    detail = (await client.get(f"/api/sessions/{session['id']}")).json()
    assert detail["chat_id"]

    assert (await client.get(f"/api/chats/{detail['chat_id']}")).status_code == 200
    assert await database.db.chats.count_documents({"session_id": session["id"]}) == 1


async def test_reopening_a_session_reuses_the_same_conversation(client, database):
    await login(client)
    session = await _session(client)

    first = (await client.get(f"/api/sessions/{session['id']}")).json()
    second = (await client.get(f"/api/sessions/{session['id']}")).json()
    assert first["chat_id"] == second["chat_id"]
    assert await database.db.chats.count_documents({"session_id": session["id"]}) == 1


async def test_conversation_is_the_most_recent_existing_chat(client, database):
    await login(client)
    session = await _session(client)
    first = (await client.post(f"/api/sessions/{session['id']}/chats", json={"title": "First"})).json()
    await client.post(f"/api/sessions/{session['id']}/chats", json={"title": "Second"})

    await database.db.chats.update_one(
        {"_id": ObjectId(first["id"])},
        {"$set": {"last_active_at": datetime.now(timezone.utc) + timedelta(hours=1)}},
    )

    detail = (await client.get(f"/api/sessions/{session['id']}")).json()
    assert detail["chat_id"] == first["id"]


async def test_can_chat_immediately_after_uploading_a_document(client, chat_model):
    await login(client)
    session = await _session(client)
    response = await client.post(
        f"/api/sessions/{session['id']}/documents",
        files=[("files", ("notes.txt", b"alpha content about cells", "text/plain"))],
    )
    document_id = response.json()[0]["id"]
    for _ in range(60):
        body = (await client.get(f"/api/documents/{document_id}")).json()
        if body["status"] == "ready":
            break
        await asyncio.sleep(0.05)

    chat_id = (await client.get(f"/api/sessions/{session['id']}")).json()["chat_id"]
    reply = await client.post(f"/api/chats/{chat_id}/messages", json={"content": "alpha"})
    assert reply.status_code == 200
    assert "text/event-stream" in reply.headers["content-type"]

    events = [
        line.split(":", 1)[1].strip()
        for block in reply.text.split("\n\n")
        for line in block.splitlines()
        if line.startswith("event:")
    ]
    assert "token" in events
    assert "done" in events

    messages = (await client.get(f"/api/chats/{chat_id}/messages")).json()
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert json.dumps(messages[-1]["citations"]) != "[]"
