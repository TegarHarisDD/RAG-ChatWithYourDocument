"""Cross-session message search."""

from __future__ import annotations

from datetime import datetime, timezone

from .helpers import login


async def _session(client, title: str) -> dict:
    return (await client.post("/api/sessions", json={"title": title})).json()


async def _chat(client, session_id: str) -> dict:
    return (await client.post(f"/api/sessions/{session_id}/chats", json={})).json()


async def _insert(database, chat_id: str, session_id: str, content: str, role: str = "user"):
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


async def test_search_returns_hits_with_the_session_title(client, database):
    await login(client)
    session = await _session(client, "Cell biology")
    chat = await _chat(client, session["id"])
    await _insert(database, chat["id"], session["id"], "Mitochondria are the powerhouse", "user")

    results = (await client.get("/api/search/messages?q=mitochondria")).json()
    assert len(results) == 1
    hit = results[0]
    assert hit["session_title"] == "Cell biology"
    assert hit["role"] == "user"
    assert hit["message_id"]
    assert "Mitochondria" in hit["snippet"]


async def test_search_is_case_insensitive(client, database):
    await login(client)
    session = await _session(client, "Alpha")
    chat = await _chat(client, session["id"])
    await _insert(database, chat["id"], session["id"], "The ZEBRA runs fast")

    results = (await client.get("/api/search/messages?q=zebra")).json()
    assert len(results) == 1
    assert "ZEBRA" in results[0]["snippet"]


async def test_empty_query_returns_nothing(client):
    await login(client)
    assert (await client.get("/api/search/messages?q=")).json() == []
    assert (await client.get("/api/search/messages?q=%20%20")).json() == []


async def test_snippet_is_windowed_around_the_match(client, database):
    await login(client)
    session = await _session(client, "Alpha")
    chat = await _chat(client, session["id"])
    content = ("filler " * 40) + "needle" + (" trailer" * 40)
    await _insert(database, chat["id"], session["id"], content)

    results = (await client.get("/api/search/messages?q=needle")).json()
    assert len(results) == 1
    snippet = results[0]["snippet"]
    assert "needle" in snippet
    assert len(snippet) < len(content)


async def test_search_requires_authentication(client):
    response = await client.get("/api/search/messages?q=anything")
    assert response.status_code == 401
