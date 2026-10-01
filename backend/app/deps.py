"""Shared FastAPI dependencies and app-state accessors."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from .config import Settings
from .db import Database
from .rate_limit import RateLimiter
from .security import verify_token
from .services.accounts import Accounts
from .services.ports import ChatModel, Embedder, VectorStore


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Database:
    return request.app.state.db


def get_accounts(request: Request) -> Accounts:
    return request.app.state.accounts


def get_rate_limiter(request: Request) -> RateLimiter:
    return request.app.state.rate_limiter


def get_embedder(request: Request) -> Embedder:
    return request.app.state.embedder


def get_vector_store(request: Request) -> VectorStore:
    return request.app.state.vector_store


def get_chat_model(request: Request) -> ChatModel:
    return request.app.state.chat_model


def client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


async def require_owner(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    accounts: Annotated[Accounts, Depends(get_accounts)],
) -> str:
    """Resolve the authenticated owner from the session cookie, else 401."""
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    secret = await accounts.session_secret(settings.secret_key)
    username = verify_token(token, secret, settings.session_max_age)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    owner = await accounts.get_owner()
    if not owner or owner["username"] != username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return username


OwnerDep = Annotated[str, Depends(require_owner)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
DatabaseDep = Annotated[Database, Depends(get_db)]
AccountsDep = Annotated[Accounts, Depends(get_accounts)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]
VectorStoreDep = Annotated[VectorStore, Depends(get_vector_store)]
ChatModelDep = Annotated[ChatModel, Depends(get_chat_model)]
