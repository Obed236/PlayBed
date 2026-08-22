import json
import secrets
import time
from datetime import datetime, timezone
from functools import wraps

from flask import abort, redirect, render_template, request, session, url_for


def register_admin_complete(app, games, db_connection, current_pseudo, core_module):
    """Complete the PlayBed back-office with persistent management tools."""

    base_game_meta = {slug: dict(meta) for slug, meta in games.items()}
    game_cache = {"loaded": 0.0}
    announcement_cache = {"loaded": 0.0, "rows": []}

    def now_iso():
        return datetime.now(timezone.utc).isoformat()

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("playbed_admin"):
                return redirect(url_for("admin_login", next=request.full_path or request.path))
            return view(*args, **kwargs)
        return wrapped

    def verify_admin_csrf():
        supplied = request.form.get("csrf_token", "")
        expected = session.get("admin_csrf", "")
        if not supplied or not expected or not secrets.compare_digest(supplied, expected):
            abort(400)

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
                CREATE TABLE IF NOT EXISTS admin_question_overrides (
                    source_key TEXT PRIMARY KEY,
                    game TEXT NOT NULL,
                    source_index INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    options_json TEXT,
                    answer TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_game_overrides (
                    slug TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    emoji TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_announcements (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    starts_at TEXT,
                    ends_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_player_notes (
                    pseudo TEXT PRIMARY KEY,
                    note TEXT NOT NULL,
                    updated_at TEXT NOT NULL
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
            conn.commit()

    def log_action(action, details=""):
        ensure_schema()
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO admin_logs (id, actor, action, details, created_at) VALUES (?, ?, ?, ?, ?)",
                (secrets.token_hex(16), session.get("playbed_admin", "admin"), action, details[:1000], now_iso()),
            )
            conn.commit()

    def raw_questions(game):
        filename = "vof.json" if game == "vof" else "quiz.json"
        path = core_module.DATA_DIR / filename
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else []

    def question_overrides(game):
        ensure_schema()
        with db_connection() as conn:
            rows = conn.execute(
                "SELECT source_key, source_index, question, options_json, answer, active, updated_at "
                "FROM admin_question_overrides WHERE game = ?",
                (game,),
            ).fetchall()
        return {int(row["source_index"]): row for row in rows}

    def custom_questions(game, include_inactive=False):
        ensure_schema()
        sql = (
            "SELECT id, game, question, options_json, answer, active, created_at, updated_at "
            "FROM admin_questions WHERE game = ?"
        )
        if not include_inactive:
            sql += " AND active = 1"
        sql += " ORDER BY created_at ASC"
        with db_connection() as conn:
            return conn.execute(sql, (game,)).fetchall()

    def build_questions(game):
        base = raw_questions(game)
        try:
            overrides = question_overrides(game)
            custom = custom_questions(game)
        except Exception:
            app.logger.exception("Chargement des questions administrables impossible")
            return base

        result = []
        for index, item in enumerate(base):
            override = overrides.get(index)
            if override and int(override["active"]) != 1:
                continue
            question = override["question"] if override else item.get("question", "")
            answer = override["answer"] if override else item.get("answer", "")
            if game == "quiz":
                if override:
                    try:
                        options = json.loads(override["options_json"] or "[]")
                    except (TypeError, ValueError, json.JSONDecodeError):
                        options = item.get("options", [])
                else:
                    options = item.get("options", [])
                if answer in options:
                    result.append({"question": question, "options": options, "answer": answer})
            else:
                result.append({"question": question, "answer": answer})

        for row in custom:
            if game == "quiz":
                try:
                    options = json.loads(row["options_json"] or "[]")
                except (TypeError, ValueError, json.JSONDecodeError):
                    continue
                if row["answer"] not in options:
                    continue
                result.append({"question": row["question"], "options": options, "answer": row["answer"]})
            else:
                result.append({"question": row["question"], "answer": row["answer"]})
        return result

    # Replace the earlier additive loaders with one source of truth that supports
    # editing/disabling the original JSON questions through PostgreSQL overrides.
    core_module.load_vof_questions = lambda: build_questions("vof")
    core_module.load_quiz_questions = lambda: build_questions("quiz")

    def refresh_game_overrides(force=False):
        if not force and time.monotonic() - game_cache["loaded"] < 30:
            return
        try:
            ensure_schema()
            with db_connection() as conn:
                rows = conn.execute(
                    "SELECT slug, name, description, emoji, tag FROM admin_game_overrides"
                ).fetchall()
            for slug, original in base_game_meta.items():
                games[slug].update(original)
            for row in rows:
                slug = row["slug"]
                if slug in games:
                    games[slug].update({
                        "name": row["name"],
                        "description": row["description"],
                        "emoji": row["emoji"],
                        "tag": row["tag"],
                    })
            game_cache["loaded"] = time.monotonic()
        except Exception:
            app.logger.exception("Impossible de charger les personnalisations de jeux")

    def current_announcements(force=False):
        if not force and time.monotonic() - announcement_cache["loaded"] < 30:
            return announcement_cache["rows"]
        try:
            ensure_schema()
            with db_connection() as conn:
                rows = conn.execute(
                    "SELECT id, title, message, kind, active, starts_at, ends_at, created_at, updated_at "
                    "FROM admin_announcements WHERE active = 1 ORDER BY created_at DESC"
                ).fetchall()
            now = datetime.now(timezone.utc)
            active_rows = []
            for row in rows:
                try:
                    starts = datetime.fromisoformat(row["starts_at"]) if row["starts_at"] else None
                    ends = datetime.fromisoformat(row["ends_at"]) if row["ends_at"] else None
                except (TypeError, ValueError):
                    starts = ends = None
                if starts and starts.tzinfo is None:
                    starts = starts.replace(tzinfo=timezone.utc)
                if ends and ends.tzinfo is None:
                    ends = ends.replace(tzinfo=timezone.utc)
                if starts and starts > now:
                    continue
                if ends and ends < now:
                    continue
                active_rows.append(row)
            announcement_cache["rows"] = active_rows[:3]
            announcement_cache["loaded"] = time.monotonic()
        except Exception:
            app.logger.exception("Impossible de charger les annonces")
            announcement_cache["rows"] = []
        return announcement_cache["rows"]

    @app.before_request
    def refresh_admin_managed_content():
        if request.endpoint not in {"static", "health", "robots_txt", "ads_txt", "sitemap_xml", "pwa_manifest", "pwa_service_worker"}:
            refresh_game_overrides()

    @app.context_processor
    def inject_managed_content():
        data = {"site_announcements": []}
        if not request.path.startswith("/admin"):
            data["site_announcements"] = current_announcements()
        if request.endpoint == "growth_public_profile":
            token = session.get("public_report_csrf")
            if not token:
                token = secrets.token_urlsafe(24)
                session["public_report_csrf"] = token
            data["public_report_csrf"] = token
        else:
            data["public_report_csrf"] = ""
        return data

    def normalize_question(game, question, answer, options_text):
        question = (question or "").strip()
        answer = (answer or "").strip()
        if game not in {"vof", "quiz"} or len(question) < 5 or len(question) > 500:
            abort(400)
        if game == "vof":
            answer = answer.lower()
            if answer not in {"vrai", "faux"}:
                abort(400)
            return question, answer, None
        options = [part.strip() for part in (options_text or "").split("|") if part.strip()]
        if len(options) < 2 or len(options) > 8 or answer not in options:
            abort(400)
        return question, answer, json.dumps(options, ensure_ascii=False)

    def complete_questions_view():
        ensure_schema()
        sections = {}
        for game in ("vof", "quiz"):
            base = raw_questions(game)
            overrides = question_overrides(game)
            base_rows = []
            for index, item in enumerate(base):
                override = overrides.get(index)
                if override:
                    try:
                        options = json.loads(override["options_json"] or "[]") if game == "quiz" else []
                    except (TypeError, ValueError, json.JSONDecodeError):
                        options = item.get("options", [])
                    base_rows.append({
                        "source": "base", "id": str(index), "game": game,
                        "question": override["question"], "answer": override["answer"],
                        "options": options, "active": bool(int(override["active"])), "modified": True,
                    })
                else:
                    base_rows.append({
                        "source": "base", "id": str(index), "game": game,
                        "question": item.get("question", ""), "answer": item.get("answer", ""),
                        "options": item.get("options", []), "active": True, "modified": False,
                    })
            custom_rows = []
            for row in custom_questions(game, include_inactive=True):
                try:
                    options = json.loads(row["options_json"] or "[]") if game == "quiz" else []
                except (TypeError, ValueError, json.JSONDecodeError):
                    options = []
                custom_rows.append({
                    "source": "custom", "id": row["id"], "game": game,
                    "question": row["question"], "answer": row["answer"], "options": options,
                    "active": bool(int(row["active"])), "modified": True,
                })
            sections[game] = {"base": base_rows, "custom": custom_rows}
        return render_template("admin/questions.html", sections=sections)

    # Keep the established /admin/questions URL but replace its limited view.
    app.view_functions["admin_questions"] = admin_required(complete_questions_view)

    @app.route("/admin/questions/edition", methods=["GET", "POST"])
    @admin_required
    def admin_question_edit():
        ensure_schema()
        source = request.values.get("source", "")
        game = request.values.get("game", "")
        item_id = request.values.get("id", "")
        if game not in {"vof", "quiz"} or source not in {"base", "custom"}:
            abort(400)

        if source == "base":
            try:
                index = int(item_id)
                original = raw_questions(game)[index]
            except (ValueError, IndexError):
                abort(404)
            override = question_overrides(game).get(index)
            item = {
                "source": "base", "id": str(index), "game": game,
                "question": override["question"] if override else original.get("question", ""),
                "answer": override["answer"] if override else original.get("answer", ""),
                "active": bool(int(override["active"])) if override else True,
                "options": [],
                "modified": bool(override),
            }
            if game == "quiz":
                if override:
                    try:
                        item["options"] = json.loads(override["options_json"] or "[]")
                    except (TypeError, ValueError, json.JSONDecodeError):
                        item["options"] = original.get("options", [])
                else:
                    item["options"] = original.get("options", [])
        else:
            with db_connection() as conn:
                row = conn.execute(
                    "SELECT id, question, options_json, answer, active FROM admin_questions WHERE id = ? AND game = ?",
                    (item_id, game),
                ).fetchone()
            if not row:
                abort(404)
            try:
                options = json.loads(row["options_json"] or "[]") if game == "quiz" else []
            except (TypeError, ValueError, json.JSONDecodeError):
                options = []
            item = {
                "source": "custom", "id": row["id"], "game": game,
                "question": row["question"], "answer": row["answer"],
                "active": bool(int(row["active"])), "options": options, "modified": True,
            }

        if request.method == "POST":
            verify_admin_csrf()
            question, answer, options_json = normalize_question(
                game, request.form.get("question"), request.form.get("answer"), request.form.get("options")
            )
            active = 1 if request.form.get("active") == "1" else 0
            timestamp = now_iso()
            with db_connection() as conn:
                if source == "base":
                    source_key = f"{game}:{item['id']}"
                    exists = conn.execute(
                        "SELECT source_key FROM admin_question_overrides WHERE source_key = ?", (source_key,)
                    ).fetchone()
                    if exists:
                        conn.execute(
                            "UPDATE admin_question_overrides SET question = ?, options_json = ?, answer = ?, active = ?, updated_at = ? WHERE source_key = ?",
                            (question, options_json, answer, active, timestamp, source_key),
                        )
                    else:
                        conn.execute(
                            "INSERT INTO admin_question_overrides (source_key, game, source_index, question, options_json, answer, active, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (source_key, game, int(item["id"]), question, options_json, answer, active, timestamp),
                        )
                else:
                    conn.execute(
                        "UPDATE admin_questions SET question = ?, options_json = ?, answer = ?, active = ?, updated_at = ? WHERE id = ?",
                        (question, options_json, answer, active, timestamp, item["id"]),
                    )
                conn.commit()
            log_action("question_edit", f"{game} / {source} / {item['id']} modifiée")
            return redirect(url_for("admin_questions"))

        return render_template("admin/question_edit.html", item=item)

    @app.route("/admin/questions/base/statut", methods=["POST"])
    @admin_required
    def admin_base_question_status():
        verify_admin_csrf()
        game = request.form.get("game", "")
        try:
            index = int(request.form.get("id", ""))
            original = raw_questions(game)[index]
        except (ValueError, IndexError, KeyError):
            abort(400)
        if game not in {"vof", "quiz"}:
            abort(400)
        active = 1 if request.form.get("active") == "1" else 0
        overrides = question_overrides(game)
        override = overrides.get(index)
        question = override["question"] if override else original.get("question", "")
        answer = override["answer"] if override else original.get("answer", "")
        if game == "quiz":
            options_json = override["options_json"] if override else json.dumps(original.get("options", []), ensure_ascii=False)
        else:
            options_json = None
        source_key = f"{game}:{index}"
        with db_connection() as conn:
            exists = conn.execute("SELECT source_key FROM admin_question_overrides WHERE source_key = ?", (source_key,)).fetchone()
            if exists:
                conn.execute(
                    "UPDATE admin_question_overrides SET active = ?, updated_at = ? WHERE source_key = ?",
                    (active, now_iso(), source_key),
                )
            else:
                conn.execute(
                    "INSERT INTO admin_question_overrides (source_key, game, source_index, question, options_json, answer, active, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (source_key, game, index, question, options_json, answer, active, now_iso()),
                )
            conn.commit()
        log_action("question_status", f"Question de base {source_key} {'activée' if active else 'désactivée'}")
        return redirect(url_for("admin_questions"))

    @app.route("/admin/questions/base/reinitialiser", methods=["POST"])
    @admin_required
    def admin_base_question_reset():
        verify_admin_csrf()
        game = request.form.get("game", "")
        item_id = request.form.get("id", "")
        if game not in {"vof", "quiz"}:
            abort(400)
        source_key = f"{game}:{item_id}"
        with db_connection() as conn:
            conn.execute("DELETE FROM admin_question_overrides WHERE source_key = ?", (source_key,))
            conn.commit()
        log_action("question_reset", f"Question {source_key} réinitialisée depuis JSON")
        return redirect(url_for("admin_questions"))

    @app.route("/admin/utilisateurs/detail")
    @admin_required
    def admin_user_detail():
        ensure_schema()
        requested = (request.args.get("pseudo") or "").strip()
        if not requested:
            abort(400)
        with db_connection() as conn:
            canonical = conn.execute(
                "SELECT pseudo FROM scores WHERE LOWER(pseudo) = LOWER(?) LIMIT 1", (requested,)
            ).fetchone()
            if not canonical:
                abort(404)
            pseudo = canonical["pseudo"]
            stats = conn.execute(
                "SELECT COUNT(*) AS games_played, COALESCE(SUM(points),0) AS total_points, COALESCE(MAX(points),0) AS best_score, "
                "COUNT(DISTINCT game) AS distinct_games, MIN(created_at) AS first_seen, MAX(created_at) AS last_seen "
                "FROM scores WHERE pseudo = ?",
                (pseudo,),
            ).fetchone()
            by_game = conn.execute(
                "SELECT game, COUNT(*) AS plays, SUM(points) AS total_points, MAX(points) AS best_score, MAX(created_at) AS last_played "
                "FROM scores WHERE pseudo = ? GROUP BY game ORDER BY total_points DESC",
                (pseudo,),
            ).fetchall()
            recent = conn.execute(
                "SELECT game, points, created_at FROM scores WHERE pseudo = ? ORDER BY created_at DESC LIMIT 50",
                (pseudo,),
            ).fetchall()
            ranking = conn.execute(
                "SELECT pseudo, SUM(points) AS total_points FROM scores GROUP BY pseudo ORDER BY total_points DESC, pseudo ASC"
            ).fetchall()
            blocked = conn.execute(
                "SELECT reason, created_at FROM admin_blocked_pseudos WHERE LOWER(pseudo) = LOWER(?)", (pseudo,)
            ).fetchone()
            note = conn.execute(
                "SELECT note, updated_at FROM admin_player_notes WHERE LOWER(pseudo) = LOWER(?)", (pseudo,)
            ).fetchone()
        rank = next((i + 1 for i, row in enumerate(ranking) if row["pseudo"] == pseudo), None)
        return render_template(
            "admin/user_detail.html", viewed_pseudo=pseudo, stats=stats, by_game=by_game,
            recent=recent, rank=rank, blocked=blocked, note=note, games=games,
        )

    @app.route("/admin/utilisateurs/note", methods=["POST"])
    @admin_required
    def admin_user_note():
        verify_admin_csrf()
        ensure_schema()
        pseudo = (request.form.get("pseudo") or "").strip()
        note = (request.form.get("note") or "").strip()[:2000]
        if not pseudo:
            abort(400)
        with db_connection() as conn:
            existing = conn.execute(
                "SELECT pseudo FROM admin_player_notes WHERE LOWER(pseudo) = LOWER(?)", (pseudo,)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE admin_player_notes SET note = ?, updated_at = ? WHERE LOWER(pseudo) = LOWER(?)",
                    (note, now_iso(), pseudo),
                )
            else:
                conn.execute(
                    "INSERT INTO admin_player_notes (pseudo, note, updated_at) VALUES (?, ?, ?)",
                    (pseudo, note, now_iso()),
                )
            conn.commit()
        log_action("player_note", f"Note administrateur mise à jour pour {pseudo}")
        return redirect(url_for("admin_user_detail", pseudo=pseudo))

    @app.route("/admin/journal")
    @admin_required
    def admin_logs_page():
        ensure_schema()
        action_filter = (request.args.get("action") or "").strip()
        query = "SELECT actor, action, details, created_at FROM admin_logs"
        params = []
        if action_filter:
            query += " WHERE action = ?"
            params.append(action_filter)
        query += " ORDER BY created_at DESC LIMIT 500"
        with db_connection() as conn:
            logs = conn.execute(query, tuple(params)).fetchall()
            actions = conn.execute("SELECT DISTINCT action FROM admin_logs ORDER BY action ASC").fetchall()
        return render_template("admin/logs.html", logs=logs, actions=actions, action_filter=action_filter)

    @app.route("/admin/annonces")
    @admin_required
    def admin_announcements():
        ensure_schema()
        with db_connection() as conn:
            rows = conn.execute(
                "SELECT id, title, message, kind, active, starts_at, ends_at, created_at, updated_at "
                "FROM admin_announcements ORDER BY created_at DESC LIMIT 200"
            ).fetchall()
        return render_template("admin/announcements.html", announcements=rows)

    @app.route("/admin/annonces/ajouter", methods=["POST"])
    @admin_required
    def admin_announcement_add():
        verify_admin_csrf()
        ensure_schema()
        title = (request.form.get("title") or "").strip()[:100]
        message = (request.form.get("message") or "").strip()[:700]
        kind = request.form.get("kind") or "info"
        starts_at = (request.form.get("starts_at") or "").strip() or None
        ends_at = (request.form.get("ends_at") or "").strip() or None
        if not title or not message or kind not in {"info", "success", "warning"}:
            abort(400)
        # datetime-local values have no timezone. Interpret them as the server/user's
        # intended local clock and store an ISO string; exact scheduling is optional.
        timestamp = now_iso()
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO admin_announcements (id, title, message, kind, active, starts_at, ends_at, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (secrets.token_hex(16), title, message, kind, 1, starts_at, ends_at, timestamp, timestamp),
            )
            conn.commit()
        announcement_cache["loaded"] = 0.0
        log_action("announcement_add", f"Annonce créée : {title}")
        return redirect(url_for("admin_announcements"))

    @app.route("/admin/annonces/statut", methods=["POST"])
    @admin_required
    def admin_announcement_status():
        verify_admin_csrf()
        announcement_id = request.form.get("id", "")
        active = 1 if request.form.get("active") == "1" else 0
        with db_connection() as conn:
            conn.execute(
                "UPDATE admin_announcements SET active = ?, updated_at = ? WHERE id = ?",
                (active, now_iso(), announcement_id),
            )
            conn.commit()
        announcement_cache["loaded"] = 0.0
        log_action("announcement_status", f"Annonce {announcement_id} {'activée' if active else 'désactivée'}")
        return redirect(url_for("admin_announcements"))

    @app.route("/admin/annonces/supprimer", methods=["POST"])
    @admin_required
    def admin_announcement_delete():
        verify_admin_csrf()
        announcement_id = request.form.get("id", "")
        with db_connection() as conn:
            row = conn.execute("SELECT title FROM admin_announcements WHERE id = ?", (announcement_id,)).fetchone()
            conn.execute("DELETE FROM admin_announcements WHERE id = ?", (announcement_id,))
            conn.commit()
        announcement_cache["loaded"] = 0.0
        log_action("announcement_delete", f"Annonce supprimée : {row['title'] if row else announcement_id}")
        return redirect(url_for("admin_announcements"))

    @app.route("/admin/jeux/modifier", methods=["POST"])
    @admin_required
    def admin_game_edit():
        verify_admin_csrf()
        ensure_schema()
        slug = request.form.get("game", "")
        if slug not in games:
            abort(400)
        original = base_game_meta[slug]
        name = (request.form.get("name") or original.get("name", slug)).strip()[:80]
        description = (request.form.get("description") or original.get("description", "")).strip()[:600]
        emoji = (request.form.get("emoji") or original.get("emoji", "🎮")).strip()[:12]
        tag = (request.form.get("tag") or original.get("tag", "Jeu")).strip()[:40]
        with db_connection() as conn:
            exists = conn.execute("SELECT slug FROM admin_game_overrides WHERE slug = ?", (slug,)).fetchone()
            if exists:
                conn.execute(
                    "UPDATE admin_game_overrides SET name = ?, description = ?, emoji = ?, tag = ?, updated_at = ? WHERE slug = ?",
                    (name, description, emoji, tag, now_iso(), slug),
                )
            else:
                conn.execute(
                    "INSERT INTO admin_game_overrides (slug, name, description, emoji, tag, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (slug, name, description, emoji, tag, now_iso()),
                )
            conn.commit()
        game_cache["loaded"] = 0.0
        refresh_game_overrides(force=True)
        log_action("game_edit", f"Fiche jeu modifiée : {slug}")
        return redirect(url_for("admin_games"))

    @app.route("/admin/jeux/reinitialiser", methods=["POST"])
    @admin_required
    def admin_game_reset():
        verify_admin_csrf()
        slug = request.form.get("game", "")
        if slug not in games:
            abort(400)
        ensure_schema()
        with db_connection() as conn:
            conn.execute("DELETE FROM admin_game_overrides WHERE slug = ?", (slug,))
            conn.commit()
        games[slug].update(base_game_meta[slug])
        game_cache["loaded"] = 0.0
        log_action("game_reset", f"Fiche jeu réinitialisée : {slug}")
        return redirect(url_for("admin_games"))

    @app.route("/signaler", methods=["POST"])
    def public_report():
        ensure_schema()
        reporter = current_pseudo()
        if not reporter:
            return redirect(url_for("home", need_pseudo=1) + "#player")
        supplied = request.form.get("csrf_token", "")
        expected = session.get("public_report_csrf", "")
        if not supplied or not expected or not secrets.compare_digest(supplied, expected):
            abort(400)
        target_type = (request.form.get("target_type") or "").strip()[:40]
        target_value = (request.form.get("target_value") or "").strip()[:120]
        reason = (request.form.get("reason") or "").strip()[:500]
        if target_type not in {"player", "game", "content"} or not target_value or len(reason) < 5:
            abort(400)
        last_report = float(session.get("last_public_report", 0) or 0)
        if time.time() - last_report < 30:
            return redirect(request.referrer or url_for("home"))
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO admin_reports (id, reporter_pseudo, target_type, target_value, reason, status, created_at, resolved_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (secrets.token_hex(16), reporter, target_type, target_value, reason, "open", now_iso(), None),
            )
            conn.commit()
        session["last_public_report"] = time.time()
        return redirect(request.referrer or url_for("home"))
