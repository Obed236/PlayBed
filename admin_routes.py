import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import abort, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash


def register_admin_routes(app, games, db_connection, current_pseudo, core_module=None):
    """Register PlayBed's private administration interface."""

    def now_iso():
        return datetime.now(timezone.utc).isoformat()

    def ensure_schema():
        with db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id TEXT PRIMARY KEY,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_blocked_pseudos (
                    pseudo TEXT PRIMARY KEY,
                    reason TEXT,
                    created_at TEXT NOT NULL
                )
            """)
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
                CREATE TABLE IF NOT EXISTS admin_questions (
                    id TEXT PRIMARY KEY,
                    game TEXT NOT NULL,
                    question TEXT NOT NULL,
                    options_json TEXT,
                    answer TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def get_setting(key, default=""):
        ensure_schema()
        with db_connection() as conn:
            row = conn.execute(
                "SELECT value FROM admin_settings WHERE key = ?",
                (key,),
            ).fetchone()
        return row["value"] if row else default

    def set_setting(key, value):
        ensure_schema()
        with db_connection() as conn:
            existing = conn.execute(
                "SELECT key FROM admin_settings WHERE key = ?",
                (key,),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE admin_settings SET value = ?, updated_at = ? WHERE key = ?",
                    (value, now_iso(), key),
                )
            else:
                conn.execute(
                    "INSERT INTO admin_settings (key, value, updated_at) VALUES (?, ?, ?)",
                    (key, value, now_iso()),
                )
            conn.commit()

    def log_action(action, details=""):
        ensure_schema()
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

    def admin_configured():
        username = os.environ.get("PLAYBED_ADMIN_USERNAME", "").strip()
        password_hash = os.environ.get("PLAYBED_ADMIN_PASSWORD_HASH", "").strip()
        password = os.environ.get("PLAYBED_ADMIN_PASSWORD", "")
        return bool(username and (password_hash or password))

    def credentials_valid(username, password):
        expected_username = os.environ.get("PLAYBED_ADMIN_USERNAME", "").strip()
        if not expected_username:
            return False
        if not hmac.compare_digest(username, expected_username):
            return False

        password_hash = os.environ.get("PLAYBED_ADMIN_PASSWORD_HASH", "").strip()
        if password_hash:
            try:
                return check_password_hash(password_hash, password)
            except (ValueError, TypeError):
                return False

        expected_password = os.environ.get("PLAYBED_ADMIN_PASSWORD", "")
        return bool(expected_password) and hmac.compare_digest(password, expected_password)

    def csrf_token():
        token = session.get("admin_csrf")
        if not token:
            token = secrets.token_urlsafe(32)
            session["admin_csrf"] = token
        return token

    def verify_csrf():
        supplied = request.form.get("csrf_token", "")
        expected = session.get("admin_csrf", "")
        if not supplied or not expected or not hmac.compare_digest(supplied, expected):
            abort(400)

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("playbed_admin"):
                return redirect(url_for("admin_login", next=request.path))
            return view(*args, **kwargs)
        return wrapped

    def game_enabled(slug):
        value = get_setting(f"game_enabled:{slug}", "1")
        return value != "0"

    def load_custom_questions(game):
        ensure_schema()
        with db_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, game, question, options_json, answer, active, created_at, updated_at
                FROM admin_questions
                WHERE game = ?
                ORDER BY created_at DESC
                """,
                (game,),
            ).fetchall()
        return rows

    if core_module is not None:
        original_vof_loader = core_module.load_vof_questions
        original_quiz_loader = core_module.load_quiz_questions

        def load_vof_with_admin():
            base = list(original_vof_loader())
            try:
                for row in load_custom_questions("vof"):
                    if int(row["active"]) == 1:
                        base.append({"question": row["question"], "answer": row["answer"]})
            except Exception:
                app.logger.exception("Impossible de charger les questions Vrai/Faux administrateur")
            return base

        def load_quiz_with_admin():
            base = list(original_quiz_loader())
            try:
                for row in load_custom_questions("quiz"):
                    if int(row["active"]) != 1:
                        continue
                    options = json.loads(row["options_json"] or "[]")
                    if isinstance(options, list) and row["answer"] in options:
                        base.append({
                            "question": row["question"],
                            "options": options,
                            "answer": row["answer"],
                        })
            except Exception:
                app.logger.exception("Impossible de charger les questions Quiz administrateur")
            return base

        core_module.load_vof_questions = load_vof_with_admin
        core_module.load_quiz_questions = load_quiz_with_admin

    @app.context_processor
    def inject_admin_helpers():
        return {
            "admin_session": session.get("playbed_admin"),
            "admin_csrf_token": csrf_token,
        }

    @app.before_request
    def enforce_admin_controls():
        if request.path.startswith("/admin"):
            return None

        if request.endpoint in {
            "static", "health", "robots_txt", "ads_txt", "sitemap_xml",
            "pwa_manifest", "pwa_service_worker",
        }:
            return None

        try:
            ensure_schema()

            if get_setting("maintenance_mode", "0") == "1":
                return render_template(
                    "maintenance.html",
                    message=get_setting(
                        "maintenance_message",
                        "PlayBed est momentanément en maintenance. Reviens dans quelques instants.",
                    ),
                ), 503

            pseudo = current_pseudo()
            if pseudo:
                with db_connection() as conn:
                    blocked = conn.execute(
                        "SELECT pseudo FROM admin_blocked_pseudos WHERE LOWER(pseudo) = LOWER(?)",
                        (pseudo,),
                    ).fetchone()
                if blocked:
                    session.pop("pseudo", None)
                    session.pop("current_game", None)
                    return redirect(url_for("home", pseudo_blocked=1))

            slug = None
            if request.view_args:
                slug = request.view_args.get("game")
            if not slug:
                arcade_paths = {
                    "/arcade/calcul": "calcul",
                    "/arcade/mot-melange": "melange",
                    "/arcade/suite-logique": "suite",
                    "/arcade/pair-impair": "pair",
                    "/arcade/chrono-10": "chrono",
                }
                slug = arcade_paths.get(request.path)
            if not slug and (
                request.path.startswith("/action-verite")
                or request.path.startswith("/jeux/action-verite")
            ):
                slug = "action-verite"

            if slug in games and not game_enabled(slug):
                return render_template(
                    "game_disabled.html",
                    meta=games[slug],
                    pseudo=current_pseudo(),
                ), 503
        except Exception:
            app.logger.exception("Contrôles administrateur temporairement indisponibles")
        return None

    @app.after_request
    def protect_admin_responses(response):
        if request.path.startswith("/admin"):
            response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
            response.headers["Cache-Control"] = "no-store, max-age=0"
        return response

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if session.get("playbed_admin"):
            return redirect(url_for("admin_dashboard"))

        error = None
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""

            if not admin_configured():
                error = (
                    "L’accès administrateur n’est pas encore configuré sur Render. "
                    "Ajoute PLAYBED_ADMIN_USERNAME et PLAYBED_ADMIN_PASSWORD_HASH "
                    "(ou PLAYBED_ADMIN_PASSWORD)."
                )
            elif credentials_valid(username, password):
                session["playbed_admin"] = username
                session["admin_csrf"] = secrets.token_urlsafe(32)
                log_action("login", "Connexion à l’interface administrateur")
                next_url = request.args.get("next", "")
                if next_url.startswith("/admin/"):
                    return redirect(next_url)
                return redirect(url_for("admin_dashboard"))
            else:
                error = "Identifiant ou mot de passe incorrect."

        return render_template("admin/login.html", configured=admin_configured(), error=error)

    @app.route("/admin/logout", methods=["POST"])
    @admin_required
    def admin_logout():
        verify_csrf()
        try:
            log_action("logout", "Déconnexion de l’interface administrateur")
        finally:
            session.pop("playbed_admin", None)
            session.pop("admin_csrf", None)
        return redirect(url_for("admin_login"))

    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        ensure_schema()
        since_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        with db_connection() as conn:
            total_scores = conn.execute("SELECT COUNT(*) AS n FROM scores").fetchone()["n"]
            players = conn.execute("SELECT COUNT(DISTINCT pseudo) AS n FROM scores").fetchone()["n"]
            scores_24h = conn.execute(
                "SELECT COUNT(*) AS n FROM scores WHERE created_at >= ?", (since_24h,)
            ).fetchone()["n"]
            blocked = conn.execute("SELECT COUNT(*) AS n FROM admin_blocked_pseudos").fetchone()["n"]
            recent_scores = conn.execute(
                "SELECT pseudo, game, points, created_at FROM scores ORDER BY created_at DESC LIMIT 10"
            ).fetchall()
            game_stats = conn.execute(
                "SELECT game, COUNT(*) AS plays, SUM(points) AS points FROM scores GROUP BY game ORDER BY plays DESC"
            ).fetchall()
            recent_logs = conn.execute(
                "SELECT actor, action, details, created_at FROM admin_logs ORDER BY created_at DESC LIMIT 8"
            ).fetchall()

        return render_template(
            "admin/dashboard.html", total_scores=total_scores, players=players,
            scores_24h=scores_24h, blocked=blocked, games=games,
            game_stats=game_stats, recent_scores=recent_scores, recent_logs=recent_logs,
        )

    @app.route("/admin/utilisateurs")
    @admin_required
    def admin_users():
        ensure_schema()
        search = (request.args.get("q") or "").strip()
        with db_connection() as conn:
            if search:
                users = conn.execute(
                    """
                    SELECT s.pseudo, COUNT(*) AS games_played, SUM(s.points) AS total_points,
                           MAX(s.created_at) AS last_seen,
                           CASE WHEN b.pseudo IS NULL THEN 0 ELSE 1 END AS blocked
                    FROM scores s
                    LEFT JOIN admin_blocked_pseudos b ON LOWER(b.pseudo) = LOWER(s.pseudo)
                    WHERE LOWER(s.pseudo) LIKE LOWER(?)
                    GROUP BY s.pseudo, b.pseudo
                    ORDER BY total_points DESC LIMIT 200
                    """, (f"%{search}%",)
                ).fetchall()
            else:
                users = conn.execute(
                    """
                    SELECT s.pseudo, COUNT(*) AS games_played, SUM(s.points) AS total_points,
                           MAX(s.created_at) AS last_seen,
                           CASE WHEN b.pseudo IS NULL THEN 0 ELSE 1 END AS blocked
                    FROM scores s
                    LEFT JOIN admin_blocked_pseudos b ON LOWER(b.pseudo) = LOWER(s.pseudo)
                    GROUP BY s.pseudo, b.pseudo
                    ORDER BY total_points DESC LIMIT 200
                    """
                ).fetchall()
        return render_template("admin/users.html", users=users, search=search)

    @app.route("/admin/utilisateurs/blocage", methods=["POST"])
    @admin_required
    def admin_user_block():
        verify_csrf()
        ensure_schema()
        pseudo = (request.form.get("pseudo") or "").strip()
        action = request.form.get("action")
        reason = (request.form.get("reason") or "").strip()[:300]
        if not pseudo:
            abort(400)

        with db_connection() as conn:
            if action == "block":
                existing = conn.execute(
                    "SELECT pseudo FROM admin_blocked_pseudos WHERE LOWER(pseudo) = LOWER(?)", (pseudo,)
                ).fetchone()
                if not existing:
                    conn.execute(
                        "INSERT INTO admin_blocked_pseudos (pseudo, reason, created_at) VALUES (?, ?, ?)",
                        (pseudo, reason, now_iso()),
                    )
                else:
                    conn.execute(
                        "UPDATE admin_blocked_pseudos SET reason = ?, created_at = ? WHERE LOWER(pseudo) = LOWER(?)",
                        (reason, now_iso(), pseudo),
                    )
                log_text = f"Pseudo bloqué : {pseudo}"
            elif action == "unblock":
                conn.execute("DELETE FROM admin_blocked_pseudos WHERE LOWER(pseudo) = LOWER(?)", (pseudo,))
                log_text = f"Pseudo débloqué : {pseudo}"
            else:
                abort(400)
            conn.commit()
        log_action("user_block", log_text)
        return redirect(url_for("admin_users", q=pseudo))

    @app.route("/admin/utilisateurs/scores/supprimer", methods=["POST"])
    @admin_required
    def admin_user_delete_scores():
        verify_csrf()
        pseudo = (request.form.get("pseudo") or "").strip()
        if not pseudo:
            abort(400)
        with db_connection() as conn:
            conn.execute("DELETE FROM scores WHERE LOWER(pseudo) = LOWER(?)", (pseudo,))
            conn.commit()
        log_action("delete_user_scores", f"Scores supprimés pour {pseudo}")
        return redirect(url_for("admin_users", q=pseudo))

    @app.route("/admin/scores")
    @admin_required
    def admin_scores():
        game = (request.args.get("game") or "").strip()
        pseudo = (request.args.get("pseudo") or "").strip()
        query = "SELECT pseudo, game, points, created_at FROM scores"
        clauses = []
        params = []
        if game:
            clauses.append("game = ?")
            params.append(game)
        if pseudo:
            clauses.append("LOWER(pseudo) LIKE LOWER(?)")
            params.append(f"%{pseudo}%")
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(200)
        with db_connection() as conn:
            scores = conn.execute(query, tuple(params)).fetchall()
        return render_template(
            "admin/scores.html", scores=scores, games=games,
            selected_game=game, pseudo_filter=pseudo,
        )

    @app.route("/admin/scores/supprimer", methods=["POST"])
    @admin_required
    def admin_score_delete():
        verify_csrf()
        pseudo = request.form.get("pseudo") or ""
        game = request.form.get("game") or ""
        created_at = request.form.get("created_at") or ""
        try:
            points = int(request.form.get("points", ""))
        except ValueError:
            abort(400)
        with db_connection() as conn:
            conn.execute(
                "DELETE FROM scores WHERE pseudo = ? AND game = ? AND points = ? AND created_at = ?",
                (pseudo, game, points, created_at),
            )
            conn.commit()
        log_action("delete_score", f"Score supprimé : {pseudo} / {game} / {points}")
        return redirect(url_for("admin_scores"))

    @app.route("/admin/jeux")
    @admin_required
    def admin_games():
        with db_connection() as conn:
            rows = conn.execute(
                """
                SELECT game, COUNT(*) AS plays, SUM(points) AS total_points,
                       MAX(points) AS best_score, MAX(created_at) AS last_played
                FROM scores GROUP BY game
                """
            ).fetchall()
        stats = {row["game"]: row for row in rows}
        statuses = {slug: game_enabled(slug) for slug in games}
        return render_template("admin/games.html", games=games, stats=stats, statuses=statuses)

    @app.route("/admin/jeux/statut", methods=["POST"])
    @admin_required
    def admin_game_status():
        verify_csrf()
        slug = request.form.get("game") or ""
        if slug not in games:
            abort(400)
        enabled = request.form.get("enabled") == "1"
        set_setting(f"game_enabled:{slug}", "1" if enabled else "0")
        log_action("game_status", f"{games[slug]['name']} {'activé' if enabled else 'désactivé'}")
        return redirect(url_for("admin_games"))

    @app.route("/admin/questions")
    @admin_required
    def admin_questions():
        vof = load_custom_questions("vof")
        quiz = load_custom_questions("quiz")
        base_vof_count = 0
        base_quiz_count = 0
        if core_module:
            base_vof_count = len(core_module.load_vof_questions()) - sum(1 for row in vof if int(row["active"]) == 1)
            base_quiz_count = len(core_module.load_quiz_questions()) - sum(1 for row in quiz if int(row["active"]) == 1)
        return render_template(
            "admin/questions.html", vof_questions=vof, quiz_questions=quiz,
            base_vof_count=max(0, base_vof_count), base_quiz_count=max(0, base_quiz_count),
        )

    @app.route("/admin/questions/ajouter", methods=["POST"])
    @admin_required
    def admin_question_add():
        verify_csrf()
        ensure_schema()
        game = request.form.get("game") or ""
        question = (request.form.get("question") or "").strip()
        answer = (request.form.get("answer") or "").strip()
        options_json = None
        if game not in {"vof", "quiz"} or len(question) < 5:
            abort(400)
        if game == "vof":
            answer = answer.lower()
            if answer not in {"vrai", "faux"}:
                abort(400)
        else:
            options = [item.strip() for item in (request.form.get("options") or "").split("|") if item.strip()]
            if len(options) < 2 or answer not in options:
                abort(400)
            options_json = json.dumps(options, ensure_ascii=False)
        timestamp = now_iso()
        with db_connection() as conn:
            conn.execute(
                """
                INSERT INTO admin_questions
                (id, game, question, options_json, answer, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (secrets.token_hex(16), game, question, options_json, answer, 1, timestamp, timestamp),
            )
            conn.commit()
        log_action("question_add", f"Question ajoutée à {game}: {question[:120]}")
        return redirect(url_for("admin_questions"))

    @app.route("/admin/questions/statut", methods=["POST"])
    @admin_required
    def admin_question_status():
        verify_csrf()
        question_id = request.form.get("id") or ""
        active = 1 if request.form.get("active") == "1" else 0
        with db_connection() as conn:
            conn.execute(
                "UPDATE admin_questions SET active = ?, updated_at = ? WHERE id = ?",
                (active, now_iso(), question_id),
            )
            conn.commit()
        log_action("question_status", f"Question {question_id} {'activée' if active else 'désactivée'}")
        return redirect(url_for("admin_questions"))

    @app.route("/admin/questions/supprimer", methods=["POST"])
    @admin_required
    def admin_question_delete():
        verify_csrf()
        question_id = request.form.get("id") or ""
        row = None
        with db_connection() as conn:
            row = conn.execute("SELECT question FROM admin_questions WHERE id = ?", (question_id,)).fetchone()
            if row:
                conn.execute("DELETE FROM admin_questions WHERE id = ?", (question_id,))
                conn.commit()
        log_action("question_delete", f"Question supprimée : {(row['question'] if row else question_id)[:120]}")
        return redirect(url_for("admin_questions"))

    @app.route("/admin/signalements")
    @admin_required
    def admin_reports():
        ensure_schema()
        with db_connection() as conn:
            reports = conn.execute(
                """
                SELECT id, reporter_pseudo, target_type, target_value, reason,
                       status, created_at, resolved_at
                FROM admin_reports ORDER BY created_at DESC LIMIT 200
                """
            ).fetchall()
        return render_template("admin/reports.html", reports=reports)

    @app.route("/admin/signalements/statut", methods=["POST"])
    @admin_required
    def admin_report_status():
        verify_csrf()
        report_id = request.form.get("id") or ""
        status = request.form.get("status") or ""
        if status not in {"open", "resolved", "dismissed"}:
            abort(400)
        resolved_at = now_iso() if status != "open" else None
        with db_connection() as conn:
            conn.execute(
                "UPDATE admin_reports SET status = ?, resolved_at = ? WHERE id = ?",
                (status, resolved_at, report_id),
            )
            conn.commit()
        log_action("report_status", f"Signalement {report_id} -> {status}")
        return redirect(url_for("admin_reports"))

    @app.route("/admin/parametres", methods=["GET", "POST"])
    @admin_required
    def admin_settings():
        if request.method == "POST":
            verify_csrf()
            maintenance = "1" if request.form.get("maintenance_mode") == "1" else "0"
            message = (request.form.get("maintenance_message") or "").strip()[:500]
            set_setting("maintenance_mode", maintenance)
            set_setting("maintenance_message", message)
            log_action("settings_update", f"Maintenance {'activée' if maintenance == '1' else 'désactivée'}")
            return redirect(url_for("admin_settings"))
        return render_template(
            "admin/settings.html",
            maintenance_mode=get_setting("maintenance_mode", "0") == "1",
            maintenance_message=get_setting(
                "maintenance_message",
                "PlayBed est momentanément en maintenance. Reviens dans quelques instants.",
            ),
            configured=admin_configured(),
            password_hash_configured=bool(os.environ.get("PLAYBED_ADMIN_PASSWORD_HASH", "").strip()),
        )
