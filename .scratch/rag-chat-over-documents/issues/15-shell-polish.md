# 15: Shell polish

**What to build:** The interface stops being a scaffold. The document panel and the chat panel are visible at the same time, so you can see what an answer is grounded in while you read it. A refresh returns you to the session and chat you were in. An expired login funnels cleanly to the login screen instead of leaving a half-broken view. Renames and deletes apply immediately and roll back visibly when they fail. It works on a laptop screen.

**Blocked by:** 05 (Chats within a session), 10 (Ask a question, get a streamed grounded answer with citations)

**Status:** done

- [x] The document panel and the chat panel are visible simultaneously within a session
- [x] Refreshing restores the session and chat that were previously open
- [x] A 401 from any request funnels to the login screen and never leaves a broken view behind
- [x] Rename and delete apply immediately in the interface and roll back visibly when the request fails
- [x] The layout is usable at a narrow laptop width without the page scrolling horizontally
- [x] Loading, error, and empty states are visually distinguishable from one another
- [x] Destructive actions that fail surface why, rather than silently reverting
