# RAG — Chat Over Documents

A private, single-user web app for uploading your own documents and asking
questions about them in a chat interface, with grounded answers and citations
back to the source. It covers the full flow: one-time first-run account setup,
login, session management with one continuous conversation per session,
document upload + ingestion for PDF/DOCX/TXT/Markdown/JSON, session-scoped
vector retrieval, and streamed grounded answers with click-through citations,
guardrails, retry/backoff for flaky free models, and a stop control.

Stack: **FastAPI** + **React/Vite/TypeScript** with **Tailwind CSS**, and
**MongoDB Atlas** for storage. One origin: the backend serves the built
frontend, so the auth cookie is same-origin.

## How it works

Create a session, upload at least one document, and a single continuous
conversation is ready for it — there is no separate "new chat" step. The
conversation is created automatically the first time the session is opened and
persists across reloads. The chat is enabled once at least one document reaches
`ready`. Deleting a session removes its conversation, documents, and chunks;
**Clear** empties the conversation in place without touching the documents.

## Prerequisites

- Python 3.10+
- Node.js 18+ (scripting via `npm.cmd` on Windows if PowerShell blocks `npm.ps1`)
- A MongoDB Atlas connection string (M0 free tier is fine)

## Setup

1. Copy the example environment file and fill in your Atlas connection string
   (and your OpenRouter API key):

   ```powershell
   Copy-Item .env.example .env
   ```

   Set `MONGODB_URI` to your Atlas connection string and `OPENROUTER_API_KEY` to
   your key. That is all the configuration required — there are no credentials
   to generate by hand.

2. Start the whole stack with one command:

   ```powershell
   .\dev.ps1
   ```

   This creates `backend\.venv`, installs dependencies, and runs the backend
   (`http://localhost:8000`) and Vite dev server (`http://localhost:5173`) via
   `concurrently`. Open `http://localhost:5173`.

3. On first run the app has no account yet, so it opens a **one-time setup**
   screen. Choose a username and password there; that single account is created
   and stored (as a bcrypt hash) in your database. Every later visit shows the
   normal sign-in form. If you ever need to start over, delete the `users`
   collection in your database.

There is no local database process: the database is Atlas, reached through
`MONGODB_URI`. (The one command starts the backend and frontend; the database
lives in the cloud.)

## Production build (single origin)

```powershell
npm run build      # builds frontend into frontend\dist
npm run start      # backend serves the API and the built frontend on :8000
```

Open `http://localhost:8000`. Set `COOKIE_SECURE=true` when serving over HTTPS.

## Environment variables

| Variable | Purpose | Example |
| --- | --- | --- |
| `SECRET_KEY` | Signs the session cookie; empty auto-generates and persists one | (empty) |
| `SESSION_MAX_AGE` | Cookie lifetime in seconds | `604800` |
| `COOKIE_SECURE` | `true` in production (HTTPS), `false` for local http | `false` |
| `MONGODB_URI` | Atlas connection string | `mongodb+srv://...` |
| `MONGODB_DB` | Database name; tests use `<name>_test` | `rag` |
| `LOGIN_RATE_LIMIT_ATTEMPTS` | Failed logins per IP before lockout | `5` |
| `LOGIN_RATE_LIMIT_WINDOW_SECONDS` | Rate-limit window length | `300` |
| `MAX_UPLOAD_BYTES` | Largest file accepted at upload, in bytes | `10485760` |
| `CHUNK_SIZE` | Characters per chunk | `1000` |
| `CHUNK_OVERLAP` | Overlap between adjacent chunks | `200` |
| `OPENROUTER_API_KEY` | Key for the embeddings endpoint | `sk-or-...` |
| `OPENROUTER_BASE_URL` | OpenRouter API base URL | `https://openrouter.ai/api/v1` |
| `EMBEDDING_MODEL` | Model that produces chunk vectors | `nvidia/nemotron-3-embed-1b:free` |
| `EMBEDDING_DIMENSIONS` | Vector dimensions; `0` auto-detects from the model | `0` |
| `EMBEDDING_BATCH_SIZE` | Chunk texts sent per embeddings request | `64` |
| `CHAT_MODEL` | Chat model (used by streaming chat) | `openrouter/free` |
| `VECTOR_STORE_BACKEND` | `local` (Mongo cosine) or `atlas` (`$vectorSearch`) | `local` |
| `ATLAS_VECTOR_INDEX` | Atlas vector search index name | `chunks_vector_index` |
| `ATLAS_NUM_CANDIDATES` | Atlas candidates considered per query | `100` |
| `RETRIEVAL_TOP_K` | Chunks returned per query | `5` |
| `RETRIEVAL_MIN_SCORE` | Below this score, nothing relevant was found | `0.05` |

`COOKIE_SECURE=false` is only for local development over plain http; a `Secure`
cookie is not sent over http, so leaving it `true` locally would break login.
Production must set it to `true`.

### Free models

The defaults use OpenRouter's free tier for both embeddings
(`nvidia/nemotron-3-embed-1b:free`) and chat (`openrouter/free`). Two caveats
come with `:free` endpoints: they are hard rate-limited (hence the retry and
backoff work), and they require enabling the free-model data policy in your
OpenRouter privacy settings. `EMBEDDING_DIMENSIONS=0` auto-detects the
embedding model's native dimension on first use. Swap in a paid embedding model
(e.g. `openai/text-embedding-3-small`) if the free rate limits are too tight.

## Tests

```powershell
npm test
```

Tests drive the real ASGI app over HTTP and run against a dedicated
`<MONGODB_DB>_test` database on the same cluster, dropped between tests. Set the
`MONGODB_URI` in `.env` before running them.

## API (implemented so far)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/health` | public | Liveness + database reachability |
| `GET` | `/api/auth/status` | public | Whether first-run setup is still required |
| `POST` | `/api/auth/setup` | public (once) | Create the single owner account |
| `POST` | `/api/auth/login` | public | Set session cookie |
| `POST` | `/api/auth/logout` | required | Clear session cookie |
| `GET` | `/api/auth/me` | required | Current owner |
| `GET` | `/api/sessions` | required | List sessions, most-recently-active first |
| `POST` | `/api/sessions` | required | Create a session |
| `GET` | `/api/sessions/{id}` | required | Read one session, including its `chat_id` |
| `PATCH` | `/api/sessions/{id}` | required | Rename a session |
| `DELETE` | `/api/sessions/{id}` | required | Delete a session and everything it owns |
| `GET` | `/api/sessions/{id}/chats` | required | List a session's chats (legacy; one is used) |
| `POST` | `/api/sessions/{id}/chats` | required | Create a chat (legacy; not used by the UI) |
| `GET` | `/api/chats/{id}` | required | Read one chat |
| `PATCH` | `/api/chats/{id}` | required | Rename a chat |
| `DELETE` | `/api/chats/{id}` | required | Delete a chat and its messages |
| `GET` | `/api/chats/{id}/messages` | required | List a chat's messages |
| `DELETE` | `/api/chats/{id}/messages` | required | Clear a chat's messages |
| `POST` | `/api/chats/{id}/messages` | required | Ask a question; streams an answer (SSE) |
| `GET` | `/api/sessions/{id}/documents` | required | List a session's documents |
| `POST` | `/api/sessions/{id}/documents` | required | Upload one or more files (multipart) |
| `GET` | `/api/documents/{id}` | required | Read one document's status |
| `PATCH` | `/api/documents/{id}` | required | Rename a document |
| `DELETE` | `/api/documents/{id}` | required | Delete a document and its chunks |
| `POST` | `/api/documents/{id}/reprocess` | required | Re-chunk and re-embed from stored text |
| `POST` | `/api/sessions/{id}/search` | required | Session-scoped retrieval (debug surface) |
| `GET` | `/api/chunks/{id}` | required | Read a chunk for citation click-through |

Uploads are validated by sniffing the content (not the filename extension) and
rejected at upload time when unsupported, empty, or over `MAX_UPLOAD_BYTES`.
Accepted files are stored `pending` and ingested in the background; poll
`GET /api/documents/{id}` (or the session's document list) until the status is
`ready` (with a chunk count) or `failed` (with a reason). PDFs/DOCX are
extracted with `pypdf`/`python-docx` (PDF chunks carry a `page` locator; a scan
with no text layer fails explicitly). Chunks are written behind the vector-store
port; retrieval (ticket 09) reads them back with session scoping as a filter on
the search rather than a post-filter.

### Streaming answers

`POST /api/chats/{id}/messages` responds `text/event-stream` with typed events:

| Event | Payload | Meaning |
| --- | --- | --- |
| `user` | `{message_id, content, created_at}` | The question, persisted before the model is called |
| `sources` | `{sources: [...]}` | The numbered chunks supplied to the model |
| `token` | `{text}` | A streamed answer delta |
| `citations` | `{citations: [...]}` | Server-resolved citations for `[n]` markers actually used |
| `guardrail` | `{reason, message, message_id}` | Short-circuit: `no_documents` or `nothing_relevant` |
| `done` | `{finish_reason, message_id}` | Terminal success (`stop`, or a guardrail reason) |
| `error` | `{reason, message}` | Terminal failure (`model_unavailable`) |

The prompt places the session's chunks in numbered blocks under a system frame
that treats the context as data, never instructions. Citations are resolved
server-side to real chunks, so a citation can never point at a chunk that was
not supplied. Rate-limited/transient model errors are retried with bounded
backoff; when retries run out the stream ends with `model_unavailable` and the
question is still in the history. Aborting the request (the Stop control) keeps
the partial answer with a `stopped` finish reason. Guardrail and failure cases
never persist a partial assistant answer.

## Atlas vector search index

Retrieval runs through `$vectorSearch` against the `chunks` collection. That
requires a **one-time** vector search index on the cluster; application code
does not create it. Create it once (Atlas UI → your cluster → Search → Create
Search Index → JSON editor) with this definition:

```json
{
  "fields": [
    { "type": "vector", "path": "embedding", "numDimensions": 2048, "similarity": "cosine" },
    { "type": "filter", "path": "session_id" }
  ]
}
```

- `numDimensions` must equal the dimensions your embedding model produces and
  the stored chunks were embedded with. With `EMBEDDING_DIMENSIONS=0` the model
  dimension is auto-detected from its first response and recorded in the `meta`
  collection (`{ "_id": "embedding", "dimensions": ... }`) — ingest one
  document, read that value, then create the index with it. Set
  `EMBEDDING_DIMENSIONS` explicitly to pin it instead. A mismatch fails
  explicitly at query time rather than silently returning nothing.
- `session_id` is declared as a **filter** field, because filter fields must be
  declared in the index or filtering fails. Retrieval uses it as the search
  filter, so a query can never return another session's chunks.
- The index name must match `ATLAS_VECTOR_INDEX` (`chunks_vector_index` by
  default).

Then select the adapter by configuration — no code change:

```powershell
VECTOR_STORE_BACKEND=atlas
```

Leave `VECTOR_STORE_BACKEND=local` (the default) for environments without an
Atlas index; it computes cosine similarity over the same `chunks` collection in
Python. Both adapters sit behind the same vector store port.
