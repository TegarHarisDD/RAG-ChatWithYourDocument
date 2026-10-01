"""A tiny in-process login rate limiter keyed by client IP.

Single-user, single-process app: an in-memory sliding window is sufficient and
avoids a Redis dependency. The window clears itself as timestamps age out.
"""

from __future__ import annotations

import time
from collections import defaultdict


class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, list[float]] = defaultdict(list)

    def _prune(self, key: str, now: float) -> None:
        cutoff = now - self.window_seconds
        self._failures[key] = [t for t in self._failures[key] if t > cutoff]

    def is_limited(self, key: str) -> bool:
        now = time.monotonic()
        self._prune(key, now)
        return len(self._failures[key]) >= self.max_attempts

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        self._prune(key, now)
        self._failures[key].append(now)

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)
