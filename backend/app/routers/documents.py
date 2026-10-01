"""Documents: upload into a session, list with status, read one.

Validation happens at upload (sniffed content type, size cap, emptiness); the
extraction/chunk/embed work runs in the background so the request returns fast.
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status

from ..config import Settings
from ..deps import DatabaseDep, EmbedderDep, OwnerDep, SettingsDep, VectorStoreDep
from ..schemas import DocumentOut, DocumentUpdate, SearchRequest, SearchResultOut
from ..services import cascade, extraction, retrieval
from ..services.ingestion import ingest_document, reprocess_document

router = APIRouter(tags=["documents"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_id(value: str, detail: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _to_out(doc: dict) -> DocumentOut:
    return DocumentOut(
        id=str(doc["_id"]),
        session_id=doc["session_id"],
        filename=doc["filename"],
        content_type=doc["content_type"],
        size_bytes=doc["size_bytes"],
        status=doc["status"],
        error=doc.get("error"),
        chunk_count=doc.get("chunk_count", 0),
        embedding_model=doc.get("embedding_model"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def _require_session(db, session_id: str) -> None:
    oid = _parse_id(session_id, "Session not found")
    if not await db.db.sessions.find_one({"_id": oid}, {"_id": 1}):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")


def _validate(filename: str, content: bytes, settings: Settings) -> str:
    """Return the sniffed content type or reject with a specific reason."""
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"File '{filename}' is empty"
        )
    if len(content) > settings.max_upload_bytes:
        cap_mb = settings.max_upload_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{filename}' exceeds the {cap_mb:g} MB size cap",
        )
    try:
        kind = extraction.detect_kind(content)
    except extraction.UnsupportedFileType as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"File '{filename}': {exc}"
        )
    if not extraction.is_supported(kind):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{filename}': unsupported file type ({kind.upper()})",
        )
    return extraction.CONTENT_TYPES[kind]


@router.get("/api/sessions/{session_id}/documents", response_model=list[DocumentOut])
async def list_documents(session_id: str, db: DatabaseDep, owner: OwnerDep):
    await _require_session(db, session_id)
    cursor = db.db.documents.find({"session_id": session_id}).sort([("created_at", 1)])
    return [_to_out(doc) for doc in await cursor.to_list(length=None)]


@router.post(
    "/api/sessions/{session_id}/documents",
    response_model=list[DocumentOut],
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_documents(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: DatabaseDep,
    vector_store: VectorStoreDep,
    embedder: EmbedderDep,
    settings: SettingsDep,
    owner: OwnerDep,
    files: list[UploadFile] = File(...),
):
    await _require_session(db, session_id)

    payloads: list[tuple[str, bytes, str]] = []
    for upload in files:
        content = await upload.read()
        content_type = _validate(upload.filename or "file", content, settings)
        payloads.append((upload.filename or "file", content, content_type))

    now = _now()
    documents = [
        {
            "session_id": session_id,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(content),
            "extracted_text": None,
            "status": "pending",
            "error": None,
            "chunk_count": 0,
            "embedding_model": None,
            "created_at": now,
            "updated_at": now,
        }
        for filename, content, content_type in payloads
    ]
    result = await db.db.documents.insert_many(documents)

    for position, ((filename, content, _), doc) in enumerate(zip(payloads, documents)):
        doc["_id"] = result.inserted_ids[position]
        background_tasks.add_task(
            ingest_document,
            str(doc["_id"]),
            session_id,
            content,
            filename,
            db,
            vector_store,
            embedder,
            settings,
        )

    await db.db.sessions.update_one(
        {"_id": ObjectId(session_id)}, {"$set": {"last_active_at": now}}
    )
    return [_to_out(doc) for doc in documents]


@router.get("/api/documents/{document_id}", response_model=DocumentOut)
async def get_document(document_id: str, db: DatabaseDep, owner: OwnerDep):
    oid = _parse_id(document_id, "Document not found")
    doc = await db.db.documents.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return _to_out(doc)


@router.patch("/api/documents/{document_id}", response_model=DocumentOut)
async def rename_document(
    document_id: str, payload: DocumentUpdate, db: DatabaseDep, owner: OwnerDep
):
    oid = _parse_id(document_id, "Document not found")
    filename = payload.filename.strip()
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Filename is required"
        )
    now = _now()
    doc = await db.db.documents.find_one_and_update(
        {"_id": oid}, {"$set": {"filename": filename, "updated_at": now}}, return_document=True
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return _to_out(doc)


@router.delete("/api/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str, db: DatabaseDep, vector_store: VectorStoreDep, owner: OwnerDep
):
    oid = _parse_id(document_id, "Document not found")
    doc = await db.db.documents.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    await cascade.delete_document(db, vector_store, document_id)


@router.post(
    "/api/documents/{document_id}/reprocess",
    response_model=DocumentOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reprocess(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: DatabaseDep,
    vector_store: VectorStoreDep,
    embedder: EmbedderDep,
    settings: SettingsDep,
    owner: OwnerDep,
):
    oid = _parse_id(document_id, "Document not found")
    doc = await db.db.documents.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    now = _now()
    doc = await db.db.documents.find_one_and_update(
        {"_id": oid},
        {"$set": {"status": "pending", "error": None, "updated_at": now}},
        return_document=True,
    )
    background_tasks.add_task(
        reprocess_document, document_id, db, vector_store, embedder, settings
    )
    return _to_out(doc)


@router.post("/api/sessions/{session_id}/search", response_model=list[SearchResultOut])
async def search(
    session_id: str,
    payload: SearchRequest,
    db: DatabaseDep,
    vector_store: VectorStoreDep,
    embedder: EmbedderDep,
    settings: SettingsDep,
    owner: OwnerDep,
):
    await _require_session(db, session_id)
    k = payload.k if payload.k is not None else settings.retrieval_top_k
    k = max(1, min(k, 20))
    query = payload.query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Query is required"
        )

    try:
        results = await retrieval.retrieve(
            db,
            vector_store,
            embedder,
            session_id,
            query,
            k,
            min_score=settings.retrieval_min_score,
        )
    except retrieval.RetrievalError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    document_ids = [row["document_id"] for row in results]
    names: dict[str, str] = {}
    if document_ids:
        cursor = db.db.documents.find({"_id": {"$in": [ObjectId(i) for i in document_ids]}})
        async for document in cursor:
            names[str(document["_id"])] = document["filename"]

    return [
        SearchResultOut(
            document_id=row["document_id"],
            filename=names.get(row["document_id"]),
            chunk_index=row["chunk_index"],
            text=row["text"],
            locator=row.get("locator", {}),
            score=float(row.get("score", 0.0)),
        )
        for row in results
    ]
