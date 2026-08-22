import secrets
import time
from datetime import datetime, timezone

from flask import abort, redirect, request, session, url_for


def register_support_routes(app, db_connection, current_pseudo):
    """Send public support requests straight to the PlayBed admin inbox."""

    def now_iso():
        return datetime.now(timezone.utc).isoformat()

    def ensure_support_schema():
        with db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_reports (
                    id TEXT PRIMARY KEY,
                    reporter_pseudo TEXT,
                    target_type TEXT,
                    target_value TEXT,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT
                )
            """)
            conn.commit()

    def support_csrf_token():
        token = session.get("support_csrf")
        if not token:
            token = secrets.token_urlsafe(32)
            session["support_csrf"] = token
        return token

    @app.context_processor
    def inject_support_helpers():
        return {"support_csrf_token": support_csrf_token}

    @app.route("/contact-administrateur", methods=["POST"])
    def contact_administrator():
        supplied = request.form.get("csrf_token", "")
        expected = session.get("support_csrf", "")
        if not supplied or not expected or not secrets.compare_digest(supplied, expected):
            abort(400)

        category = (request.form.get("category") or "").strip().lower()
        game = (request.form.get("game") or "").strip()[:80]
        message = (request.form.get("message") or "").strip()

        labels = {
            "bug": "Bug",
            "suggestion": "Suggestion",
            "question": "Question",
            "other": "Autre demande",
        }
        if category not in labels or len(message) < 5 or len(message) > 1000:
            abort(400)

        last_report = float(session.get("last_support_report", 0) or 0)
        if time.time() - last_report < 30:
            return redirect(url_for("platform_contact", sent="too_fast"))

        reporter = current_pseudo() or None
        target_type = "game" if game else "content"
        target_value = labels[category]
        if game:
            target_value = f"{target_value} — {game}"

        ensure_support_schema()
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO admin_reports "
                "(id, reporter_pseudo, target_type, target_value, reason, status, created_at, resolved_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    secrets.token_hex(16),
                    reporter,
                    target_type,
                    target_value,
                    message,
                    "open",
                    now_iso(),
                    None,
                ),
            )
            conn.commit()

        session["last_support_report"] = time.time()
        return redirect(url_for("platform_contact", sent="1"))
