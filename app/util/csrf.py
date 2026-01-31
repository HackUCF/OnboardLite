import logging
import re
from urllib.parse import urlparse

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.util.settings import Settings

logger = logging.getLogger(__name__)


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 0. Check Bypass Patterns
        path = request.url.path
        bypass_paths = Settings().security.bypass_paths

        # Simple prefix matching for bypass paths
        # Could be upgraded to regex if needed, but prefix is usually sufficient
        for bypass in bypass_paths:
            if path.startswith(bypass):
                return await call_next(request)

        method = request.method

        # 1. Check Sec-Fetch-Site (Modern Browsers)
        # Strict enforcement: Only allow same-origin and none.
        if "sec-fetch-site" in request.headers:
            sec_fetch_site = request.headers.get("sec-fetch-site")
            sec_fetch_mode = request.headers.get("sec-fetch-mode")

            # Go behavior: same-origin and none are allowed. same-site is NOT allowed by default.
            if sec_fetch_site in ["same-origin", "none"]:
                return await call_next(request)

            # Allow "navigate" mode (Top Level Navigation) for cross-site requests
            if sec_fetch_mode == "navigate" and method in ["GET", "HEAD"]:
                return await call_next(request)

            # Check Trusted Origins (Whitelist) for cross-site/same-site requests
            origin = request.headers.get("origin")
            if origin and self._is_trusted_origin(origin):
                return await call_next(request)

            # Block everything else
            return await self._handle_violation(request, f"Blocked by Sec-Fetch-Site. Mode: {sec_fetch_mode}, Site: {sec_fetch_site}")

        # 2. Fallback: Check Origin Header (Older Browsers / iOS 13)
        origin = request.headers.get("origin")
        if origin:
            # Check Whitelist First
            if self._is_trusted_origin(origin):
                return await call_next(request)

            # Go Behavior: Allow if Origin matches Host
            # This is the "Legacy Fallback" to support older browsers without configuration for every domain
            try:
                parsed_origin = urlparse(origin)
                # Ensure netloc is not empty
                if parsed_origin.netloc and parsed_origin.netloc == request.headers.get("host"):
                    return await call_next(request)
            except Exception:
                pass  # Fail closed

            return await self._handle_violation(request, f"Origin Mismatch. Origin: {origin}, Host: {request.headers.get('host')}")

        # 3. Neither header present -> Allow (Assume same-origin or non-browser)
        return await call_next(request)

    def _is_trusted_origin(self, origin: str) -> bool:
        trusted_origins = Settings().security.trusted_origins
        return origin in trusted_origins

    async def _handle_violation(self, request: Request, reason: str):
        msg = f"CSRF Violation: {reason} | Path: {request.url.path} | UA: {request.headers.get('user-agent')}"

        # Always Log
        logger.error(msg)

        # Report to Sentry if enabled (Monitoring)
        if Settings().telemetry.enable:
            try:
                import sentry_sdk

                with sentry_sdk.push_scope() as scope:
                    scope.set_tag("csrf_violation", "true")
                    sentry_sdk.capture_message(msg, level="error")
            except ImportError:
                pass
            except Exception as e:
                logger.error(f"Failed to report to Sentry: {e}")

        # Always Block (403)
        return Response(content="CSRF Protection: Request Denied", status_code=403)
