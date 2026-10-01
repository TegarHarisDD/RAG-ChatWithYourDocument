# 13: Stop a stream and keep the partial answer

**What to build:** A stop control ends a runaway response, aborts the upstream request so it stops consuming quota, and keeps the text already streamed as a real message. Reload and it is still there, marked as stopped rather than as a complete answer.

**Blocked by:** 10 (Ask a question, get a streamed grounded answer with citations)

**Status:** done

- [x] A stop control is available while a response is streaming
- [x] Activating it ends the response and aborts the upstream request
- [x] Text streamed before the stop is persisted as a real assistant message
- [x] The stopped message records a stopped finish reason, distinguishable from normal completion
- [x] The partial message reappears after a reload
- [x] Stopping does not leave the chat unable to accept a new message
- [x] Stopping before any token arrives does not create an empty assistant message
