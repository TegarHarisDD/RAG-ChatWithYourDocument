"""Ticket 08: manage documents (rename, delete, re-process)."""

from __future__ import annotations

import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import create_app

from .fakes import FakeEmbedder, FlakyEmbedder
from .helpers import login


def _upload(files):
    return [("files", (name, content, ctype)) for name, content, ctype in files]


async def _wait_for_status(client, document_id: str) -> dict:
    body = {}
    for _ in range(60):
        body = (await client.get(f"/api/documents/{document_id}")).json()
        if body["status"] in ("ready", "failed"):
            return body
        await asyncio.sleep(0.05)
    return body


async def _session(client, title: str = "Docs") -> dict:
    return (await client.post("/api/sessions", json={"title": title})).json()


async def _upload_one(client, session_id: str, name: str, text: bytes) -> dict:
    response = await client.post(
        f"/api/sessions/{session_id}/documents",
        files=_upload([(name, text, "text/plain")]),
    )
    assert response.status_code == 202
    return await _wait_for_status(client, response.json()[0]["id"])


async def test_rename_persists_and_updates_the_listing(client):
    await login(client)
    session = await _session(client)
    document = await _upload_one(client, session["id"], "cryptic.txt", b"some content here")

    response = await client.patch(
        f"/api/documents/{document['id']}", json={"filename": "Readable name.txt"}
    )
    assert response.status_code == 200
    assert response.json()["filename"] == "Readable name.txt"

    listed = (await client.get(f"/api/sessions/{session['id']}/documents")).json()
    assert listed[0]["filename"] == "Readable name.txt"


async def test_delete_removes_chunks_and_the_document(client, database):
    await login(client)
    session = await _session(client)
    document = await _upload_one(client, session["id"], "gone.txt", b"content to be removed")
    assert await database.db.chunks.count_documents({"document_id": document["id"]}) > 0

    response = await client.delete(f"/api/documents/{document['id']}")
    assert response.status_code == 204

    assert (await client.get(f"/api/documents/{document['id']}")).status_code == 404
    assert await database.db.chunks.count_documents({"document_id": document["id"]}) == 0


async def test_delete_one_document_leaves_the_others(client):
    await login(client)
    session = await _session(client)
    keep = await _upload_one(client, session["id"], "keep.txt", b"keep this content")
    drop = await _upload_one(client, session["id"], "drop.txt", b"drop this content")

    await client.delete(f"/api/documents/{drop['id']}")

    listed = (await client.get(f"/api/sessions/{session['id']}/documents")).json()
    assert [d["id"] for d in listed] == [keep["id"]]
    assert listed[0]["status"] == "ready"


async def test_reprocess_replaces_chunks_rather_than_duplicating(client, database):
    await login(client)
    session = await _session(client)
    document = await _upload_one(client, session["id"], "notes.txt", b"a short piece of text")

    before = await database.db.chunks.count_documents({"document_id": document["id"]})
    response = await client.post(f"/api/documents/{document['id']}/reprocess")
    assert response.status_code == 202
    await _wait_for_status(client, document["id"])

    after = await database.db.chunks.count_documents({"document_id": document["id"]})
    assert after == before


async def test_reprocess_recovers_a_failed_document(settings, database):
    embedder = FlakyEmbedder(failures=1)
    app = create_app(settings=settings, db=database, embedder=embedder)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://testserver") as local:
        await login(local)
        session = await _session(local, "Flaky")
        document = await _upload_one(local, session["id"], "notes.txt", b"recoverable content")
        assert document["status"] == "failed"
        assert document["error"]

        response = await local.post(f"/api/documents/{document['id']}/reprocess")
        assert response.status_code == 202
        recovered = await _wait_for_status(local, document["id"])
        assert recovered["status"] == "ready"
        assert recovered["chunk_count"] > 0


async def test_document_list_shows_status_chunk_count_and_reason(client):
    await login(client)
    session = await _session(client)
    ok = await _upload_one(client, session["id"], "ok.txt", b"healthy content")
    bad = await client.post(
        f"/api/sessions/{session['id']}/documents",
        files=_upload([("bad.pdf", b"%PDF-1.4 not a pdf", "application/pdf")]),
    )
    failed = await _wait_for_status(client, bad.json()[0]["id"])

    listed = {d["id"]: d for d in (await client.get(f"/api/sessions/{session['id']}/documents")).json()}
    assert listed[ok["id"]]["status"] == "ready"
    assert listed[ok["id"]]["chunk_count"] > 0
    assert listed[failed["id"]]["status"] == "failed"
    assert listed[failed["id"]]["error"]


async def test_reprocess_missing_document_is_not_found(client):
    await login(client)
    response = await client.post("/api/documents/000000000000000000000000/reprocess")
    assert response.status_code == 404


async def test_default_app_is_hermetic():
    # Guard: the exported fakes stay deterministic, so retrieval tests can rely
    # on stable similarity ordering.
    embedder = FakeEmbedder()
    vectors = await embedder.embed(["alpha beta", "alpha beta"])
    assert vectors[0] == vectors[1]
