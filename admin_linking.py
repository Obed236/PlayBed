import hmac
import re
from datetime import datetime, timezone

from flask import abort, redirect, request, session, url_for


def register_admin_linking(app, db_connection):
    """Link PlayBed administrator identities to player pseudos."""

    def now_iso():
        return datetime.now(timezone.utc).isoformat()

    def ensure_schema():
        with db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_player_links (
                    admin_key TEXT PRIMARY KEY,
                    player_pseudo TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def valid_pseudo(value):
        value = (value or "").strip()
        return 2 <= len(value) <= 20 and bool(re.fullmatch(r"[A-Za-zÀ-ÿ0-9 _-]+", value))

    def current_admin_key():
        if session.get("admin_source") == "environment" or session.get("admin_role") == "super_admin":
            return "environment"
        account_id = session.get("admin_account_id")
        return f"account:{account_id}" if account_id else None

    def linked_pseudo(admin_key):
        if not admin_key:
            return None
        try:
            ensure_schema()
            with db_connection() as conn:
                row = conn.execute(
                    "SELECT player_pseudo FROM admin_player_links WHERE admin_key = ?",
                    (admin_key,),
                ).fetchone()
            return row["player_pseudo"] if row else None
        except Exception:
            app.logger.exception("Impossible de charger la liaison admin/pseudo")
            return None

    def verify_csrf():
        supplied = request.form.get("csrf_token", "")
        expected = session.get("admin_csrf", "")
        if not supplied or not expected or not hmac.compare_digest(supplied, expected):
            abort(400)

    def target_admin_key():
        target = (request.form.get("target") or "").strip()
        if target == "environment":
            return "environment"
        account_id = (request.form.get("account_id") or "").strip()
        if target == "account" and account_id:
            with db_connection() as conn:
                row = conn.execute(
                    "SELECT id FROM admin_accounts WHERE id = ? LIMIT 1",
                    (account_id,),
                ).fetchone()
            if row:
                return f"account:{account_id}"
        abort(400)

    def canonical_pseudo(pseudo):
        with db_connection() as conn:
            score_row = conn.execute(
                "SELECT pseudo FROM scores WHERE LOWER(pseudo) = LOWER(?) ORDER BY created_at DESC LIMIT 1",
                (pseudo,),
            ).fetchone()
        return score_row["pseudo"] if score_row else pseudo

    def save_link(admin_key, pseudo):
        canonical = canonical_pseudo(pseudo)
        with db_connection() as conn:
            conflict = conn.execute(
                "SELECT admin_key FROM admin_player_links WHERE LOWER(player_pseudo) = LOWER(?) AND admin_key <> ? LIMIT 1",
                (canonical, admin_key),
            ).fetchone()
            if conflict:
                return None, "Ce pseudo est déjà lié à un autre compte administrateur."

            existing = conn.execute(
                "SELECT admin_key FROM admin_player_links WHERE admin_key = ?",
                (admin_key,),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE admin_player_links SET player_pseudo = ?, updated_at = ? WHERE admin_key = ?",
                    (canonical, now_iso(), admin_key),
                )
            else:
                conn.execute(
                    "INSERT INTO admin_player_links (admin_key, player_pseudo, updated_at) VALUES (?, ?, ?)",
                    (admin_key, canonical, now_iso()),
                )
            conn.commit()
        return canonical, None

    def remove_link(admin_key):
        with db_connection() as conn:
            conn.execute("DELETE FROM admin_player_links WHERE admin_key = ?", (admin_key,))
            conn.commit()

    @app.context_processor
    def inject_admin_player_link_helpers():
        if not session.get("playbed_admin"):
            return {
                "admin_linked_pseudo": None,
                "admin_linked_player": lambda _key: None,
                "current_player_pseudo": session.get("pseudo"),
            }
        return {
            "admin_linked_pseudo": linked_pseudo(current_admin_key()),
            "admin_linked_player": linked_pseudo,
            "current_player_pseudo": session.get("pseudo"),
        }

    @app.route("/mon-compte-admin/pseudo", methods=["POST"])
    def admin_self_player_link_update():
        """Allow any authenticated admin to manage only their own player link."""
        if not session.get("playbed_admin"):
            return redirect(url_for("admin_login", next=url_for("admin_dashboard")))

        verify_csrf()
        ensure_schema()
        admin_key = current_admin_key()
        if not admin_key:
            abort(400)

        action = (request.form.get("action") or "link").strip()
        if action == "unlink":
            remove_link(admin_key)
            return redirect(url_for("admin_dashboard", message="Liaison avec ton pseudo joueur supprimée."))

        pseudo = (request.form.get("pseudo") or session.get("pseudo") or "").strip()
        if not valid_pseudo(pseudo):
            return redirect(url_for("admin_dashboard", error="Pseudo invalide : utilise un pseudo PlayBed de 2 à 20 caractères."))

        canonical, error = save_link(admin_key, pseudo)
        if error:
            return redirect(url_for("admin_dashboard", error=error))

        return redirect(url_for("admin_dashboard", message=f"Ton compte admin est maintenant associé au pseudo {canonical}."))

    @app.route("/admin/administrateurs/pseudo", methods=["POST"])
    def admin_player_link_update():
        """Super-admin management of any administrator/player association."""
        if not session.get("playbed_admin"):
            return redirect(url_for("admin_login", next=request.path))
        if session.get("admin_role") != "super_admin":
            abort(403)

        verify_csrf()
        ensure_schema()
        admin_key = target_admin_key()
        action = (request.form.get("action") or "link").strip()

        if action == "unlink":
            remove_link(admin_key)
            return redirect(url_for("admin_accounts_page", message="Liaison avec le pseudo supprimée."))

        pseudo = (request.form.get("pseudo") or "").strip()
        if not valid_pseudo(pseudo):
            return redirect(url_for("admin_accounts_page", error="Pseudo invalide : utilise un pseudo PlayBed de 2 à 20 caractères."))

        canonical, error = save_link(admin_key, pseudo)
        if error:
            return redirect(url_for("admin_accounts_page", error=error))

        return redirect(url_for("admin_accounts_page", message=f"Le pseudo {canonical} est maintenant lié au compte administrateur."))
