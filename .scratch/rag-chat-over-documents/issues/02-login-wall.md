# 02: Login wall

**What to build:** Visiting any page while logged out lands on a login screen. Correct credentials let you in and persist across refreshes; wrong username and wrong password are indistinguishable; repeated failures are rate limited; logging out ends the session. Every data route is closed to anyone unauthenticated. There is no registration page and no way to create a second account.

**Blocked by:** 01 (Walking skeleton — one-origin app with Mongo connected)

**Status:** done

- [x] Visiting any app page while unauthenticated redirects to the login screen
- [x] Correct credentials set an httpOnly, Secure, SameSite=Lax cookie and land on the authenticated app
- [x] The cookie is not readable from JavaScript
- [x] Wrong username and wrong password return an identical generic error, with no observable difference in body or timing
- [x] Repeated failed attempts from one client are rate limited, and the limit clears once the window passes
- [x] Every API route except login and health rejects unauthenticated requests
- [x] An invalid, tampered, or expired cookie is rejected, and the client returns to the login screen rather than an error state
- [x] Logging out clears the cookie, and subsequent requests are rejected
- [x] The password is stored only as a hash, is never logged, and no credential is present in the repository
