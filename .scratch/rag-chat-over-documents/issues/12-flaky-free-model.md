# 12: Survive a flaky free model

**What to build:** Free chat models rate limit aggressively, and that must not be your problem. A rate-limit or transient server error is retried with backoff and usually simply works. When retries run out you get a clear "model unavailable" state rather than a stream that quietly stops mid-sentence. Because your question is persisted before the model is called, a failure never loses it.

**Blocked by:** 10 (Ask a question, get a streamed grounded answer with citations)

**Status:** done

- [x] A rate-limit response from the model is retried with backoff and succeeds once the limit clears
- [x] Transient server errors are retried on the same policy
- [x] When retries are exhausted the stream ends with a distinguishable "model unavailable" state
- [x] The interface shows that state rather than a stream that appears to have stopped mid-sentence
- [x] The user's question is persisted even when every attempt fails
- [x] Retry attempts are bounded, so a genuine outage surfaces promptly instead of hanging
- [x] A failed attempt does not leave a partial or empty assistant message in the history
