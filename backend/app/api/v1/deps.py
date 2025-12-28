"""
API Dependencies for Authentication.

Story P13-1.4: Implement API Key Authentication Middleware

Provides unified authentication that supports both JWT tokens and API keys.
This allows endpoints to accept either form of authentication.
"""
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import Optional, Union
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.api_key import APIKey
from app.api.v1.auth import get_current_user, COOKIE_NAME
from app.middleware.api_key_auth import APIKeyAuth, get_optional_api_key
from app.utils.jwt import decode_access_token, TokenError

logger = logging.getLogger(__name__)


class AuthResult:
    """
    Result of authentication attempt.

    Contains either a User (from JWT) or an APIKey (from X-API-Key header).
    Provides a unified interface for accessing authentication info.
    """

    def __init__(
        self,
        user: Optional[User] = None,
        api_key: Optional[APIKey] = None,
    ):
        self.user = user
        self.api_key = api_key

    @property
    def is_user_auth(self) -> bool:
        """Check if authenticated via JWT/user."""
        return self.user is not None

    @property
    def is_api_key_auth(self) -> bool:
        """Check if authenticated via API key."""
        return self.api_key is not None

    @property
    def is_authenticated(self) -> bool:
        """Check if any authentication is present."""
        return self.user is not None or self.api_key is not None

    @property
    def identifier(self) -> str:
        """Get a string identifier for logging."""
        if self.user:
            return f"user:{self.user.id}"
        if self.api_key:
            return f"api_key:{self.api_key.id}"
        return "anonymous"

    def has_scope(self, scope: str) -> bool:
        """
        Check if the authenticated entity has a given scope.

        For users, all scopes are implicitly granted (users have full access).
        For API keys, checks the key's scope list.
        """
        if self.user:
            # Users have all scopes (full access)
            return True
        if self.api_key:
            return self.api_key.has_scope(scope)
        return False


async def get_auth(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthResult:
    """
    Get authentication from either JWT or API key.

    This is the primary authentication dependency for endpoints that
    should accept both JWT tokens and API keys.

    Priority:
    1. API Key (X-API-Key header) - for programmatic access
    2. JWT Token (Cookie or Authorization header) - for user sessions

    Usage:
        @router.get("/endpoint")
        async def endpoint(auth: AuthResult = Depends(get_auth)):
            if auth.is_user_auth:
                # User is logged in via JWT
                user = auth.user
            elif auth.is_api_key_auth:
                # Request authenticated via API key
                api_key = auth.api_key

    Raises:
        HTTPException: 401 if neither valid JWT nor API key provided
    """
    # Try API key first (programmatic access takes priority)
    api_key = await get_optional_api_key(request, db)
    if api_key:
        return AuthResult(api_key=api_key)

    # Try JWT authentication
    try:
        user = get_current_user(request, db)
        return AuthResult(user=user)
    except HTTPException:
        pass

    # Neither authentication method worked
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Provide JWT token or API key.",
        headers={"WWW-Authenticate": "Bearer, ApiKey"},
    )


async def get_auth_with_scope(
    scope: str,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthResult:
    """
    Get authentication and verify the required scope.

    This is a factory function - use it to create scope-specific dependencies.

    Args:
        scope: Required scope (e.g., "read:events")
        request: FastAPI request
        db: Database session

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if authenticated but lacking scope
    """
    auth = await get_auth(request, db)

    if not auth.has_scope(scope):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required scope: {scope}",
        )

    return auth


def require_scope(scope: str):
    """
    Create a dependency that requires a specific scope.

    Usage:
        @router.get("/events")
        async def list_events(auth: AuthResult = Depends(require_scope("read:events"))):
            ...
    """
    async def dependency(
        request: Request,
        db: Session = Depends(get_db),
    ) -> AuthResult:
        return await get_auth_with_scope(scope, request, db)

    return dependency


# Pre-configured scope dependencies
require_read_events = require_scope("read:events")
require_read_cameras = require_scope("read:cameras")
require_write_cameras = require_scope("write:cameras")
require_admin = require_scope("admin")


async def get_optional_auth(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[AuthResult]:
    """
    Get authentication if present, but don't require it.

    Useful for endpoints that have different behavior for
    authenticated vs anonymous users.

    Returns:
        AuthResult if authenticated, None otherwise
    """
    # Try API key first
    api_key = await get_optional_api_key(request, db)
    if api_key:
        return AuthResult(api_key=api_key)

    # Try JWT authentication
    token = None
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if token:
        try:
            payload = decode_access_token(token)
            user_id = payload.get("user_id")
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.is_active:
                    return AuthResult(user=user)
        except TokenError:
            pass

    return None
