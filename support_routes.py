import hmac
import secrets
import time
from datetime import datetime, timezone
from functools import wraps

from flask import abort, redirect, render_template, request, session, url_for


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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_report_decisions (
                    report_id TEXT PRIMARY KEY,
                    admin_message TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def support_csrf_token():
        token = session.get("support_csrf")
        if not token:
            token = secrets.token_urlsafe(32)
            session["support_csrf"] = token
        return token

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("playbed_admin"):
                return redirect(url_for("admin_login", next=request.path))
            return view(*args, **kwargs)
        return wrapped

    def verify_admin_csrf():
        supplied = request.form.get("csrf_token", "")
        expected = session.get("admin_csrf", "")
        if not supplied or not expected or not hmac.compare_digest(supplied, expected):
            abort(400)

    def write_admin_log(action, details):
        try:
            with db_connection() as conn:
                conn.execute(
                    "INSERT INTO admin_logs (id, actor, action, details, created_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        secrets.token_hex(16),
                        session.get("playbed_admin", "admin"),
                        action,
                        details[:1000],
                        now_iso(),
                    ),
                )
                conn.commit()
        except Exception:
            app.logger.exception("Impossible d'enregistrer le journal du signalement")

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

    def support_center_view():
        pseudo = current_pseudo()
        support_requests = []
        if pseudo:
            try:
                ensure_support_schema()
                with db_connection() as conn:
                    support_requests = conn.execute(
                        """
                        SELECT r.id, r.target_type, r.target_value, r.reason, r.status,
                               r.created_at, r.resolved_at, d.admin_message
                        FROM admin_reports r
                        LEFT JOIN admin_report_decisions d ON d.report_id = r.id
                        WHERE LOWER(r.reporter_pseudo) = LOWER(?)
                        ORDER BY r.created_at DESC
                        LIMIT 20
                        """,
                        (pseudo,),
                    ).fetchall()
            except Exception:
                app.logger.exception("Impossible de charger l'historique du support")
        return render_template(
            "contact.html",
            pseudo=pseudo,
            support_requests=support_requests,
        )

    # platform_contact existe déjà quand ce module est enregistré.
    if "platform_contact" in app.view_functions:
        app.view_functions["platform_contact"] = support_center_view

    def enhanced_admin_reports():
        ensure_support_schema()
        with db_connection() as conn:
            reports = conn.execute(
                """
                SELECT r.id, r.reporter_pseudo, r.target_type, r.target_value, r.reason,
                       r.status, r.created_at, r.resolved_at, d.admin_message
                FROM admin_reports r
                LEFT JOIN admin_report_decisions d ON d.report_id = r.id
                ORDER BY r.created_at DESC LIMIT 200
                """
            ).fetchall()
        return render_template("admin/reports.html", reports=reports)

    def enhanced_admin_report_status():
        verify_admin_csrf()
        ensure_support_schema()
        report_id = (request.form.get("id") or "").strip()
        status = (request.form.get("status") or "").strip()
        admin_message = (request.form.get("admin_message") or "").strip()[:1000]

        if status not in {"open", "resolved", "dismissed"} or not report_id:
            abort(400)
        if status == "dismissed" and len(admin_message) < 5:
            return redirect(url_for("admin_reports", error="rejection_reason_required"))
        if status == "resolved" and not admin_message:
            admin_message = "La demande a été traitée par l’administrateur."

        resolved_at = now_iso() if status != "open" else None
        with db_connection() as conn:
            report = conn.execute(
                "SELECT id FROM admin_reports WHERE id = ?",
                (report_id,),
            ).fetchone()
            if not report:
                abort(404)

            conn.execute(
                "UPDATE admin_reports SET status = ?, resolved_at = ? WHERE id = ?",
                (status, resolved_at, report_id),
            )

            if status == "open":
                conn.execute(
                    "DELETE FROM admin_report_decisions WHERE report_id = ?",
                    (report_id,),
                )
            else:
                existing = conn.execute(
                    "SELECT report_id FROM admin_report_decisions WHERE report_id = ?",
                    (report_id,),
                ).fetchone()
                if existing:
                    conn.execute(
                        "UPDATE admin_report_decisions SET admin_message = ?, updated_at = ? WHERE report_id = ?",
                        (admin_message, now_iso(), report_id),
                    )
                else:
                    conn.execute(
                        "INSERT INTO admin_report_decisions (report_id, admin_message, updated_at) VALUES (?, ?, ?)",
                        (report_id, admin_message, now_iso()),
                    )
            conn.commit()

        action_label = {
            "open": "rouvert",
            "resolved": "résolu",
            "dismissed": "rejeté",
        }[status]
        write_admin_log(
            "report_status",
            f"Signalement {report_id} {action_label}" + (f" — {admin_message[:300]}" if admin_message else ""),
        )
        return redirect(url_for("admin_reports"))

    # Les routes admin sont enregistrées après ce module. On remplace leurs vues
    # une seule fois au premier appel HTTP, quand toute l'application est prête.
    installed = {"done": False}

    @app.before_request
    def install_enhanced_report_views():
        if installed["done"]:
            return None
        if "admin_reports" in app.view_functions and "admin_report_status" in app.view_functions:
            app.view_functions["admin_reports"] = admin_required(enhanced_admin_reports)
            app.view_functions["admin_report_status"] = admin_required(enhanced_admin_report_status)
            installed["done"] = True
        return None
