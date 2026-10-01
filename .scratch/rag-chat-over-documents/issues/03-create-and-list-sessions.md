# 03: Create and list sessions

**What to build:** Log in and see a sidebar of your sessions, most recently active first, each showing how many documents it holds. Creating one persists it and puts it straight at the top, without a manual refresh. Opening a session shows its detail view. This is the first real domain object and it establishes the app shell that every later ticket hangs off.

**Blocked by:** 02 (Login wall)

**Status:** done

- [x] After logging in, the sidebar lists existing sessions ordered by most recently active
- [x] Creating a session persists it and it appears at the top of the list without a manual refresh
- [x] A session created without a title receives a sensible default rather than being nameless
- [x] Each session in the list shows its document count
- [x] Activity in a session moves it to the top of the list
- [x] The session list survives a page reload and a backend restart
- [x] Opening a session shows its detail view
- [x] Requesting a session that does not exist returns not-found rather than an error or an empty success
