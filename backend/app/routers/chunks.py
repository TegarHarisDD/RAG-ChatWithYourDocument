"""Chunk reads, used by citation click-through (ticket 14).

Returns the exact stored chunk text that was supplied to the model, so the
revealed passage is never a re-extraction.
"""

from __future__ import annotations

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, status

from ..deps import DatabaseDep, OwnerDep
from ..schemas import ChunkOut

router = APIRouter(tags=["chunks"])


def _parse_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")


@router.get("/api/chunks/{chunk_id}", response_model=ChunkOut)
async def get_chunk(chunk_id: str, db: DatabaseDep, owner: OwnerDep):
    oid = _parse_id(chunk_id)
    chunk = await db.db.chunks.find_one({"_id": oid})
    if not chunk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")

    filename = None
    document = await db.db.documents.find_one(
        {"_id": _parse_id(chunk["document_id"])}, {"filename": 1}
    )
    if document:
        filename = document.get("filename")

    return ChunkOut(
        id=str(chunk["_id"]),
        session_id=chunk["session_id"],
        document_id=chunk["document_id"],
        filename=filename,
        chunk_index=chunk["chunk_index"],
        text=chunk["text"],
        locator=chunk.get("locator", {}),
    )
