import time
import threading
from typing import Dict, List, Tuple
from fastapi import Request, HTTPException, status
from app.config import settings


class RateLimiter:
    """Thread-safe in-memory sliding window rate limiter."""

    def __init__(self):
        self._lock = threading.Lock()
        # Storage: { key: [timestamp1, timestamp2, ...] }
        self._records: Dict[str, List[float]] = {}
        self._last_cleanup = time.time()

    def _cleanup_expired(self, now: float, max_window: float = 300.0):
        """Periodically prune expired records to bound memory usage."""
        if now - self._last_cleanup < 60.0:
            return
        self._last_cleanup = now
        cutoff = now - max_window
        empty_keys = []
        for key, timestamps in self._records.items():
            self._records[key] = [t for t in timestamps if t > cutoff]
            if not self._records[key]:
                empty_keys.append(key)
        for k in empty_keys:
            del self._records[k]

    def is_allowed(
        self, client_id: str, max_requests: int, window_seconds: int = 60
    ) -> Tuple[bool, int, int]:
        """
        Check whether client_id is within max_requests in the window_seconds.
        Returns:
            (allowed: bool, remaining: int, retry_after: int)
        """
        if not settings.rate_limit_enabled:
            return True, max_requests, 0

        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            self._cleanup_expired(now, max_window=window_seconds * 2)

            timestamps = self._records.get(client_id, [])
            # Keep only timestamps within window
            valid_timestamps = [t for t in timestamps if t > window_start]

            if len(valid_timestamps) >= max_requests:
                # Limit exceeded. Calculate time until earliest record expires
                earliest = valid_timestamps[0]
                retry_after = max(1, int(earliest + window_seconds - now))
                self._records[client_id] = valid_timestamps
                return False, 0, retry_after

            # Record this request
            valid_timestamps.append(now)
            self._records[client_id] = valid_timestamps
            remaining = max(0, max_requests - len(valid_timestamps))
            return True, remaining, 0

    def reset(self):
        """Reset all rate limit tracking (useful for test suites)."""
        with self._lock:
            self._records.clear()


limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract client IP, taking X-Forwarded-For into account safely."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def rate_limit_dependency(key_prefix: str, max_requests: int, window_seconds: int = 60):
    """FastAPI dependency to enforce rate limiting on specific endpoints."""

    def dependency(request: Request):
        client_ip = get_client_ip(request)
        rate_key = f"{key_prefix}:{client_ip}"
        allowed, remaining, retry_after = limiter.is_allowed(
            rate_key, max_requests=max_requests, window_seconds=window_seconds
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds}s.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )
        # Store remaining in request state for response headers if needed
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_limit = max_requests

    return dependency
