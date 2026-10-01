# 14: Click a citation to see the source passage

**What to build:** Citations stop being decoration and become verification. Clicking a citation in an answer reveals the exact chunk text it points at, named by its source document and locator, so you can judge for yourself whether the model read the source correctly.

**Blocked by:** 10 (Ask a question, get a streamed grounded answer with citations)

**Status:** done

- [x] Every citation in an assistant message is interactive
- [x] Activating a citation reveals the exact chunk text it points at
- [x] The revealed passage identifies its source document and its locator
- [x] Moving between citations updates the revealed passage rather than stacking views
- [x] A citation whose chunk has since been deleted degrades gracefully instead of erroring
- [x] The revealed passage is the same text that was supplied to the model, not a re-extraction
