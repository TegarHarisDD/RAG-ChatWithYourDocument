"""Password hashing and session-token signing.

The password is only ever stored as a bcrypt hash. The session token is a
signed, timestamped value (itsdangerous) so an expired or tampered cookie can
be rejected without a server-side session store.
"""

from __future__ import annotations

import hmac

import bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SALT = "rag-session"

# A valid bcrypt hash of a random string, used to make the unknown-username
# path take the same time as the wrong-password path.
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt())


def hash_password(plaintext: str) -> str:
    return bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plaintext: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plaintext.encode("utf-8"), hashed.encode("ascii"))
    except (ValueError, TypeError):
        return False


def verify_credentials(username: str, password: str, expected_username: str, expected_hash: str) -> bool:
    """Constant-ish-time verification with one generic outcome.

    Always performs a bcrypt check, even for an unknown username, so response
    timing does not reveal whether the username exists.
    """
    user_ok = hmac.compare_digest(username, expected_username)
    if user_ok and expected_hash:
        pass_ok = verify_password(password, expected_hash)
    else:
        # Burn comparable time; ignore the result.
        bcrypt.checkpw(password.encode("utf-8")[:72], _DUMMY_HASH)
        pass_ok = False
    return user_ok and pass_ok


def _serializer(secret_key: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key, salt=SALT)


def create_token(username: str, secret_key: str) -> str:
    return _serializer(secret_key).dumps({"u": username})


def verify_token(token: str, secret_key: str, max_age: int) -> str | None:
    """Return the username for a valid, unexpired token, else None."""
    try:
        data = _serializer(secret_key).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    return data.get("u")
