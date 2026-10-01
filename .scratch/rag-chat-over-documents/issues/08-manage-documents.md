# 08: Manage documents

**What to build:** A document's lifecycle is fully under your control. Rename one so its name reads well in citations, delete one and trust its chunks are gone with it, re-process a failed one after fixing the underlying problem. Failure reasons sit in the list where you can see them, not behind a toast that has already disappeared.

**Blocked by:** 07 (PDF and DOCX extraction)

**Status:** done

- [x] Renaming a document persists, and the new name is what citations display
- [x] Deleting a document removes its chunks, and a later retrieval can no longer return them
- [x] Re-processing a failed document retries extraction and reaches ready once the underlying problem is fixed
- [x] Re-processing a ready document replaces its chunks rather than duplicating them
- [x] The document list shows status, chunk count, and failure reason together
- [x] Deleting one document leaves the session's other documents unaffected
- [x] Requesting a deleted document's identifier returns not-found
