"""Ticket 14: citation click-through resolves to the exact source chunk."""

from __future__ import annotations

import asyncio
import json

from bson import ObjectId

from .helpers import login


async def _session(client, title: str = "Topic") -> dict:
    return (await client.post("/api/sessions", json={"title": title})).json()


async def _chat(client, session_id: str) -> dict:
    return (await client.post(f"/api/sessions/{session_id}/chats", json={"title": "C"})).json()


async def _upload_ready(client, session_id: str, name: str, text: bytes) -> dict:
    response = await client.post(
        f"/api/sessions/{session_id}/documents",
        files=[("files", (name, text, "text/plain"))],
    )
    document_id = response.json()[0]["id"]
    for _ in range(60):
        body = (await client.get(f"/api/documents/{document_id}")).json()
        if body["status"] in ("ready", "failed"):
            return body
        await asyncio.sleep(0.05)
    return body


async def _send(client, chat_id: str, content: str) -> str:
    response = await client.post(f"/api/chats/{chat_id}/messages", json={"content": content})
    assert response.status_code == 200
    return response.text


def _first_citation(sse_text: str) -> dict:
    for block in sse_text.split("\n\n"):
        if "event: citations" in block:
            for line in block.splitlines():
                if line.startswith("data:"):
                    return json.loads(line[5:].strip())["citations"][0]
    raise AssertionError("no citations event")


async def test_citation_points_at_the_exact_stored_chunk(client, chat_model, database):
    await login(client)
    session = await _session(client)
    document = await _upload_ready(
        client, session["id"], "cells.txt", b"Mitochondria are the powerhouse of the cell."
    )
    chat = await _chat(client, session["id"])

    citation = _first_citation(await _send(client, chat["id"], "mitochondria"))

    response = await client.get(f"/api/chunks/{citation['chunk_id']}")
    assert response.status_code == 200
    chunk = response.json()
    assert chunk["document_id"] == document["id"]
    assert chunk["filename"] == "cells.txt"
    assert chunk["locator"] == citation["locator"]
    assert "Mitochondria are the powerhouse" in chunk["text"]

    # Same text that was supplied to the model, not a re-extraction.
    supplied = chat_model.prompts[-1][-1]["content"]
    assert chunk["text"] in supplied

    stored = await database.db.chunks.find_one({"_id": ObjectId(citation["chunk_id"])})
    assert stored["text"] == chunk["text"]


async def test_deleted_source_chunk_returns_not_found(client):
    await login(client)
    session = await _session(client)
    document = await _upload_ready(client, session["id"], "gone.txt", b"ephemeral content here")
    chat = await _chat(client, session["id"])
    citation = _first_citation(await _send(client, chat["id"], "ephemeral"))

    assert (await client.get(f"/api/chunks/{citation['chunk_id']}")).status_code == 200
    await client.delete(f"/api/documents/{document['id']}")
    assert (await client.get(f"/api/chunks/{citation['chunk_id']}")).status_code == 404


async def test_missing_chunk_id_returns_not_found(client):
    await login(client)
    assert (await client.get("/api/chunks/000000000000000000000000")).status_code == 404
    assert (await client.get("/api/chunks/not-an-id")).status_code == 404
