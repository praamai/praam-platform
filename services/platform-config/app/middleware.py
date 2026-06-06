"""Access logs and rate limiting."""

from __future__ import annotations

import time
from typing import Callable

from praam_platform.logging import StructuredLogger
from praam_platform.ratelimit import RateLimiter
from praam_platform.settings import PlatformSettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class AccessLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: PlatformSettings) -> None:
        super().__init__(app)
        self.logger = StructuredLogger("platform-config", json_output=settings.log_json)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        self.logger.http_access(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else "",
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: PlatformSettings) -> None:
        super().__init__(app)
        self.settings = settings
        self._limiter = RateLimiter(
            settings.rate_limit_max,
            settings.rate_limit_window_seconds,
        )

    def _client_key(self, request: Request) -> str:
        if auth := request.headers.get("authorization"):
            return f"auth:{auth[:24]}"
        host = request.client.host if request.client else "unknown"
        return f"ip:{host}"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.settings.rate_limit_enabled:
            return await call_next(request)
        if request.url.path.startswith("/v1/health"):
            return await call_next(request)
        key = self._client_key(request)
        if not self._limiter.allow(key):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
            )
        return await call_next(request)
