# 11: Groundedness guardrails

**What to build:** A session with no ready documents and a question nothing matches both short-circuit before the model is ever called, each with its own message so you know which situation you are in. Document text is framed as data to be read, never as instructions to follow, so a passage inside a document cannot hijack the answer. No hallucinated answer is ever presented to you as grounded.

**Blocked by:** 10 (Ask a question, get a streamed grounded answer with citations)

**Status:** done

- [x] A question in a session with no ready documents returns a specific "upload something first" response without calling the model
- [x] A question that nothing in the session matches returns a specific "nothing relevant found" response, distinguishable from the empty-session case
- [x] Neither case produces output that reads as a grounded answer
- [x] Retrieved document text is framed in the prompt as data to be read rather than instructions to follow
- [x] A document containing instruction-like text does not cause the model to act on it
- [x] Both short-circuit cases are surfaced in the interface as distinct states rather than as errors
