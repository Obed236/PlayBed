import hmac
import json
import os
import re
import secrets
from datetime import datetime, timezone
from functools import wraps

from flask import abort, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


ADMIN_PERMISSIONS = {
    "users": "Utilisateurs",
    "games": "Jeux",
    "scores": "Scores",
    "questions": "Quiz / Vrai-Faux",
    "action_verite": "Action ou Vérité",
    "reports": "Signalements",
    "announcements": "Annonces",
    "logs": "Journal admin",
    "settings": "Paramètres",
}

PATH_PERMISSIONS = (
    ("/admin/administrateurs", "super_admin"),
    ("/admin/utilisateurs", "users"),
    ("/admin/jeux", "games"),
    ("/admin/scores", "scores"),
    ("/admin/questions", "questions"),
    ("/admin/action-verite", "action_verite"),
    ("/admin/signalements", "reports"),
    ("/admin/annonces", "announcements"),
    ("/admin/journal", "logs"),
    ("/admin/parametres", "settings"),
)


def register_admin_accounts(app, db_connection):
    """Add multi-admin accounts and server-side permissions to the PlayBed back-office."""

    def now_iso():
        return datetime.now(timezone.utc).isoformat()

    def ensure_schema():
        with db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_accounts (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'admin',
                    permissions_json TEXT NOT NULL DEFAULT '[]',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_by TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id TEXT PRIMARY KEY,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def legacy_configured():
        username = os.environ.get("PLAYBED_ADMIN_USERNAME", "").strip()
        password_hash = os.environ.get("PLAYBED_ADMIN_PASSWORD_HASH", "").strip()
        password = os.environ.get("PLAYBED_ADMIN_PASSWORD", "")
        return bool(username and (password_hash or password))

    def legacy_credentials_valid(identifier, password):
        expected_username = os.environ.get("PLAYBED_ADMIN_USERNAME", "").strip()
        if not expected_username or not hmac.compare_digest(identifier, expected_username):
            return False

        password_hash = os.environ.get("PLAYBED_ADMIN_PASSWORD_HASH", "").strip()
        if password_hash:
            try:
                return check_password_hash(password_hash, password)
            except (ValueError, TypeError):
                return False

        expected_password = os.environ.get("PLAYBED_ADMIN_PASSWORD", "")
        return bool(expected_password) and hmac.compare_digest(password, expected_password)

    def parse_permissions(raw):
        try:
            values = json.loads(raw or "[]")
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
        if not isinstance(values, list):
            return []
        allowed = set(ADMIN_PERMISSIONS)
        return sorted({str(value) for value in values if str(value) in allowed})

    def database_account_by_login(identifier):
        ensure_schema()
        with db_connection() as conn:
            return conn.execute(
                """
                SELECT id, username, password_hash, role, permissions_json, active
                FROM admin_accounts
                WHERE LOWER(username) = LOWER(?)
                LIMIT 1
                """,
                (identifier,),
            ).fetchone()

    def database_account_by_id(account_id):
        ensure_schema()
        with db_connection() as conn:
            return conn.execute(
                """
                SELECT id, username, password_hash, role, permissions_json, active
                FROM admin_accounts WHERE id = ? LIMIT 1
                """,
                (account_id,),
            ).fetchone()

    def has_database_accounts():
        try:
            ensure_schema()
            with db_connection() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) AS n FROM admin_accounts WHERE active = 1"
                ).fetchone()
            return bool(row and int(row["n"]) > 0)
        except Exception:
            app.logger.exception("Impossible de vérifier les comptes administrateurs")
            return False

    def admin_configured():
        return legacy_configured() or has_database_accounts()

    def clear_admin_session():
        for key in (
            "playbed_admin",
            "admin_csrf",
            "admin_role",
            "admin_permissions",
            "admin_account_id",
            "admin_source",
        ):
            session.pop(key, None)

    def set_super_admin_session(username):
        session["playbed_admin"] = username
        session["admin_role"] = "super_admin"
        session["admin_permissions"] = list(ADMIN_PERMISSIONS)
        session["admin_source"] = "environment"
        session.pop("admin_account_id", None)
        session["admin_csrf"] = secrets.token_urlsafe(32)

    def set_database_admin_session(row):
        session["playbed_admin"] = row["username"]
        session["admin_role"] = "admin"
        session["admin_permissions"] = parse_permissions(row["permissions_json"])
        session["admin_source"] = "database"
        session["admin_account_id"] = row["id"]
        if not session.get("admin_csrf"):
            session["admin_csrf"] = secrets.token_urlsafe(32)

    def log_action(action, details=""):
        try:
            ensure_schema()
            with db_connection() as conn:
                conn.execute(
                    "INSERT INTO admin_logs (id, actor, action, details, created_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        secrets.token_hex(16),
                        session.get("playbed_admin", "admin"),
                        action,
                        (details or "")[:1000],
                        now_iso(),
                    ),
                )
                conn.commit()
        except Exception:
            app.logger.exception("Impossible d'écrire le journal administrateur")

    def verify_csrf():
        supplied = request.form.get("csrf_token", "")
        expected = session.get("admin_csrf", "")
        if not supplied or not expected or not hmac.compare_digest(supplied, expected):
            abort(400)

    def is_super_admin():
        return session.get("admin_role") == "super_admin"

    def admin_can(permission):
        if is_super_admin():
            return True
        return permission in set(session.get("admin_permissions") or [])

    def super_admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("playbed_admin"):
                return redirect(url_for("admin_login", next=request.path))
            if not is_super_admin():
                abort(403)
            return view(*args, **kwargs)
        return wrapped

    def refresh_current_admin():
        username = session.get("playbed_admin")
        if not username:
            return False

        if session.get("admin_source") == "environment" or session.get("admin_role") == "super_admin":
            expected = os.environ.get("PLAYBED_ADMIN_USERNAME", "").strip()
            if expected and hmac.compare_digest(username, expected):
                session["admin_role"] = "super_admin"
                session["admin_permissions"] = list(ADMIN_PERMISSIONS)
                session["admin_source"] = "environment"
                return True
            clear_admin_session()
            return False

        account_id = session.get("admin_account_id")
        row = database_account_by_id(account_id) if account_id else database_account_by_login(username)
        if not row or int(row["active"]) != 1:
            clear_admin_session()
            return False
        set_database_admin_session(row)
        return True

    @app.context_processor
    def inject_multi_admin_helpers():
        return {
            "admin_can": admin_can,
            "admin_is_super": is_super_admin(),
            "admin_role_label": "Super-admin" if is_super_admin() else "Admin",
            "admin_permission_labels": ADMIN_PERMISSIONS,
        }

    @app.before_request
    def enforce_admin_permissions():
        path = request.path or ""
        if not path.startswith("/admin") or path == "/admin/login":
            return None

        if not session.get("playbed_admin"):
            return None

        try:
            if not refresh_current_admin():
                return redirect(url_for("admin_login"))
        except Exception:
            app.logger.exception("Impossible de vérifier le compte administrateur")
            clear_admin_session()
            return redirect(url_for("admin_login"))

        if path in {"/admin", "/admin/", "/admin/logout"}:
            return None

        for prefix, permission in PATH_PERMISSIONS:
            if path.startswith(prefix):
                if permission == "super_admin":
                    if not is_super_admin():
                        abort(403)
                elif not admin_can(permission):
                    abort(403)
                return None

        if not is_super_admin():
            abort(403)
        return None

    def multi_admin_login():
        if session.get("playbed_admin"):
            return redirect(url_for("admin_dashboard"))

        error = None
        if request.method == "POST":
            identifier = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""

            if legacy_credentials_valid(identifier, password):
                set_super_admin_session(identifier)
                log_action("login", "Connexion super-admin")
                next_url = request.args.get("next", "")
                if next_url.startswith("/admin/"):
                    return redirect(next_url)
                return redirect(url_for("admin_dashboard"))

            try:
                row = database_account_by_login(identifier) if identifier else None
            except Exception:
                app.logger.exception("Connexion administrateur base de données indisponible")
                row = None

            if row and int(row["active"]) == 1:
                try:
                    password_ok = check_password_hash(row["password_hash"], password)
                except (ValueError, TypeError):
                    password_ok = False
                if password_ok:
                    set_database_admin_session(row)
                    log_action("login", "Connexion administrateur délégué")
                    next_url = request.args.get("next", "")
                    if next_url.startswith("/admin/"):
                        return redirect(next_url)
                    return redirect(url_for("admin_dashboard"))

            error = "Nom d’utilisateur ou mot de passe incorrect."

        return render_template("admin/login.html", configured=admin_configured(), error=error)

    app.view_functions["admin_login"] = multi_admin_login

    def multi_admin_logout():
        if not session.get("playbed_admin"):
            return redirect(url_for("admin_login"))
        verify_csrf()
        log_action("logout", "Déconnexion de l'interface administrateur")
        clear_admin_session()
        return redirect(url_for("admin_login"))

    app.view_functions["admin_logout"] = multi_admin_logout

    def selected_permissions_from_form():
        return sorted({
            value for value in request.form.getlist("permissions")
            if value in ADMIN_PERMISSIONS
        })

    def valid_username(value):
        return bool(re.fullmatch(r"[A-Za-z0-9._-]{1,8}", value or ""))

    @app.route("/admin/administrateurs")
    @super_admin_required
    def admin_accounts_page():
        ensure_schema()
        with db_connection() as conn:
            accounts = conn.execute(
                """
                SELECT id, username, role, permissions_json, active,
                       created_by, created_at, updated_at
                FROM admin_accounts
                ORDER BY created_at DESC
                """
            ).fetchall()
        normalized = []
        for row in accounts:
            normalized.append({
                "id": row["id"],
                "username": row["username"],
                "role": row["role"],
                "permissions": parse_permissions(row["permissions_json"]),
                "active": bool(int(row["active"])),
                "created_by": row["created_by"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            })
        return render_template(
            "admin/admins.html",
            accounts=normalized,
            permissions=ADMIN_PERMISSIONS,
            primary_username=os.environ.get("PLAYBED_ADMIN_USERNAME", "").strip(),
            message=request.args.get("message", ""),
            error=request.args.get("error", ""),
        )

    @app.route("/admin/administrateurs/ajouter", methods=["POST"])
    @super_admin_required
    def admin_account_add():
        verify_csrf()
        ensure_schema()
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        permissions = selected_permissions_from_form()

        if not valid_username(username):
            return redirect(url_for("admin_accounts_page", error="Nom d’utilisateur invalide : 1 à 8 caractères, lettres/chiffres/._- uniquement."))
        if len(password) < 8:
            return redirect(url_for("admin_accounts_page", error="Le mot de passe doit contenir au moins 8 caractères."))

        primary = os.environ.get("PLAYBED_ADMIN_USERNAME", "").strip()
        if primary and username.lower() == primary.lower():
            return redirect(url_for("admin_accounts_page", error="Ce nom d’utilisateur est réservé au super-admin principal."))

        with db_connection() as conn:
            duplicate = conn.execute(
                """
                SELECT id FROM admin_accounts
                WHERE LOWER(username) = LOWER(?)
                LIMIT 1
                """,
                (username,),
            ).fetchone()
            if duplicate:
                return redirect(url_for("admin_accounts_page", error="Ce nom d’utilisateur est déjà utilisé."))

            account_id = secrets.token_hex(16)
            internal_identifier = f"username-only:{account_id}"
            timestamp = now_iso()
            conn.execute(
                """
                INSERT INTO admin_accounts
                (id, username, email, password_hash, role, permissions_json, active, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'admin', ?, 1, ?, ?, ?)
                """,
                (
                    account_id,
                    username,
                    internal_identifier,
                    generate_password_hash(password),
                    json.dumps(permissions, ensure_ascii=False),
                    session.get("playbed_admin"),
                    timestamp,
                    timestamp,
                ),
            )
            conn.commit()

        log_action("admin_create", f"Compte admin créé : {username}")
        return redirect(url_for("admin_accounts_page", message=f"Administrateur {username} ajouté."))

    @app.route("/admin/administrateurs/modifier", methods=["POST"])
    @super_admin_required
    def admin_account_update():
        verify_csrf()
        ensure_schema()
        account_id = request.form.get("id") or ""
        new_username = (request.form.get("username") or "").strip()
        permissions = selected_permissions_from_form()
        active = 1 if request.form.get("active") == "1" else 0
        new_password = request.form.get("new_password") or ""

        if not valid_username(new_username):
            return redirect(url_for("admin_accounts_page", error="Nom d’utilisateur invalide : 1 à 8 caractères, lettres/chiffres/._- uniquement."))
        if new_password and len(new_password) < 8:
            return redirect(url_for("admin_accounts_page", error="Le nouveau mot de passe doit contenir au moins 8 caractères."))

        primary = os.environ.get("PLAYBED_ADMIN_USERNAME", "").strip()
        if primary and new_username.lower() == primary.lower():
            return redirect(url_for("admin_accounts_page", error="Ce nom d’utilisateur est réservé au super-admin principal."))

        with db_connection() as conn:
            row = conn.execute(
                "SELECT username FROM admin_accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
            if not row:
                abort(404)

            duplicate = conn.execute(
                """
                SELECT id FROM admin_accounts
                WHERE LOWER(username) = LOWER(?) AND id <> ?
                LIMIT 1
                """,
                (new_username, account_id),
            ).fetchone()
            if duplicate:
                return redirect(url_for("admin_accounts_page", error="Ce nom d’utilisateur est déjà utilisé."))

            old_username = row["username"]
            if new_password:
                conn.execute(
                    """
                    UPDATE admin_accounts
                    SET username = ?, permissions_json = ?, active = ?, password_hash = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        new_username,
                        json.dumps(permissions, ensure_ascii=False),
                        active,
                        generate_password_hash(new_password),
                        now_iso(),
                        account_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE admin_accounts
                    SET username = ?, permissions_json = ?, active = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        new_username,
                        json.dumps(permissions, ensure_ascii=False),
                        active,
                        now_iso(),
                        account_id,
                    ),
                )
            conn.commit()

        if old_username != new_username:
            log_action("admin_update", f"Compte admin renommé : {old_username} -> {new_username}")
        else:
            log_action("admin_update", f"Compte admin modifié : {new_username}")
        return redirect(url_for("admin_accounts_page", message=f"Administrateur {new_username} mis à jour."))

    @app.route("/admin/administrateurs/supprimer", methods=["POST"])
    @super_admin_required
    def admin_account_delete():
        verify_csrf()
        ensure_schema()
        account_id = request.form.get("id") or ""
        with db_connection() as conn:
            row = conn.execute(
                "SELECT username FROM admin_accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
            if not row:
                abort(404)
            conn.execute("DELETE FROM admin_accounts WHERE id = ?", (account_id,))
            conn.commit()
        log_action("admin_delete", f"Compte admin supprimé : {row['username']}")
        return redirect(url_for("admin_accounts_page", message=f"Administrateur {row['username']} supprimé."))
