"""Ticket 09: vector retrieval scoped to a session."""

from __future__ import annotations

import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import create_app, _build_vector_store
from app.services.atlas_store import AtlasVectorStore
from app.services.vector_store import LocalVectorStore

from .fakes import FakeEmbedder
from .helpers import login


def _multipart(files):
    return [("files", (name, content, ctype)) for name, content, ctype in files]


async def _wait_for_status(client, document_id: str) -> dict:
    body = {}
    for _ in range(60):
        body = (await client.get(f"/api/documents/{document_id}")).json()
        if body["status"] in ("ready", "failed"):
            return body
        await asyncio.sleep(0.05)
    return body


async def _session(client, title: str) -> dict:
    return (await client.post("/api/sessions", json={"title": title})).json()


async def _upload(client, session_id: str, name: str, text: bytes) -> dict:
    response = await client.post(
        f"/api/sessions/{session_id}/documents",
        files=_multipart([(name, text, "text/plain")]),
    )
    assert response.status_code == 202
    document = await _wait_for_status(client, response.json()[0]["id"])
    assert document["status"] == "ready"
    return document


async def _search(client, session_id: str, query: str, k: int | None = None) -> list[dict]:
    payload = {"query": query} if k is None else {"query": query, "k": k}
    response = await client.post(f"/api/sessions/{session_id}/search", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


async def test_query_returns_the_matching_document(client):
    await login(client)
    session = await _session(client, "Bio")
    document = await _upload(client, session["id"], "cells.txt", b"Mitochondria are organelles.")

    results = await _search(client, session["id"], "mitochondria")
    assert results
    assert results[0]["document_id"] == document["id"]
    assert results[0]["filename"] == "cells.txt"
    assert results[0]["chunk_index"] == 0
    assert results[0]["score"] > 0


async def test_query_never_crosses_session_boundaries(client):
    await login(client)
    alpha = await _session(client, "Alpha")
    beta = await _session(client, "Beta")
    await _upload(client, alpha["id"], "alpha.txt", b"only about beta matters")
    beta_document = await _upload(client, beta["id"], "beta.txt", b"unique alpha fact")

    scoped_to_alpha = await _search(client, alpha["id"], "alpha")
    assert all(row["document_id"] != beta_document["id"] for row in scoped_to_alpha)

    # Nothing in session Alpha is relevant, so the query comes back empty.
    assert scoped_to_alpha == []

    scoped_to_beta = await _search(client, beta["id"], "alpha")
    assert scoped_to_beta
    assert scoped_to_beta[0]["document_id"] == beta_document["id"]


async def test_results_are_ordered_by_relevance(client):
    await login(client)
    session = await _session(client, "Ranking")
    strong = await _upload(client, session["id"], "strong.txt", b"alpha alpha alpha")
    weak = await _upload(client, session["id"], "weak.txt", b"alpha beta gamma")

    results = await _search(client, session["id"], "alpha", k=5)
    assert [row["document_id"] for row in results[:2]] == [strong["id"], weak["id"]]
    assert results[0]["score"] > results[1]["score"]


async def test_top_k_caps_the_number_of_results(client):
    await login(client)
    session = await _session(client, "Many")
    for index in range(5):
        await _upload(client, session["id"], f"doc{index}.txt", f"alpha content number {index}".encode())

    results = await _search(client, session["id"], "alpha", k=2)
    assert len(results) == 2


async def test_query_with_no_documents_returns_empty(client):
    await login(client)
    session = await _session(client, "Empty")
    assert await _search(client, session["id"], "anything") == []


async def test_embedding_dimension_mismatch_fails_explicitly(settings, database):
    app = create_app(settings=settings, db=database, embedder=FakeEmbedder(dimensions=64))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://testserver") as first:
        await login(first)
        session = await _session(first, "Locked")
        await _upload(first, session["id"], "notes.txt", b"some indexed content")

    changed = create_app(settings=settings, db=database, embedder=FakeEmbedder(dimensions=32))
    transport = ASGITransport(app=changed)
    async with AsyncClient(transport=transport, base_url="https://testserver") as second:
        await login(second)
        response = await second.post(
            f"/api/sessions/{session['id']}/search", json={"query": "content"}
        )
        assert response.status_code == 409
        assert "dimensions" in response.json()["detail"]


async def test_vector_store_is_selected_by_configuration(settings, database):
    local = settings.model_copy(update={"vector_store_backend": "local"})
    atlas = settings.model_copy(update={"vector_store_backend": "atlas"})
    assert isinstance(_build_vector_store(local, database), LocalVectorStore)
    assert isinstance(_build_vector_store(atlas, database), AtlasVectorStore)

