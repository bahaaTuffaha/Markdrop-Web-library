"""Optional single-password gate. Off unless MARKDROP_WEB_PASSWORD is set."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from .config import session_secret_path, web_password

COOKIE = "markdrop_session"
PUBLIC_PATHS = {
    "/login",
    "/api/login",
    "/api/logout",
    "/api/health",
    "/favicon.ico",
}


def _secret() -> bytes:
    path = session_secret_path()
    if not path.is_file():
        path.write_bytes(secrets.token_bytes(32))
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    return path.read_bytes()


def cookie_value() -> str:
    password = web_password() or ""
    digest = hmac.new(_secret(), password.encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()


def is_authenticated(request: Request) -> bool:
    if web_password() is None:
        return True
    return hmac.compare_digest(request.cookies.get(COOKIE, ""), cookie_value())


def login(password: str) -> bool:
    expected = web_password()
    if expected is None:
        return True
    return hmac.compare_digest(password, expected)


class PasswordMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if web_password() is None:
            return await call_next(request)
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith("/static/") or path.startswith("/assets/"):
            return await call_next(request)
        if is_authenticated(request):
            return await call_next(request)
        if path.startswith("/api/"):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return RedirectResponse("/login", status_code=302)
