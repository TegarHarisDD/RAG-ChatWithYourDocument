# 05: Chats within a session

**What to build:** Open a session and create several conversations inside it, each named and each listed in the sidebar. Rename them, delete one, or clear one in place. Deleting a conversation takes its messages with it but leaves the session's documents completely untouched — clearing a line of questioning should never cost you uploaded files.

**Blocked by:** 03 (Create and list sessions)

**Status:** done

**Flow change (superseded UI):** the app now presents one continuous conversation per session, created automatically when the session is opened. The multi-chat sidebar and "+ New chat" are gone from the UI; the chat endpoints and this ticket's behaviour remain in the API for compatibility.

- [x] Opening a session lists the chats it contains
- [x] Creating a chat adds it to the session and opens it
- [x] A chat created without a title receives a sensible default
- [x] Renaming a chat persists and is reflected in the sidebar
- [x] Deleting a chat removes its messages while the session's documents remain present and still ready
- [x] Clearing a chat's messages empties the thread while keeping the chat in the list
- [x] A session can hold several chats, each with independent history
- [x] Chats belonging to one session are never visible from another
