import hashlib
import os
import re
import secrets
import time
from urllib.parse import urlsplit

from flask import abort, g, jsonify, request


UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

_SCRIPT_OR_STYLE_TAG = re.compile(
    r"<(?P<tag>script|style)\b(?![^>]*\bnonce\s*=)(?P<attrs>[^>]*)>",
    re.IGNORECASE,
)
_BODY_CLOSE_TAG = re.compile(r"</body\s*>", re.IGNORECASE)
_CSP_EVENTS_SCRIPT = "/static/js/csp-events.js"


def _nonce_html_response(response, nonce):
    """Attach the request nonce to inline script/style tags and load the CSP bridge."""
    if response.direct_passthrough or response.mimetype != "text/html":
        return response

    body = response.get_data(as_text=True)
    if not body:
        return response

    def add_nonce(match):
        return f'<{match.group("tag")} nonce="{nonce}"{match.group("attrs")}>'

    body = _SCRIPT_OR_STYLE_TAG.sub(add_nonce, body)

    if _CSP_EVENTS_SCRIPT not in body:
        bridge = (
            f'<script nonce="{nonce}" defer src="{_CSP_EVENTS_SCRIPT}" '
            'data-playbed-csp-events="true"></script>'
        )
        if _BODY_CLOSE_TAG.search(body):
            body = _BODY_CLOSE_TAG.sub(lambda match: bridge + match.group(0), body, count=1)
        else:
            body += bridge

    response.set_data(body)
    return response


def register_security(app, db_connection):
    """Central security policy: rate limiting, origin checks and hardened response headers."""

    # Le vieux hook de core.py est remplacé par cette politique plus stricte.
    for scope, functions in list(app.after_request_funcs.items()):
        app.after_request_funcs[scope] = [
            function for function in functions
            if getattr(function, "__name__", "") != "security_headers"
        ]

    app.config.setdefault("MAX_CONTENT_LENGTH", 1024 * 1024)
    app.config.setdefault("MAX_FORM_MEMORY_SIZE", 128 * 1024)
    app.config.setdefault("MAX_FORM_PARTS", 200)

    configured_hosts = os.environ.get(
        "PLAYBED_TRUSTED_HOSTS",
        "playbed.fr,www.playbed.fr,playbed.onrender.com,localhost,127.0.0.1",
    )
    trusted_hosts = [host.strip() for host in configured_hosts.split(",") if host.strip()]
    if trusted_hosts:
        app.config["TRUSTED_HOSTS"] = trusted_hosts

    schema_ready = {"value": False}

    def ensure_schema():
        if schema_ready["value"]:
            return
        with db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS security_rate_limits (
                    bucket_key TEXT PRIMARY KEY,
                    window_start INTEGER NOT NULL,
                    hits INTEGER NOT NULL
                )
            """)
            conn.commit()
        schema_ready["value"] = True

    def client_ip():
        return (request.remote_addr or "unknown")[:128]

    def bucket_key(label):
        raw = f"{label}|{client_ip()}".encode("utf-8", "ignore")
        return hashlib.sha256(raw).hexdigest()

    def hit_rate_limit(label, limit, window_seconds):
        now = int(time.time())
        key = bucket_key(label)
        ensure_schema()
        with db_connection() as conn:
            row = conn.execute(
                "SELECT window_start, hits FROM security_rate_limits WHERE bucket_key = ?",
                (key,),
            ).fetchone()

            if not row or now - int(row["window_start"]) >= window_seconds:
                if row:
                    conn.execute(
                        "UPDATE security_rate_limits SET window_start = ?, hits = 1 WHERE bucket_key = ?",
                        (now, key),
                    )
                else:
                    conn.execute(
                        "INSERT INTO security_rate_limits (bucket_key, window_start, hits) VALUES (?, ?, 1)",
                        (key, now),
                    )
                hits = 1
                window_start = now
            else:
                hits = int(row["hits"]) + 1
                window_start = int(row["window_start"])
                conn.execute(
                    "UPDATE security_rate_limits SET hits = ? WHERE bucket_key = ?",
                    (hits, key),
                )

            if now % 97 == 0:
                conn.execute(
                    "DELETE FROM security_rate_limits WHERE window_start < ?",
                    (now - 86400,),
                )
            conn.commit()

        retry_after = max(1, window_seconds - (now - window_start))
        return hits > limit, retry_after

    def reject_rate_limit(retry_after):
        if request.path.startswith("/api/"):
            response = jsonify({"ok": False, "error": "rate_limited"})
            response.status_code = 429
        else:
            response = app.response_class(
                "Trop de requêtes. Réessaie dans quelques instants.",
                status=429,
                mimetype="text/plain",
            )
        response.headers["Retry-After"] = str(retry_after)
        return response

    def same_origin_request():
        origin = request.headers.get("Origin")
        if not origin:
            return True
        try:
            origin_parts = urlsplit(origin)
        except ValueError:
            return False
        origin_host = (origin_parts.netloc or "").lower()
        request_host = (request.host or "").lower()
        return origin_parts.scheme in {"https", "http"} and origin_host == request_host

    @app.before_request
    def prepare_csp_nonce():
        # One unpredictable nonce per HTTP response. Inline blocks only execute when
        # PlayBed itself stamped them with this nonce.
        g.csp_nonce = secrets.token_urlsafe(18)

    @app.before_request
    def enforce_security_policy():
        if request.method in UNSAFE_METHODS and not same_origin_request():
            abort(403)

        try:
            if request.path == "/admin/login" and request.method == "POST":
                limited, retry_after = hit_rate_limit("admin-login", 10, 15 * 60)
                if limited:
                    return reject_rate_limit(retry_after)

            if request.path == "/api/memory-flip" and request.method == "POST":
                limited, retry_after = hit_rate_limit("memory-flip", 180, 60)
                if limited:
                    return reject_rate_limit(retry_after)

            if request.path == "/api/memory-score" and request.method == "POST":
                limited, retry_after = hit_rate_limit("memory-score-legacy", 10, 60)
                if limited:
                    return reject_rate_limit(retry_after)

            if request.path == "/pseudo" and request.method == "POST":
                limited, retry_after = hit_rate_limit("pseudo-change", 30, 60)
                if limited:
                    return reject_rate_limit(retry_after)

            if request.method in UNSAFE_METHODS and request.path.startswith(
                ("/imposteur", "/action-verite", "/jeux/imposteur", "/jeux/action-verite")
            ):
                limited, retry_after = hit_rate_limit("room-write", 180, 60)
                if limited:
                    return reject_rate_limit(retry_after)
        except Exception:
            app.logger.exception("Rate limiting temporairement indisponible")
            if request.path == "/admin/login" and request.method == "POST":
                return app.response_class(
                    "Connexion administrateur temporairement indisponible.",
                    status=503,
                    mimetype="text/plain",
                )

        return None

    @app.after_request
    def harden_response(response):
        is_admin = request.path.startswith("/admin")
        nonce = getattr(g, "csp_nonce", secrets.token_urlsafe(18))

        response = _nonce_html_response(response, nonce)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        if is_admin:
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                f"script-src 'self' 'nonce-{nonce}' 'strict-dynamic'; "
                "script-src-attr 'none'; "
                f"style-src 'self' 'nonce-{nonce}'; "
                f"style-src-elem 'self' 'nonce-{nonce}'; "
                "style-src-attr 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "form-action 'self'; "
                "base-uri 'self'; "
                "object-src 'none'; "
                "upgrade-insecure-requests"
            )
        else:
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                f"script-src 'self' 'nonce-{nonce}' 'strict-dynamic' "
                "https://*.googletagmanager.com https://*.googlesyndication.com "
                "https://*.google.com https://*.doubleclick.net https://*.gstatic.com "
                "https://*.googleadservices.com; "
                "script-src-attr 'none'; "
                f"style-src 'self' 'nonce-{nonce}' https:; "
                f"style-src-elem 'self' 'nonce-{nonce}' https:; "
                "style-src-attr 'unsafe-inline'; "
                "img-src 'self' data: blob: https:; "
                "font-src 'self' data: https:; "
                "connect-src 'self' https://*.google-analytics.com https://*.googlesyndication.com "
                "https://*.google.com https://*.doubleclick.net https://*.googleadservices.com; "
                "frame-src 'self' https://*.googlesyndication.com https://*.google.com https://*.doubleclick.net; "
                "frame-ancestors 'self'; "
                "form-action 'self'; "
                "base-uri 'self'; "
                "object-src 'none'; "
                "upgrade-insecure-requests"
            )

        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"

        return response
