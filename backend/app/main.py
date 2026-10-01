"""FastAPI application factory.

One origin: the built React bundle is served by this same app, so the auth
cookie is same-origin and no credentialed CORS is involved.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import ROOT_DIR, Settings, get_settings
from .db import Database
from .rate_limit import RateLimiter
from .routers import auth, chats, chunks, documents, health, search, sessions
from .services.accounts import Accounts
from .services.embeddings import OpenRouterEmbedder
from .services.chat_model import OpenRouterChatModel
from .services.atlas_store import AtlasVectorStore
from .services.ports import ChatModel, Embedder, VectorStore
from .services.vector_store import LocalVectorStore


def _build_vector_store(settings: Settings, database: Database) -> VectorStore:
    if settings.vector_store_backend.lower() == "atlas":
        return AtlasVectorStore(database, settings.atlas_vector_index, settings.atlas_num_candidates)
    return LocalVectorStore(database)


def _frontend_dir(settings: Settings) -> Path:
    if settings.frontend_dist:
        return Path(settings.frontend_dist).resolve()
    return (ROOT_DIR / "frontend" / "dist").resolve()


def _mount_frontend(app: FastAPI, dist: Path) -> None:
    if not dist.is_dir():
        return

    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (dist / full_path).resolve()
        if candidate.is_file() and (candidate == dist or dist in candidate.parents):
            return FileResponse(candidate)
        index = dist / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Not Found")


def create_app(
    settings: Settings | None = None,
    db: Database | None = None,
    embedder: Embedder | None = None,
    vector_store: VectorStore | None = None,
    chat_model: ChatModel | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    database = db or Database(settings.mongodb_uri, settings.mongodb_db)
    accounts = Accounts(database)
    embedder = embedder or OpenRouterEmbedder(settings)
    vector_store = vector_store or _build_vector_store(settings, database)
    chat_model = chat_model or OpenRouterChatModel(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            await database.ensure_indexes()
            # Resolve/persist the cookie-signing secret before serving requests.
            await accounts.session_secret(settings.secret_key)
        except Exception:
            # A dead database must not stop the app from starting; /api/health
            # reports the real state.
            pass
        yield
        for closable in (embedder, chat_model):
            closer = getattr(closable, "aclose", None)
            if closer is not None:
                await closer()
        database.close()

    app = FastAPI(title="RAG — Chat Over Documents", lifespan=lifespan)
    app.state.settings = settings
    app.state.db = database
    app.state.accounts = accounts
    app.state.embedder = embedder
    app.state.vector_store = vector_store
    app.state.chat_model = chat_model
    app.state.rate_limiter = RateLimiter(
        settings.login_rate_limit_attempts,
        settings.login_rate_limit_window_seconds,
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(sessions.router)
    app.include_router(chats.router)
    app.include_router(documents.router)
    app.include_router(chunks.router)
    app.include_router(search.router)

    _mount_frontend(app, _frontend_dir(settings))
    return app


app = create_app()
