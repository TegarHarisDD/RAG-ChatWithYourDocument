# 04: Rename and delete sessions

**What to build:** Session management is complete. Renaming corrects a topic name after the fact and is reflected in the sidebar. Deleting asks for confirmation first, then removes the session along with everything it owns. The cascade is established here as shared machinery, so later entities plug into it rather than each inventing their own.

**Blocked by:** 03 (Create and list sessions)

**Status:** done

- [x] Renaming a session persists it and the sidebar shows the new name
- [x] Deleting a session requires explicit confirmation before any request is sent
- [x] A session that owned chats, messages, documents, and chunks can be deleted, and none of that data is reachable through any endpoint afterwards
- [x] After deletion the session is gone from the list and the app navigates to a valid view rather than a dead one
- [x] Deleting a session with no chats and no documents succeeds
- [x] Requesting a deleted session's identifier returns not-found
