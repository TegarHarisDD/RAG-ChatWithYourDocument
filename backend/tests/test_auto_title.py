"""Session auto-titling from the first question."""

from __future__ import annotations

from .helpers import login


async def _session(client, title: str | None = None) -> dict:
    payload = {} if title is None else {"title": title}
    return (await client.post("/api/sessions", json=payload)).json()


async def _chat(client, session_id: str) -> dict:
    return (await client.post(f"/api/sessions/{session_id}/chats", json={})).json()


async def _ask(client, chat_id: str, content: str):
    return await client.post(f"/api/chats/{chat_id}/messages", json={"content": content})


async def test_first_question_names_an_untitled_session(client):
    await login(client)
    session = await _session(client)
    assert session["title"] == "Untitled session"

    chat = await _chat(client, session["id"])
    response = await _ask(client, chat["id"], "How do mitochondria work?")
    assert response.status_code == 200

    refreshed = (await client.get(f"/api/sessions/{session['id']}")).json()
    assert refreshed["title"] == "How do mitochondria work?"


async def test_named_session_is_never_overwritten(client):
    await login(client)
    session = await _session(client, "Cell biology")
    chat = await _chat(client, session["id"])

    await _ask(client, chat["id"], "unrelated question")

    refreshed = (await client.get(f"/api/sessions/{session['id']}")).json()
    assert refreshed["title"] == "Cell biology"


async def test_long_question_is_truncated_to_a_label(client):
    await login(client)
    session = await _session(client)
    chat = await _chat(client, session["id"])

    await _ask(client, chat["id"], "alpha " * 40)

    refreshed = (await client.get(f"/api/sessions/{session['id']}")).json()
    assert refreshed["title"].endswith("…")
    assert len(refreshed["title"]) <= 61
