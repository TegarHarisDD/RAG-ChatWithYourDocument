# 10: Ask a question, get a streamed grounded answer with citations

**What to build:** The whole point of the app. Type a question in a chat, watch tokens arrive, and read an answer grounded in that session's documents with numbered inline citations naming their source file. The prompt receives the session's top-k chunks in numbered blocks; citations are resolved server-side to real chunks, so one can never point at something that does not exist. Both turns persist and come back on reload. This is the first ticket where the app is genuinely useful.

**Blocked by:** 05 (Chats within a session), 09 (Atlas vector search, scoped to a session)

**Status:** done

- [x] Sending a message in a chat returns a streaming response that renders incrementally
- [x] The prompt contains the session's retrieved chunks as numbered context blocks
- [x] Only the current session's chunks can appear in the prompt
- [x] The answer contains inline numbered citations corresponding to those blocks
- [x] Citations are resolved server-side to real chunks, carrying document name and locator
- [x] A citation can never reference a chunk that was not supplied in the prompt
- [x] Both the user message and the assistant reply persist and reappear after a reload
- [x] The user message is persisted before the model is called
- [x] The stream terminates with an event distinguishing normal completion from failure
- [x] The model used and the finish reason are recorded with the assistant message
- [x] The retrieval scope is capped so the prompt stays inside the configured model's context window
