"""Pydantic request/response schemas (the API contract)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class SetupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class AuthStatus(BaseModel):
    setup_required: bool


class AuthUser(BaseModel):
    username: str


class SessionCreate(BaseModel):
    title: str | None = None


class SessionUpdate(BaseModel):
    title: str


class SessionOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    last_active_at: datetime
    document_count: int = 0
    chat_id: str | None = None


class ChatCreate(BaseModel):
    title: str | None = None


class ChatUpdate(BaseModel):
    title: str


class ChatOut(BaseModel):
    id: str
    session_id: str
    title: str
    created_at: datetime
    last_active_at: datetime


class MessageOut(BaseModel):
    id: str
    chat_id: str
    session_id: str
    role: str
    content: str
    citations: list[dict] = []
    created_at: datetime
    model: str | None = None
    finish_reason: str | None = None


class MessageCreate(BaseModel):
    content: str


class ChunkOut(BaseModel):
    id: str
    session_id: str
    document_id: str
    filename: str | None = None
    chunk_index: int
    text: str
    locator: dict = {}


class DocumentOut(BaseModel):
    id: str
    session_id: str
    filename: str
    content_type: str
    size_bytes: int
    status: str
    error: str | None = None
    chunk_count: int = 0
    embedding_model: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentUpdate(BaseModel):
    filename: str


class SearchRequest(BaseModel):
    query: str
    k: int | None = None


class SearchResultOut(BaseModel):
    document_id: str
    filename: str | None = None
    chunk_index: int
    text: str
    locator: dict = {}
    score: float


class MessageSearchResultOut(BaseModel):
    message_id: str
    chat_id: str
    session_id: str
    session_title: str = ""
    role: str
    snippet: str


class HealthOut(BaseModel):
    status: str
    database: str


class ErrorOut(BaseModel):
    detail: str = Field(default="error")
