"""Ingestion: from an uploaded byte payload to stored, embedded chunks.

Runs as a FastAPI background task so the upload request returns immediately and
the interface stays responsive. Status moves
``pending -> processing -> ready`` (or ``-> failed`` with a reason).

Original file bytes are not retained. The structured extracted text (segments
plus locators) is stored on the document, so a later re-process can re-chunk and
re-embed without a re-upload.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from bson import ObjectId

from ..config import Settings
from ..db import Database
from . import extraction
from .chunking import chunk_blocks
from .ports import Embedder, VectorStore


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _processing(db: Database, oid: ObjectId) -> None:
    await db.db.documents.update_one(
        {"_id": oid},
        {"$set": {"status": "processing", "error": None, "updated_at": _now()}},
    )


async def _fail(db: Database, oid: ObjectId, reason: str) -> None:
    await db.db.documents.update_one(
        {"_id": oid},
        {"$set": {"status": "failed", "error": reason, "updated_at": _now()}},
    )


async def _record_embedding_meta(db: Database, embedder: Embedder) -> None:
    await db.db.meta.update_one(
        {"_id": "embedding"},
        {
            "$set": {
                "embedding_model": embedder.model,
                "dimensions": embedder.dimensions,
                "updated_at": _now(),
            }
        },
        upsert=True,
    )


async def _embed_and_store(
    db: Database,
    vector_store: VectorStore,
    embedder: Embedder,
    settings: Settings,
    oid: ObjectId,
    session_id: str,
    segments: list[dict],
) -> None:
    """Chunk, embed, and replace this document's chunks; then mark it ready."""
    try:
        blocks = [extraction.TextBlock(text=s["text"], locator=s.get("locator", {})) for s in segments]
        chunks = await asyncio.to_thread(
            chunk_blocks, blocks, settings.chunk_size, settings.chunk_overlap
        )
        if not chunks:
            raise extraction.NoExtractableText("No extractable text — this file may be a scan")

        vectors = await embedder.embed([chunk["text"] for chunk in chunks])
        if len(vectors) != len(chunks):
            raise RuntimeError("Embedding provider returned the wrong number of vectors")
        for chunk, vector in zip(chunks, vectors):
            chunk["embedding"] = vector

        await vector_store.delete_document(str(oid))
        await vector_store.index_document(
            session_id=session_id,
            document_id=str(oid),
            chunks=chunks,
            embedding_model=embedder.model,
        )
        await _record_embedding_meta(db, embedder)

        await db.db.documents.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": "ready",
                    "error": None,
                    "chunk_count": len(chunks),
                    "embedding_model": embedder.model,
                    "updated_at": _now(),
                }
            },
        )
    except extraction.NoExtractableText as exc:
        await _fail(db, oid, str(exc))
    except Exception as exc:  # noqa: BLE001 - a durable, user-visible reason
        await _fail(db, oid, str(exc) or exc.__class__.__name__)


async def ingest_document(
    document_id: str,
    session_id: str,
    content: bytes,
    filename: str,
    db: Database,
    vector_store: VectorStore,
    embedder: Embedder,
    settings: Settings,
) -> None:
    oid = ObjectId(document_id)
    await _processing(db, oid)

    try:
        result = await asyncio.to_thread(extraction.extract, content, filename)
    except extraction.NoExtractableText as exc:
        await _fail(db, oid, str(exc))
        return
    except extraction.UnsupportedFileType as exc:
        await _fail(db, oid, str(exc))
        return
    except Exception as exc:  # noqa: BLE001
        await _fail(db, oid, str(exc) or exc.__class__.__name__)
        return

    segments = [{"text": block.text, "locator": block.locator} for block in result.blocks]
    await db.db.documents.update_one(
        {"_id": oid},
        {
            "$set": {
                "content_type": result.content_type,
                "extracted_text": "\n\n".join(block.text for block in result.blocks),
                "segments": segments,
                "updated_at": _now(),
            }
        },
    )
    await _embed_and_store(db, vector_store, embedder, settings, oid, session_id, segments)


async def reprocess_document(
    document_id: str,
    db: Database,
    vector_store: VectorStore,
    embedder: Embedder,
    settings: Settings,
) -> None:
    """Re-chunk and re-embed a document from its stored extracted text."""
    oid = ObjectId(document_id)
    doc = await db.db.documents.find_one({"_id": oid})
    if not doc:
        return

    segments = doc.get("segments")
    if not segments and doc.get("extracted_text"):
        segments = [{"text": doc["extracted_text"], "locator": {}}]
    if not segments:
        await _fail(db, oid, "No stored text to re-process — upload the file again")
        return

    await _processing(db, oid)
    await _embed_and_store(db, vector_store, embedder, settings, oid, doc["session_id"], segments)
