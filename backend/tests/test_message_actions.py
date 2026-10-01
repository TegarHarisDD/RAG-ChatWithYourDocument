"""Message-level actions: paired delete and truncate-from."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .helpers import login


async def _session(client, title: str = "Topic") -> dict:
    return (await client.post("/api/sessions", json={"title": title})).json()


async def _chat(client, session_id: str) -> dict:
    return (await client.post(f"/api/sessions/{session_id}/chats", json={})).json()


async def _insert(database, chat_id: str, session_id: str, content: str, role: str, when):
    await database.db.messages.insert_one(
        {
            "chat_id": chat_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "citations": [],
            "created_at": when,
        }
    )


async def _thread(database, chat_id: str, session_id: str) -> None:
    base = datetime.now(timezone.utc)
    await _insert(database, chat_id, session_id, "Q1", "user", base)
    await _insert(database, chat_id, session_id, "A1", "assistant", base + timedelta(seconds=1))
    await _insert(database, chat_id, session_id, "Q2", "user", base + timedelta(seconds=2))
    await _insert(database, chat_id, session_id, "A2", "assistant", base + timedelta(seconds=3))


async def _contents(client, chat_id: str) -> list[str]:
    messages = (await client.get(f"/api/chats/{chat_id}/messages")).json()
    return [message["content"] for message in messages]


async def _find(client, chat_id: str, content: str) -> dict:
    messages = (await client.get(f"/api/chats/{chat_id}/messages")).json()
    return next(message for message in messages if message["content"] == content)


async def test_deleting_a_question_removes_its_answer(client, database):
    await login(client)
    session = await _session(client)
    chat = await _chat(client, session["id"])
    await _thread(database, chat["id"], session["id"])

    question = await _find(client, chat["id"], "Q1")
    response = await client.delete(f"/api/chats/{chat['id']}/messages/{question['id']}")
    assert response.status_code == 204

    assert await _contents(client, chat["id"]) == ["Q2", "A2"]


async def test_deleting_an_answer_removes_its_question(client, database):
    await login(client)
    session = await _session(client)
    chat = await _chat(client, session["id"])
    await _thread(database, chat["id"], session["id"])

    answer = await _find(client, chat["id"], "A2")
    response = await client.delete(f"/api/chats/{chat['id']}/messages/{answer['id']}")
    assert response.status_code == 204

    assert await _contents(client, chat["id"]) == ["Q1", "A1"]


async def test_truncate_from_a_message_drops_it_and_everything_after(client, database):
    await login(client)
    session = await _session(client)
    chat = await _chat(client, session["id"])
    await _thread(database, chat["id"], session["id"])

    question = await _find(client, chat["id"], "Q2")
    response = await client.delete(
        f"/api/chats/{chat['id']}/messages?from_message_id={question['id']}"
    )
    assert response.status_code == 204

    assert await _contents(client, chat["id"]) == ["Q1", "A1"]


async def test_truncate_from_is_scoped_to_the_chat(client, database):
    await login(client)
    session = await _session(client)
    first = await _chat(client, session["id"])
    second = await _chat(client, session["id"])
    await _thread(database, first["id"], session["id"])
    await _thread(database, second["id"], session["id"])

    question = await _find(client, first["id"], "Q2")
    # A message id from another chat cannot be truncated via this chat.
    response = await client.delete(
        f"/api/chats/{second['id']}/messages?from_message_id={question['id']}"
    )
    assert response.status_code == 404


async def test_message_actions_require_authentication(client):
    response = await client.delete(
        "/api/chats/000000000000000000000000/messages/000000000000000000000000"
    )
    assert response.status_code == 401
