# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import logging
import time
import uuid
from typing import Annotated, Optional

from fastapi import Cookie, Depends, HTTPException, Request, status
from joserfc import errors, jwt

from app.util.settings import Settings

# Handle optional sentry import
try:
    if Settings().telemetry.enable:
        from sentry_sdk import set_user
    else:
        set_user = None
except Exception:
    set_user = None

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails"""

    pass


class AuthorizationError(Exception):
    """Raised when user lacks required permissions"""

    pass


def authenticate_request(request: Request, token: Optional[str] = Cookie(None)) -> dict:
    """
    Unified authentication handler for both Discord and API key auth
    Returns JWT payload dict or raises AuthenticationError
    """
    # Check for API key in Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer onboard_"):
        return _authenticate_api_key(auth_header)

    # Fallback to cookie-based JWT auth
    if token:
        return _authenticate_jwt_cookie(token)

    raise AuthenticationError("No valid authentication provided")


def _authenticate_api_key(auth_header: str) -> dict:
    """Validate API key and return equivalent JWT payload"""
    api_key = auth_header.replace("Bearer ", "")

    # Validate API key format
    if not api_key.startswith("onboard_live_"):
        raise AuthenticationError("Invalid API key format")

    # Check against configured keys
    configured_keys = Settings().api_keys or []
    key_config = None

    for config in configured_keys:
        if config.key == api_key:
            key_config = config
            break

    if not key_config:
        raise AuthenticationError("Invalid API key")

    logger.info(f"API key authentication successful: {key_config.name}")

    API_KEY_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, Settings().http.domain)
    api_key_uuid = str(uuid.uuid5(API_KEY_NAMESPACE, api_key))
    logger.debug(f"API key UUID generated: {api_key_uuid}")

    return {
        "discord": None,
        "name": "API Key",
        "pfp": None,
        "id": api_key_uuid,
        "sudo": True,
        "is_full_member": True,
        "issued": time.time(),
        "infra_email": None,
        "auth_method": "api_key",
        "api_key": True,
        "api_key_name": key_config.name,
    }


def _authenticate_jwt_cookie(token: str) -> dict:
    """Validate JWT cookie and return payload"""
    try:
        user_jwt = jwt.decode(
            token,
            Settings().jwt.key_object,
            algorithms=[Settings().jwt.algorithm],
        )
        return user_jwt.claims
    except Exception as e:
        if isinstance(e, errors.BadSignatureError):
            raise AuthenticationError("Invalid token signature")
        else:
            raise AuthenticationError(f"Token validation failed: {e}")


def get_current_user(request: Request, token: Optional[str] = Cookie(None)) -> dict:
    """
    FastAPI dependency to get current authenticated user
    Raises HTTPException on auth failure for web requests
    """
    try:
        user_jwt = authenticate_request(request, token)
    except AuthenticationError as e:
        # For API requests (with Authorization header), return 401
        if request.headers.get("Authorization"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

        # For web requests, redirect to Discord OAuth
        raise HTTPException(status_code=status.HTTP_302_FOUND, detail="Authentication required", headers={"Location": f"/discord/new?redir={request.url.path}"})

    # Session timeout check (skip for API keys)
    if not user_jwt.get("api_key", False):
        creation_date = user_jwt.get("issued", -1)
        if time.time() > creation_date + Settings().jwt.lifetime_user:
            if request.headers.get("Authorization"):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
            else:
                raise HTTPException(status_code=status.HTTP_302_FOUND, detail="Session expired", headers={"Location": f"/discord/new?redir={request.url.path}"})

    # Set Sentry user context if enabled
    if Settings().telemetry.enable and set_user is not None:
        set_user({"id": user_jwt["id"]})

    return user_jwt


def get_current_member(current_user: dict = Depends(get_current_user)) -> dict:
    """
    FastAPI dependency to ensure user is at least a member
    All authenticated users are considered members
    """
    return current_user


def get_current_admin(request: Request, current_user: dict = Depends(get_current_user)) -> dict:
    """
    FastAPI dependency to ensure user has admin privileges
    """
    if not current_user.get("sudo", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # Additional session timeout checks for non-API-key admin sessions
    if not current_user.get("api_key", False):
        creation_date = current_user.get("issued", -1)
        if time.time() > creation_date + Settings().jwt.lifetime_sudo:
            if request.headers.get("Authorization"):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin session expired")
            else:
                raise HTTPException(status_code=status.HTTP_302_FOUND, detail="Admin session expired - please re-authenticate", headers={"Location": f"/discord/new?redir={request.url.path}"})

    return current_user


# Type aliases for better IDE support and cleaner endpoint signatures
# These will NOT appear in OpenAPI specs because they use Depends()
CurrentUser = Annotated[dict, Depends(get_current_user)]
CurrentMember = Annotated[dict, Depends(get_current_member)]
CurrentAdmin = Annotated[dict, Depends(get_current_admin)]

# Alternative approach if the above shows up in OpenAPI (it shouldn't):
# Use these directly in function signatures instead of type aliases
# current_admin: dict = Depends(get_current_admin)


# Legacy compatibility function for gradual migration
class Authentication:
    """
    Legacy Authentication class for backward compatibility
    New code should use FastAPI dependencies instead
    """

    @staticmethod
    def create_jwt(user):
        """Keep existing JWT creation logic unchanged"""

        # Handle cases where discord relation might not be loaded
        discord_username = "Unknown"
        discord_avatar = None

        if hasattr(user, "discord") and user.discord:
            discord_username = user.discord.username
            discord_avatar = user.discord.avatar

        jwtData = {
            "discord": user.discord_id,
            "name": discord_username,
            "pfp": discord_avatar,
            "id": str(user.id),
            "sudo": user.sudo,
            "is_full_member": user.is_full_member,
            "issued": time.time(),
            "infra_email": user.infra_email,
            "auth_method": "discord",
            "api_key": False,
        }

        try:
            bearer = jwt.encode(
                {"alg": Settings().jwt.algorithm},
                jwtData,
                Settings().jwt.key_object,
            )
        except Exception as encode_error:
            logger.error(f"JWT encode error: {encode_error}")
            raise ValueError(f"Failed to encode JWT: {encode_error}")
        return bearer
