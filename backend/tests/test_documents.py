"""Ticket 06: upload and ingest text-format documents."""

from __future__ import annotations

import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import create_app

from .fakes import FakeEmbedder
from .helpers import login


class _FailingEmbedder:
    model = "fake-embedding"
    dimensions = 8

    async def embed(self, texts):
        raise RuntimeError("embedding provider exploded")


async def _session(client, title: str = "Docs") -> dict:
    return (await client.post("/api/sessions", json={"title": title})).json()


def _upload(files):
    return [("files", (name, content, ctype)) for name, content, ctype in files]


async def _wait_for_status(client, document_id: str, expected: str | None = None) -> dict:
    body = (await client.get(f"/api/documents/{document_id}")).json()
    for _ in range(50):
        body = (await client.get(f"/api/documents/{document_id}")).json()
        if expected is None and body["status"] in ("ready", "failed"):
            return body
        if expected is not None and body["status"] == expected:
            return body
        await asyncio.sleep(0.05)
    return body


async def test_txt_upload_reaches_ready_with_chunks(client):
    await login(client)
    session = await _session(client)
    response = await client.post(
        f"/api/sessions/{session['id']}/documents",
        files=_upload([("notes.txt", b"Biology notes. " * 50, "text/plain")]),
    )
    assert response.status_code == 202
    document_id = response.json()[0]["id"]

    body = await _wait_for_status(client, document_id)
    assert body["status"] == "ready"
    assert body["chunk_count"] > 0
    assert body["error"] is None


async def test_markdown_and_json_upload_together(client):
    await login(client)
    session = await _session(client)
    response = await client.post(
        f"/api/sessions/{session['id']}/documents",
        files=_upload(
            [
                ("guide.md", b"# Heading\n\nSome prose.", "text/markdown"),
                ("data.json", b'{"a": 1, "b": 2}', "application/json"),
            ]
        ),
    )
    assert response.status_code == 202
    assert len(response.json()) == 2
    for document in response.json():
        body = await _wait_for_status(client, document["id"])
        assert body["status"] == "ready"
        assert body["chunk_count"] > 0


async def test_markdown_chunks_carry_section_locator(client, database):
    await login(client)
    session = await _session(client)
    response = await client.post(
        f"/api/sessions/{session['id']}/documents",
        files=_upload([("guide.md", b"# Introduction\n\nHello world.", "text/markdown")]),
    )
    document_id = response.json()[0]["id"]
    await _wait_for_status(client, document_id)

    chunks = await database.db.chunks.find({"document_id": document_id}).to_list(length=None)
    assert chunks
    assert any(chunk["locator"].get("section") == "Introduction" for chunk in chunks)


async def test_json_is_flattened_to_key_path_lines(client, database):
    await login(client)
    session = await _session(client)
    nested = b'{"user": {"name": "Ada", "roles": ["admin", "author"]}}'
    response = await client.post(
        f"/api/sessions/{session['id']}/documents",
        files=_upload([("data.json", nested, "application/json")]),
    )
    document_id = response.json()[0]["id"]
    await _wait_for_status(client, document_id)

    chunks = await database.db.chunks.find({"document_id": document_id}).to_list(length=None)
    texts = "\n".join(chunk["text"] for chunk in chunks)
    assert "user.name: Ada" in texts
    assert "user.roles[0]: admin" in texts
    paths = {chunk["locator"].get("path") for chunk in chunks}
    assert "user.name" in paths


async def test_every_chunk_records_embedding_model(client, database):
    await login(client)
    session = await _session(client)
    response = await client.post(
        f"/api/sessions/{session['id']}/documents",
        files=_upload([("notes.txt", b"Some words to embed.", "text/plain")]),
    )
    document_id = response.json()[0]["id"]
    await _wait_for_status(client, document_id)

    chunks = await database.db.chunks.find({"document_id": document_id}).to_list(length=None)
    assert chunks
    assert {chunk["embedding_model"] for chunk in chunks} == {"fake-embedding"}
    assert all(chunk["chunk_index"] >= 0 for chunk in chunks)


async def test_same_file_uploaded_twice_is_two_documents(client):
    await login(client)
    session = await _session(client)
    payload = _upload([("notes.txt", b"duplicate content", "text/plain")])

    first = await client.post(f"/api/sessions/{session['id']}/documents", files=payload)
    second = await client.post(f"/api/sessions/{session['id']}/documents", files=payload)
    assert first.json()[0]["id"] != second.json()[0]["id"]

    documents = (await client.get(f"/api/sessions/{session['id']}/documents")).json()
    assert len(documents) == 2


async def test_empty_file_is_rejected(client):
    await login(client)
    session = await _session(client)
    response = await client.post(
        f"/api/sessions/{session['id']}/documents",
        files=_upload([("empty.txt", b"", "text/plain")]),
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


async def test_binary_file_is_rejected(client):
    await login(client)
    session = await _session(client)
    response = await client.post(
        f"/api/sessions/{session['id']}/documents",
        files=_upload([("blob.txt", b"\x00\x01\x02\xff\xfe", "text/plain")]),
    )
    assert response.status_code == 400
    assert "blob.txt" in response.json()["detail"]


async def test_type_is_sniffed_from_content_not_extension(client):
    await login(client)
    session = await _session(client)

    # A .txt file whose bytes are a PDF is stored as a PDF, not as text.
    disguised = await client.post(
        f"/api/sessions/{session['id']}/documents",
        files=_upload([("fake.txt", b"%PDF-1.4 not really a pdf", "text/plain")]),
    )
    assert disguised.status_code == 202
    assert disguised.json()[0]["content_type"] == "application/pdf"

    # A .pdf file whose bytes are plain text is stored as text.
    mislabelled = await client.post(
        f"/api/sessions/{session['id']}/documents",
        files=_upload([("notes.pdf", b"just plain text content", "application/pdf")]),
    )
    assert mislabelled.status_code == 202
    body = await _wait_for_status(client, mislabelled.json()[0]["id"])
    assert body["status"] == "ready"


async def test_text_content_with_unknown_extension_is_accepted(client):
    await login(client)
    session = await _session(client)
    response = await client.post(
        f"/api/sessions/{session['id']}/documents",
        files=_upload([("notes.bin", b"plain text content", "application/octet-stream")]),
    )
    assert response.status_code == 202
    body = await _wait_for_status(client, response.json()[0]["id"])
    assert body["status"] == "ready"


async def test_oversized_file_is_rejected(client, settings, database):
    small = settings.model_copy(update={"max_upload_bytes": 8})
    app = create_app(settings=small, db=database, embedder=FakeEmbedder())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://testserver") as local:
        await login(local)
        session = (await local.post("/api/sessions", json={"title": "Tiny"})).json()
        response = await local.post(
            f"/api/sessions/{session['id']}/documents",
            files=_upload([("big.txt", b"way too many bytes", "text/plain")]),
        )
        assert response.status_code == 400
        assert "size cap" in response.json()["detail"]


async def test_failed_ingestion_records_a_visible_reason(settings, database):
    app = create_app(settings=settings, db=database, embedder=_FailingEmbedder())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://testserver") as local:
        await login(local)
        session = (await local.post("/api/sessions", json={"title": "Doomed"})).json()
        response = await local.post(
            f"/api/sessions/{session['id']}/documents",
            files=_upload([("notes.txt", b"content that will fail", "text/plain")]),
        )
        document_id = response.json()[0]["id"]
        body = await _wait_for_status(local, document_id)
        assert body["status"] == "failed"
        assert body["error"]

        listed = (await local.get(f"/api/sessions/{session['id']}/documents")).json()
        assert listed[0]["status"] == "failed"
        assert listed[0]["error"]


async def test_reading_missing_document_is_not_found(client):
    await login(client)
    response = await client.get("/api/documents/000000000000000000000000")
    assert response.status_code == 404
