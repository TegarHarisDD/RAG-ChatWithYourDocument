# Spec: RAG — Chat Over Documents

**Issue tracker:** local markdown (`.scratch/<feature>/`)
**Triage label:** `ready-for-agent`
**Status:** ready for agent

---

## Problem Statement

I want a private, single-user web app where I can upload my own documents and ask questions about them in a chat interface, so that I can get grounded answers with citations back to the source instead of scrolling through PDFs myself.

Everything that exists today is either a paid SaaS product holding my documents, or a throwaway notebook script that forgets everything between runs. I want one place where a body of documents and the conversation about them persist together, and where starting a new topic means cleanly separating a new document set and a new conversation rather than polluting one endless thread.

I am the only person who will ever log in. There is no sign-up flow, no second user, and no sharing.

## Solution

A deployed web app with a login wall and two levels of organisation:

- A **session** is a topic workspace. It owns a set of uploaded **documents**.
- A **chat** is one conversation thread inside a session. A session can hold several chats, all grounded in the same document set.

After logging in I land on my sessions. I create a session, upload PDFs/DOCX/TXT/JSON/Markdown, watch them get processed, then start a chat. Answers stream back token by token, grounded only in that session's documents, with numbered citations I can click to jump to the exact source passage. I can rename, delete, and re-process anything at any level, and deleting a session takes its chats, messages, documents, and chunks with it.

The whole thing runs on free infrastructure: MongoDB Atlas M0 for storage and vector search, and OpenRouter for both the chat model and the embeddings.

### Domain glossary

These terms are used with these exact meanings throughout the spec and the code.

| Term | Meaning |
| --- | --- |
| **Session** | A topic workspace. Owns documents and chats. The unit of deletion and of document scoping. |
| **Chat** | One conversation thread inside a session. Owns messages. |
| **Message** | A single turn in a chat, either `user` or `assistant`, with optional citations. |
| **Document** | One uploaded file within a session, plus its extracted text and processing status. |
| **Chunk** | A slice of a document's extracted text, with its embedding vector. The unit of retrieval. |
| **Citation** | A link from an assistant message back to the specific chunk that supported a claim. |
| **Ingestion** | The pipeline from uploaded file to stored, embedded chunks. |
| **Retrieval** | Selecting the top-k chunks for a question, scoped to one session. |

## User Stories

### Authentication

1. As the app owner, I want to log in with a username and password, so that my documents and conversations are not readable by anyone who finds the URL.
2. As the app owner, I want there to be no registration page at all, so that nobody can create an account on my instance.
3. As the app owner, I want my credentials configured outside the codebase, so that my password is not committed to a public repo.
4. As the app owner, I want my password stored as a hash, so that a database or config leak does not reveal the plaintext.
5. As the app owner, I want an incorrect username or password to return the same generic error, so that an attacker cannot discover my username by probing.
6. As the app owner, I want repeated failed logins to be rate limited, so that a public deployment cannot be brute forced.
7. As the app owner, I want my login to persist across page refreshes, so that I am not retyping my password constantly.
8. As the app owner, I want to log out explicitly, so that I can end a session on a shared machine.
9. As the app owner, I want an expired or invalid session to send me back to the login page rather than showing a broken screen, so that the failure mode is obvious.
10. As the app owner, I want every API route except login and health to require authentication, so that no data endpoint is accidentally public.

### Sessions

11. As the app owner, I want to create a session, so that I can group documents and conversations by topic.
12. As the app owner, I want to name a session, so that I can tell my sessions apart in the sidebar.
13. As the app owner, I want a session to get a sensible default name if I do not supply one, so that I can move fast without inventing titles.
14. As the app owner, I want to see all my sessions ordered by most recently active, so that what I am working on is at the top.
15. As the app owner, I want to see how many documents each session holds, so that I can tell a populated session from an empty one at a glance.
16. As the app owner, I want to rename a session, so that a topic name can be corrected after the fact.
17. As the app owner, I want to delete a session and have its chats, messages, documents, and chunks deleted with it, so that I do not leave orphaned data consuming my free-tier quota.
18. As the app owner, I want a confirmation step before deleting a session, so that one misclick cannot destroy a topic's worth of work.
19. As the app owner, I want sessions to be strictly independent, so that a question in one session can never retrieve a chunk from another.

### Chats

20. As the app owner, I want to start a chat inside a session, so that I can have a separate conversation without re-uploading documents.
21. As the app owner, I want multiple chats per session, so that I can explore different angles on the same document set without one thread growing unwieldy.
22. As the app owner, I want to name a chat, so that I can find a past conversation again.
23. As the app owner, I want a chat to get a default name, so that starting one is a single click.
24. As the app owner, I want to list the chats in a session, so that I can jump back into an earlier conversation.
25. As the app owner, I want to rename a chat, so that a vague conversation can be labelled once I know what it turned out to be.
26. As the app owner, I want to delete a chat, so that dead-end explorations can be cleared away.
27. As the app owner, I want deleting a chat to delete its messages and not its session's documents, so that clearing a conversation does not cost me my uploaded files.
28. As the app owner, I want to clear a chat's messages while keeping the chat itself, so that I can restart a line of questioning in place.

### Documents

29. As the app owner, I want to upload PDF files, so that I can query papers and reports.
30. As the app owner, I want to upload DOCX files, so that I can query documents I wrote in Word.
31. As the app owner, I want to upload TXT files, so that I can query plain notes and logs.
32. As the app owner, I want to upload Markdown files, so that I can query my own written notes.
33. As the app owner, I want to upload JSON files, so that I can query structured data exports.
34. As the app owner, I want to upload several files at once, so that assembling a document set is one action.
35. As the app owner, I want to see each document's processing status, so that I know when it is safe to ask questions about it.
36. As the app owner, I want to see why a document failed to process, so that I can fix the file rather than guess.
37. As the app owner, I want an unsupported or oversized file rejected at upload time with a clear message, so that I am not waiting on a job that was never going to work.
38. As the app owner, I want to see how many chunks a document produced, so that I can tell whether extraction actually found the text.
39. As the app owner, I want to rename a document, so that a cryptic filename can be made readable in citations.
40. As the app owner, I want to delete a document and have its chunks and embeddings deleted with it, so that removed material cannot be retrieved or cited.
41. As the app owner, I want to re-process a document, so that a failed extraction can be retried after a fix.
42. As the app owner, I want a list of a session's documents with their statuses, so that I can manage the set as a whole.
43. As the app owner, I want ingestion to run in the background, so that uploading a large PDF does not freeze the interface.
44. As the app owner, I want a scanned PDF with no text layer to fail with an explicit "no extractable text" error rather than producing an empty document, so that I understand OCR is needed.

### Chatting

45. As the app owner, I want to ask a question in a chat, so that I get an answer drawn from my documents.
46. As the app owner, I want the answer to stream in token by token, so that I am reading immediately rather than watching a spinner.
47. As the app owner, I want answers grounded only in the session's documents, so that the model does not answer from its own general knowledge and mislead me.
48. As the app owner, I want numbered citations inline in the answer, so that I can verify any claim.
49. As the app owner, I want each citation to name its source document, so that I know which file a claim came from.
50. As the app owner, I want to click a citation and see the actual source passage, so that I can check the model read it correctly.
51. As the app owner, I want to be told when nothing relevant was found, so that I do not mistake an ungrounded answer for a grounded one.
52. As the app owner, I want to be told when a session has no ready documents, so that I know to upload something first.
53. As the app owner, I want my question recorded even if the model call fails, so that I can retry without retyping.
54. As the app owner, I want a rate-limited free model to be retried with backoff, so that a transient 429 does not lose my question.
55. As the app owner, I want a clear error when the model is genuinely unavailable, so that I am not staring at a dead stream.
56. As the app owner, I want to reopen a chat and see its full history, so that conversations persist across sessions of use.
57. As the app owner, I want to stop a response mid-stream, so that a runaway answer does not burn my quota.
58. As the app owner, I want what was already streamed to be kept when I stop, so that a partial answer is still useful.
59. As the app owner, I want the model to treat document text as data and not as instructions, so that a malicious or accidental prompt inside a document cannot hijack the answer.
60. As the app owner, I want the retrieval scope capped to a few chunks, so that I stay within the free model's context window.

### Interface

61. As the app owner, I want a login page, so that the app is usable without remembering API calls.
62. As the app owner, I want a sidebar of sessions and their chats, so that navigation is one click from anywhere.
63. As the app owner, I want the document panel and the chat panel visible together, so that I can see what a chat is grounded in while I read an answer.
64. As the app owner, I want a visible upload progress and processing state, so that I trust the app is working during a slow ingest.
65. As the app owner, I want optimistic feedback on rename and delete, so that the interface feels immediate.
66. As the app owner, I want the interface to work down to a narrow laptop window, so that I can use it without a large monitor.
67. As the app owner, I want to land back on the last thing I was doing after a refresh, so that I do not lose my place.

### Operations

68. As the app owner, I want the frontend and backend served from one origin, so that cookies work without cross-origin CORS config.
69. As the app owner, I want a health endpoint, so that I can check a deployment is alive.
70. As the app owner, I want a single documented command to run the whole stack locally, so that I can develop without remembering the incantation.
71. As the app owner, I want the vector search index creation documented as a one-time setup step, so that a fresh cluster can be brought up from the README.
72. As the app owner, I want secrets to come from environment variables with a committed `.env.example`, so that setup is reproducible without leaking keys.

## Implementation Decisions

### Stack and shape

- **Backend:** FastAPI (Python). **Frontend:** React + TypeScript, built with Vite. **Storage:** MongoDB Atlas M0. **LLM + embeddings:** OpenRouter. **Glue:** LangChain.
- **Single origin.** FastAPI serves the built React bundle as static files, and in development Vite proxies `/api` to the backend. This makes the app one deployable service and, critically, makes the auth cookie same-origin — no `SameSite=None`, no credentialed CORS, no third-party-cookie problems.
- **No user collection and no tenancy.** The owner is not a database row; there is exactly one identity, configured by environment variables. No `user_id` field is threaded through the schema. This is deliberate and reversible if a second user ever appears, but carrying it now would be speculative complexity.

### Authentication

- Credentials come from `APP_USERNAME` and `APP_PASSWORD_HASH`. The hash is produced by a documented one-liner against a committed script, and the plaintext password is never stored.
- Verification uses a constant-time comparison and returns one generic error for both "unknown user" and "wrong password".
- On success the backend sets an **httpOnly, Secure, SameSite=Lax cookie** holding a signed token with an expiry. The token is not readable by JavaScript, so an XSS bug cannot exfiltrate the session.
- A **login rate limiter** keyed by client IP bounds failed attempts. Because the app is publicly reachable, this is in scope, not a later hardening step.
- A FastAPI dependency resolves the current owner from the cookie and rejects with 401. Every router except `auth` and `health` depends on it. The React app treats any 401 as "navigate to login".

### Data model

Four collections, plus a small meta document.

- **`sessions`** — `title`, `created_at`, `last_active_at`. `last_active_at` is bumped on new message or new document and drives sidebar ordering, so "recently active" is an indexed read rather than a computed scan.
- **`chats`** — `session_id`, `title`, `created_at`, `last_active_at`.
- **`messages`** — `chat_id`, `session_id` (denormalised for cheap cascade and scope checks), `role` (`user` | `assistant`), `content`, `citations[]`, `created_at`, `model`, `finish_reason`.
- **`documents`** — `session_id`, `filename`, `content_type`, `size_bytes`, `extracted_text`, `status` (`pending` | `processing` | `ready` | `failed`), `error`, `chunk_count`, `chunk_index_version`, `embedding_model`, `created_at`, `updated_at`.
- **`chunks`** — `session_id`, `document_id`, `chunk_index`, `text`, `embedding`, plus locator metadata (`page` for PDFs, `section` for Markdown, `path` for JSON).
- **`meta`** — a single document recording the active `embedding_model` and its dimensions.

Cascade deletes are explicit, ordered deletes issued by the service layer — delete a session and it deletes its chats, then those chats' messages, then its documents, then its chunks. MongoDB has no cascading foreign keys, so this is application responsibility and is easy to get wrong; it is a first-class decision, not an afterthought.

**Original file bytes are not stored.** Only extracted text and chunks are persisted. GridFS on an M0 cluster (512 MB) plus an ephemeral-disk host is not worth it, and downloading originals is out of scope. Extracted text is stored on the document so a document can be re-chunked and re-embedded without a re-upload.

### Embedding model lock

Dimension mismatches between an embedding model and an existing Atlas vector index are a silent, confusing failure. Every chunk records the `embedding_model` that produced it, and `meta` records the active model and its dimensions. A document is only embedded with a model matching `meta`; if the configured model differs from a session's existing chunks, the API refuses and surfaces "re-process this session's documents", rather than mixing incompatible vectors in one index.

### Ingestion

- **Async, polled.** Ingestion runs via FastAPI `BackgroundTasks` — no Celery, Redis, or external worker, because this is a single-user app on free infrastructure and the extra moving parts buy nothing. The frontend polls document status.
- Status transitions `pending → processing → ready` or `→ failed`, with `error` populated on failure.
- **Extraction** is per-format and isolated behind one interface so a new format is one new implementation: `pypdf` for PDF, `python-docx` for DOCX, direct read for TXT/Markdown, and for JSON a flatten-to-paths pass so a deeply nested export yields readable `path: value` lines rather than a wall of braces. PDF extraction records a `page` locator; Markdown records the nearest heading; JSON records the source path.
- **Rejected at upload:** unsupported extension or MIME, empty file, and files over the size cap. Validation checks the sniffed content type, not just the extension.
- **Chunking** uses LangChain's recursive character splitter over the extracted text, with a fixed chunk size and overlap, alongside the locator metadata above.
- Embeddings are requested from OpenRouter in batches, which matters because the endpoint is OpenAI-shaped and accepts an array of inputs.
- A document whose extraction yields no text fails with an explicit "no extractable text — this file may be a scan" error rather than becoming an empty, silently useless document.

### Retrieval and answering

- Retrieval is **Atlas Vector Search** through `langchain-mongodb`'s `MongoDBAtlasVectorSearch`, which keeps the retrieval path idiomatic LangChain rather than hand-rolled aggregation.
- The Atlas index declares `embedding` as a vector field with the model's dimensions and cosine similarity, and `session_id` as a **filter field** — filter fields must be declared explicitly in the index or filtering fails. Index creation is a **manual, documented one-time step** against the cluster (Atlas UI or Admin API), not something application code does at startup.
- **Session scoping is a filter on the vector search**, so cross-session leakage is prevented at the query level rather than by post-filtering.
- Top-k is small and fixed, with a context cap, sized to the free chat model's context window.
- The prompt places retrieved chunks in numbered blocks and instructs the model to cite `[n]`, to answer only from the provided context, and to treat the context as **data, never instructions**.
- **Empty retrieval short-circuits.** If no chunks clear the relevance bar, or the session has no `ready` documents, the backend returns a fixed message distinguishing "no documents yet" from "nothing relevant found" and flags it in the stream — it does not call the model and does not risk a hallucinated answer.
- **Citation mapping happens server-side.** The model emits `[n]`; the backend maps each to its chunk, resolves it to document name, page/section/path, and a snippet, and persists that alongside the message. Inline markers are the model's job; attribution is the server's, so a citation can never point at a nonexistent chunk.

### Streaming

- `POST` on the messages endpoint responds `text/event-stream` over SSE, emitting typed events: retrieved-sources, token deltas, the final citation payload, and a terminal event carrying `stop` or `error`.
- The browser's `EventSource` cannot issue a POST, so the frontend consumes the stream with `fetch` plus a `ReadableStream` reader.
- **The user's message is persisted before the model call**, so a model failure still leaves the question in the history.
- A client disconnect or explicit stop aborts the upstream request and **persists the partial assistant text** with a `stopped` finish reason, so a partial answer is not thrown away.
- Free models rate limit aggressively. The client retries 429 and 5xx with backoff, and when retries are exhausted the terminal event carries a distinguishable "model unavailable" error rather than a truncated stream.

### API surface

REST under `/api`, JSON, cookie-authenticated. Grouped: `auth` (login, logout, me); `sessions` (list, create, read, rename, delete); nested `chats` (list, create) and top-level `chats` (rename, delete, clear messages); nested `messages` under a chat (list, create-with-SSE); nested `documents` under a session (list, upload) and top-level `documents` (read status, rename, delete, re-process); plus `chunks` read for citation jumps and `health`.

Deletion returns 204. Unknown identifiers return 404 rather than 403, so the API does not confirm the existence of other objects. Uploads are `multipart/form-data`.

### Frontend

- Vite + React + TypeScript. **TanStack Query** for all server state, including the polling that backs ingestion status; local component state for view concerns. No Redux — there is one user and no meaningful client-side domain state.
- Three screens: login, session list, session detail.
- Session detail is a two-pane layout — document panel and chat panel — with the chat list and session list in the sidebar, so what an answer is grounded in is visible while reading it.
- Streaming chat is the one place not going through TanStack Query's cache, since it is a token stream rather than a request/response.
- Rename and delete are optimistic with rollback on error.
- The last opened session and chat are remembered so a refresh restores context.
- Any 401 from any query funnels to the login screen.

## Testing Decisions

**What makes a good test here.** A test drives the real FastAPI app over HTTP and asserts only on what a client can observe: status codes, response bodies, streamed events, and persisted state read back through the API. No test imports an internal function, asserts on a Mongo document's shape, or names a class that is not part of the API contract. If the whole retrieval pipeline were rewritten — a different splitter, a different vector store, a different prompt — every test should still pass. That is the standard being aimed at.

**The seam.** One: the ASGI application, driven with an HTTP test client (`httpx.ASGITransport`). There are no separate unit tests for extractors, splitters, or retrievers. A behaviour that matters is reachable through HTTP — "upload this file, ask this question, get this answer with this citation" — and asserting it there tests the composition, which is where the bugs actually live.

**Injected ports.** Three dependencies are injected at app construction so tests can be hermetic without a second test seam:

- **Chat model** — a scripted fake that records the prompt it was given and emits a canned stream.
- **Embedder** — a deterministic fake that maps text to a stable vector, so the same input always produces the same vector and similarity ordering is reproducible.
- **Vector store** — an in-memory implementation of the same port as the Atlas adapter.

The third exists for a concrete reason: `$vectorSearch` is an Atlas-only aggregation stage that cannot run against a local or emulated MongoDB, so a test suite that used the production retriever would require a live Atlas cluster on every run. The port also earns its keep in development.

**Persistence.** Tests run against a real MongoDB (the local instance from the compose file, or a dedicated test database), dropped between tests. Real Mongo is worth the small setup cost because the CRUD behaviour under test *is* Mongo query semantics — cascade deletes, ordering, filtering — and an in-memory Mongo emulator would let those silently diverge from production.

**What gets tested.** Each area maps to the external behaviour a user would notice:

- **Auth** — login with correct and incorrect credentials, generic error on both failure modes, unauthenticated access rejected on every non-public route, expired token rejected, logout invalidating the cookie, rate limit engaging after repeated failures.
- **Sessions and chats** — the full CRUD surface, cascade on delete, ordering by activity, optimistic rename reflected in a subsequent read.
- **Documents** — upload per format through the API, status reaching `ready`, a scanned/empty PDF failing with the documented error, an oversized or unsupported file rejected at upload, delete removing the document's chunks such that retrieval no longer returns them, re-process recovering a previously failed document.
- **Retrieval and answering** — with a scripted model and deterministic embedder, the strongest test available: upload a document containing a distinctive fact, ask about it, assert the scripted model *received that chunk in its prompt* and that the returned citation points at that document and chunk. This is what makes the pipeline verifiable without calling a real model.
- **Scope isolation** — a question in session A, where only session B holds a matching document, retrieves nothing and yields the "nothing found" response. This is the highest-value test in the suite.
- **Groundedness guardrails** — a session with no ready documents and a session whose documents do not match the question both short-circuit before the model is called.
- **Streaming** — event ordering, the terminal event, partial persistence on stop, and the retry-then-error path when the fake model raises a rate-limit error.
- **Prompt construction** — asserted indirectly, by inspecting the prompt the scripted model received: session's chunks present, no other session's chunks present, numbered context blocks, and the data-not-instructions framing.

**Prior art.** The repository is empty, so there is no existing test convention to match. The suite establishes one: pytest with an app fixture that wires fakes over a per-test database, and tests written as HTTP calls. Later work should follow that fixture rather than inventing a second harness.

## Out of Scope

- **Registration, multiple users, sharing, collaboration, and any per-user data scoping.**
- **OCR** for scanned PDFs and images. A scan fails explicitly; it is not silently emptied.
- **Formats beyond** PDF, DOCX, TXT, JSON, and Markdown — no XLSX, PPTX, HTML, or EPUB.
- **Storing or serving original file bytes.** Extracted text only; no download-original feature.
- **Reranking, hybrid/BM25 search, query expansion, and multi-query retrieval.** Vector search only.
- **LLM-generated session or chat titles.** Default titles are deterministic and user-editable.
- **A retrieval-quality or answer-quality evaluation harness.**
- **Editing document text in the app.**
- **Multi-step agentic behaviour** — tool calls, web search, or follow-up question generation.
- **Production hardening beyond what is listed above:** no audit log, no backup/restore strategy, no metrics, tracing, or alerting, no CI/CD pipeline.
- **Migrating off the free tiers**, private networking, or a paid cluster.

## Further Notes

**One interpretation to confirm.** The brief lists "CRUD previous chats" and "CRUD sessions" as separate bullets, which this spec reads as two distinct entities: a session owns documents and can contain several chats, and a chat is one conversation. That reading is what makes the two bullets mean different things and is what makes "each session uses its own uploaded documents" — rather than each conversation — the natural phrasing. If the intent was actually one flat entity where a session *is* a conversation, say so before implementation starts: the change is small in the data model but touches the API surface, the sidebar, and roughly a third of the user stories.

**Free-tier realities that shaped the design.** OpenRouter's free tier covers chat models only — the embeddings endpoint is billed, so embedding cost is small but nonzero and worth a usage glance. Free chat models are rate limited hard enough that retry-with-backoff and a distinguishable "model unavailable" error are load-bearing, not polish. Atlas M0 allows one free cluster per project, runs search on the same node as the database, and its automated-embedding path is capped at 3 requests/minute without a payment method — which is why embeddings are requested from OpenRouter in batches instead.

**Suggested build order.** Auth and the session/chat CRUD can be built and tested end-to-end before any RAG exists, since the seam is HTTP and the fakes arrive with the first retrieval test. Ingestion and retrieval are where the real risk sits, so they should not be left until last.

**Repository state.** This directory is not yet a git repository. Initialising it, adding a `.gitignore` covering `.env` and the virtualenv, and committing a `.env.example` should happen alongside the first implementation work — the secrets story depends on it.

**Tooling prerequisite.** This spec was written without the per-repo configuration that the engineering skills expect (`docs/agents/issue-tracker.md`, triage labels, domain docs). Run `/setup-matt-pocock-skills` and select **local markdown** as the tracker so that `to-tickets`, `triage`, and `implement` can read this spec from the place they expect.
