"""Production security hardening for PlayBed.

Loaded by the production WSGI entry point. Keeps security controls centralized
without changing game behavior.
"""
import os
import time
from collections import defaultdict, deque
from threading import Lock

from flask import abort, request


_lock = Lock()
_attempts = defaultdict(deque)


def _client_key():
    # Render terminates TLS and supplies X-Forwarded-For. Only the first value
    # identifies the original client; never use the full attacker-controlled header.
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",", 1)[0].strip() if forwarded else request.remote_addr
    return ip or "unknown"


def _rate_limited(bucket, limit, window):
    now = time.monotonic()
    key = (bucket, _client_key())
    with _lock:
        values = _attempts[key]
        while values and now - values[0] > window:
            values.popleft()
        if len(values) >= limit:
            return True
        values.append(now)
        return False


def apply_security(app):
    # Cookies are never sent over plaintext HTTP in production.
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=1 * 1024 * 1024,
    )

    # Refuse the public development key if a deployment was misconfigured.
    if os.environ.get("RENDER") and app.secret_key == "playbed-v2-dev-secret-change-me":
        raise RuntimeError("SECRET_KEY must be configured in production")

    @app.before_request
    def playbed_security_limits():
        # Slow password guessing substantially. This is deliberately stricter
        # than public gameplay endpoints.
        if request.path == "/admin/login" and request.method == "POST":
            if _rate_limited("admin-login", 8, 15 * 60):
                abort(429)

        # Protect score/API endpoints from simple flooding and automation abuse.
        if request.path.startswith("/api/") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if _rate_limited("api-write", 120, 60):
                abort(429)

    @app.after_request
    def playbed_security_headers(response):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cache-Control"] = (
            "no-store" if request.path.startswith("/admin") else response.headers.get("Cache-Control", "")
        )

        # The request-specific CSP nonce and the final CSP header are owned by
        # security.register_security(). Keeping a second CSP here would overwrite
        # or conflict with the nonce-bearing policy when production uses wsgi.py.
        return response

    return app
