"""Application configuration, read from environment variables (and `.env`)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(ROOT_DIR / ".env"), str(ROOT_DIR / "backend" / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Optional override for the cookie-signing secret. Leave empty to have a
    # random one generated on first run and persisted in the database.
    secret_key: str = ""
    session_max_age: int = 60 * 60 * 24 * 7
    cookie_secure: bool = True

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "rag"

    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300

    # --- Uploads and ingestion ---
    max_upload_bytes: int = 10 * 1024 * 1024
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # --- Embeddings (OpenRouter, OpenAI-shaped embeddings endpoint) ---
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    embedding_model: str = "nvidia/nemotron-3-embed-1b:free"
    # 0 = auto-detect the model's native dimension from its first response.
    # Set an explicit value only to pin the Atlas vector index's numDimensions.
    embedding_dimensions: int = 0
    embedding_batch_size: int = 64
    embedding_timeout_seconds: float = 60.0

    # --- Chat (streaming chat arrives in ticket 10) ---
    # "openrouter/free" routes to whichever free model is available.
    chat_model: str = "openrouter/free"
    chat_temperature: float = 0.2
    chat_max_tokens: int = 1024
    chat_timeout_seconds: float = 120.0
    # Retrieval scope cap: how many chunks, and how many characters of context.
    rag_context_max_chars: int = 12000
    # Retry policy for rate-limited / transient free models.
    model_max_retries: int = 3
    model_retry_base_seconds: float = 1.0
    model_retry_max_seconds: float = 8.0

    # --- Retrieval ---
    # "local" (Mongo-backed cosine) or "atlas" ($vectorSearch). Atlas requires
    # the one-time index documented in the README.
    vector_store_backend: str = "local"
    atlas_vector_index: str = "chunks_vector_index"
    atlas_num_candidates: int = 100
    retrieval_top_k: int = 5
    # Chunks scoring below this are treated as "nothing relevant found".
    retrieval_min_score: float = 0.05

    # Optional override for the built frontend directory (used by tests).
    frontend_dist: str | None = None

    @property
    def cookie_name(self) -> str:
        return "session"


@lru_cache
def get_settings() -> Settings:
    return Settings()
