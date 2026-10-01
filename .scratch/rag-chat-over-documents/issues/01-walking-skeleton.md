# 01: Walking skeleton — one-origin app with Mongo connected

**What to build:** You can run one command and open the app in a browser. A production build of the frontend is served by the backend on a single origin, the health endpoint answers honestly about the database, and secrets come from environment variables with a committed example file. This is the thin path that proves the deploy story — single origin, cookie-compatible — before any feature depends on it.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] A single documented command starts the backend and the database locally
- [x] Visiting the app's root URL renders the frontend, served from the same origin as the API — no second port in production mode
- [x] The health endpoint returns ok only when the database actually responds, and a non-ok status when it does not
- [x] Configuration is read from environment variables, with a committed example file listing every required variable and containing no real secrets
- [x] The local secrets file and the virtualenv are ignored by version control, and the example file is tracked
- [x] One documented command produces the frontend production build that the backend serves
- [x] Requesting an unknown non-API path returns the frontend app rather than a JSON 404, so client-side routes survive a hard refresh
