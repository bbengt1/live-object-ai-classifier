"""
API Key Rate Limiting Middleware.

Story P13-1.5: Implement API Key Rate Limiting

Provides rate limiting for API key authenticated requests.
Uses in-memory storage with configurable per-key limits.
"""
from fastapi import Request, HTTPException, status
from collections import defaultdict
from datetime import datetime, timezone
from threading import Lock
from typing import Optional
import logging

from app.models.api_key import APIKey

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, limit: int, remaining: int, reset_at: datetime):
        self.limit = limit
        self.remaining = remaining
        self.reset_at = reset_at

        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {limit}/minute. Retry after {int((reset_at - datetime.now(timezone.utc)).total_seconds())} seconds.",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(reset_at.timestamp())),
                "Retry-After": str(int((reset_at - datetime.now(timezone.utc)).total_seconds())),
            },
        )


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter using sliding window.

    Tracks request counts per API key with per-minute windows.
    Thread-safe implementation for concurrent requests.
    """

    def __init__(self):
        # Store: {api_key_id: [(timestamp, count), ...]}
        self._windows: dict[str, list[tuple[datetime, int]]] = defaultdict(list)
        self._lock = Lock()

    def check_rate_limit(
        self,
        api_key: APIKey,
        window_seconds: int = 60,
    ) -> tuple[bool, int, int, datetime]:
        """
        Check if request is within rate limit.

        Args:
            api_key: The API key making the request
            window_seconds: Window size in seconds (default 60 for per-minute)

        Returns:
            Tuple of (allowed, limit, remaining, reset_at)
        """
        now = datetime.now(timezone.utc)
        limit = api_key.rate_limit_per_minute
        window_start = now.timestamp() - window_seconds

        with self._lock:
            # Get requests in current window
            key_id = str(api_key.id)
            requests = self._windows[key_id]

            # Remove expired entries
            requests[:] = [
                (ts, count) for ts, count in requests
                if ts.timestamp() > window_start
            ]

            # Count requests in window
            current_count = sum(count for _, count in requests)

            # Calculate remaining and reset time
            remaining = max(0, limit - current_count - 1)  # -1 for this request
            reset_at = datetime.fromtimestamp(
                window_start + window_seconds, tz=timezone.utc
            )

            if current_count >= limit:
                return False, limit, 0, reset_at

            # Record this request
            requests.append((now, 1))

            return True, limit, remaining, reset_at

    def get_usage(self, api_key: APIKey, window_seconds: int = 60) -> dict:
        """Get current rate limit usage for an API key."""
        now = datetime.now(timezone.utc)
        window_start = now.timestamp() - window_seconds

        with self._lock:
            key_id = str(api_key.id)
            requests = self._windows.get(key_id, [])

            # Count requests in window
            current_count = sum(
                count for ts, count in requests
                if ts.timestamp() > window_start
            )

            return {
                "limit": api_key.rate_limit_per_minute,
                "remaining": max(0, api_key.rate_limit_per_minute - current_count),
                "reset_at": datetime.fromtimestamp(
                    window_start + window_seconds, tz=timezone.utc
                ).isoformat(),
            }

    def clear(self, api_key_id: Optional[str] = None):
        """Clear rate limit data for a specific key or all keys."""
        with self._lock:
            if api_key_id:
                self._windows.pop(api_key_id, None)
            else:
                self._windows.clear()


# Global rate limiter instance
_rate_limiter: Optional[InMemoryRateLimiter] = None


def get_rate_limiter() -> InMemoryRateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = InMemoryRateLimiter()
    return _rate_limiter


async def check_api_key_rate_limit(request: Request) -> None:
    """
    Middleware function to check API key rate limits.

    Should be called after API key authentication has stored
    the API key in request.state.api_key.

    Raises:
        RateLimitExceeded: If the rate limit is exceeded
    """
    api_key: Optional[APIKey] = getattr(request.state, "api_key", None)

    if not api_key:
        # No API key auth, skip rate limiting
        return

    rate_limiter = get_rate_limiter()
    allowed, limit, remaining, reset_at = rate_limiter.check_rate_limit(api_key)

    if not allowed:
        logger.warning(
            f"API key rate limit exceeded: {api_key.id}",
            extra={
                "event_type": "api_key_rate_limit_exceeded",
                "api_key_id": api_key.id,
                "api_key_name": api_key.name,
                "limit": limit,
            }
        )
        raise RateLimitExceeded(limit, remaining, reset_at)

    # Add rate limit headers to response
    # Note: These will be set by the endpoint or middleware
    request.state.rate_limit_headers = {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(int(reset_at.timestamp())),
    }


def add_rate_limit_headers(request: Request, response) -> None:
    """
    Add rate limit headers to response if present in request state.

    Call this in endpoints or middleware after check_api_key_rate_limit.
    """
    headers = getattr(request.state, "rate_limit_headers", None)
    if headers:
        for key, value in headers.items():
            response.headers[key] = value
