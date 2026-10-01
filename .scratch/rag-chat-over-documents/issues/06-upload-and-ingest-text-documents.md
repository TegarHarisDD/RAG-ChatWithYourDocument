# 06: Upload and ingest text-format documents

**What to build:** Upload TXT, Markdown, and JSON files into a session, one or several at once. Each shows a status that moves from pending to processing to ready, a chunk count when done, and a reason when it fails. Text is extracted, chunked, and embedded in the background so the interface never freezes. Bad files are rejected at upload. Chunks land behind the vector store port using a local adapter, so this ticket is not blocked on Atlas setup.

**Blocked by:** 03 (Create and list sessions)

**Status:** done

- [x] TXT, Markdown, and JSON files can be uploaded into a session, one or several at once
- [x] Upload returns promptly and ingestion runs in the background — the interface stays responsive during a slow ingest
- [x] Document status moves pending → processing → ready, and the interface reflects each state without a manual reload
- [x] A ready document reports a nonzero chunk count
- [x] JSON is flattened so nested content becomes readable key-path lines rather than a wall of braces
- [x] Chunks carry their source document, their order within it, and a locator for where in the file they came from
- [x] Chunks are embedded through the configured embedding provider and stored behind the vector store port
- [x] Unsupported file types, files above the size cap, and empty files are rejected at upload with a specific reason
- [x] Content type is validated by inspecting the content, not by trusting the file extension
- [x] A failed ingestion records a reason that is visible in the document list
- [x] Uploading the same file twice produces two independent documents
- [x] Every chunk records which embedding model produced its vector
