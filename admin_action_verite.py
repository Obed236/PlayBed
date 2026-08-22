import secrets
import time
from datetime import datetime, timezone
from functools import wraps

from flask import abort, redirect, render_template, request, session, url_for

import action_verite as av
import action_verite_preferences as preferences
import action_verite_no_repeat as no_repeat


def register_admin_action_verite(app, db_connection):
    """Make every Action ou Vérité prompt pool manageable from the back-office."""

    pools = {
        "classic_truth": {"label": "Classique · Vérité", "target": av.NORMAL_TRUTHS},
        "classic_dare": {"label": "Classique · Action", "target": av.NORMAL_DARES},
        "daring_truth": {"label": "Osé · Vérité", "target": preferences.DARING_TRUTHS},
        "daring_dare": {"label": "Osé · Action", "target": preferences.DARING_DARES},
        "very_daring_truth": {"label": "Très osé · Vérité", "target": no_repeat.STRONG_VERY_DARING_TRUTHS},
        "very_daring_dare": {"label": "Très osé · Action", "target": no_repeat.STRONG_VERY_DARING_DARES},
    }
    base = {key: list(info["target"]) for key, info in pools.items()}
    cache = {"loaded": 0.0}

    def now_iso():
        return datetime.now(timezone.utc).isoformat()

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("playbed_admin"):
                return redirect(url_for("admin_login", next=request.path))
            return view(*args, **kwargs)
        return wrapped

    def verify_csrf():
        supplied = request.form.get("csrf_token", "")
        expected = session.get("admin_csrf", "")
        if not supplied or not expected or not secrets.compare_digest(supplied, expected):
            abort(400)

    def ensure_schema():
        with db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_av_overrides (
                    source_key TEXT PRIMARY KEY,
                    bucket TEXT NOT NULL,
                    source_index INTEGER NOT NULL,
                    prompt TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_av_custom (
                    id TEXT PRIMARY KEY,
                    bucket TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def log_action(action, details):
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO admin_logs (id, actor, action, details, created_at) VALUES (?, ?, ?, ?, ?)",
                (secrets.token_hex(16), session.get("playbed_admin", "admin"), action, details[:1000], now_iso()),
            )
            conn.commit()

    def refresh(force=False):
        if not force and time.monotonic() - cache["loaded"] < 30:
            return
        try:
            ensure_schema()
            with db_connection() as conn:
                overrides = conn.execute(
                    "SELECT source_key, bucket, source_index, prompt, active FROM admin_av_overrides"
                ).fetchall()
                custom = conn.execute(
                    "SELECT id, bucket, prompt, active FROM admin_av_custom ORDER BY created_at ASC"
                ).fetchall()
            by_bucket = {key: {} for key in pools}
            for row in overrides:
                if row["bucket"] in by_bucket:
                    by_bucket[row["bucket"]][int(row["source_index"])] = row
            custom_by_bucket = {key: [] for key in pools}
            for row in custom:
                if row["bucket"] in custom_by_bucket and int(row["active"]) == 1:
                    custom_by_bucket[row["bucket"]].append(row["prompt"])
            for key, info in pools.items():
                values = []
                for index, original in enumerate(base[key]):
                    override = by_bucket[key].get(index)
                    if override and int(override["active"]) != 1:
                        continue
                    values.append(override["prompt"] if override else original)
                values.extend(custom_by_bucket[key])
                if not values:
                    values = ["Aucune proposition active dans cette catégorie. Tu peux passer ce tour."]
                info["target"][:] = values
            # These names are used directly by the preference engine.
            preferences.NORMAL_TRUTHS = pools["classic_truth"]["target"]
            preferences.NORMAL_DARES = pools["classic_dare"]["target"]
            preferences.DARING_TRUTHS = pools["daring_truth"]["target"]
            preferences.DARING_DARES = pools["daring_dare"]["target"]
            preferences.VERY_DARING_TRUTHS = pools["very_daring_truth"]["target"]
            preferences.VERY_DARING_DARES = pools["very_daring_dare"]["target"]
            cache["loaded"] = time.monotonic()
        except Exception:
            app.logger.exception("Impossible de charger les contenus Action ou Vérité administrés")

    @app.before_request
    def refresh_action_verite_admin_content():
        if request.path.startswith("/action-verite") or request.path.startswith("/jeux/action-verite") or request.path.startswith("/admin/action-verite"):
            refresh()

    def view_rows():
        ensure_schema()
        with db_connection() as conn:
            override_rows = conn.execute(
                "SELECT source_key, bucket, source_index, prompt, active FROM admin_av_overrides"
            ).fetchall()
            custom_rows = conn.execute(
                "SELECT id, bucket, prompt, active, created_at, updated_at FROM admin_av_custom ORDER BY created_at ASC"
            ).fetchall()
        overrides = {row["source_key"]: row for row in override_rows}
        result = {}
        for key, info in pools.items():
            base_rows = []
            for index, original in enumerate(base[key]):
                source_key = f"{key}:{index}"
                override = overrides.get(source_key)
                base_rows.append({
                    "source": "base", "id": str(index), "bucket": key,
                    "prompt": override["prompt"] if override else original,
                    "active": bool(int(override["active"])) if override else True,
                    "modified": bool(override),
                })
            custom = [
                {"source": "custom", "id": row["id"], "bucket": key, "prompt": row["prompt"], "active": bool(int(row["active"])), "modified": True}
                for row in custom_rows if row["bucket"] == key
            ]
            result[key] = {"label": info["label"], "base": base_rows, "custom": custom}
        return result

    @app.route("/admin/action-verite-contenu")
    @admin_required
    def admin_av_content():
        refresh(force=True)
        return render_template("admin/action_verite_content.html", sections=view_rows())

    @app.route("/admin/action-verite-contenu/ajouter", methods=["POST"])
    @admin_required
    def admin_av_add():
        verify_csrf()
        ensure_schema()
        bucket = request.form.get("bucket", "")
        prompt = (request.form.get("prompt") or "").strip()[:700]
        if bucket not in pools or len(prompt) < 5:
            abort(400)
        stamp = now_iso()
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO admin_av_custom (id, bucket, prompt, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (secrets.token_hex(16), bucket, prompt, 1, stamp, stamp),
            )
            conn.commit()
        cache["loaded"] = 0.0
        refresh(force=True)
        log_action("av_prompt_add", f"{bucket}: {prompt[:120]}")
        return redirect(url_for("admin_av_content"))

    @app.route("/admin/action-verite-contenu/modifier", methods=["POST"])
    @admin_required
    def admin_av_edit():
        verify_csrf()
        ensure_schema()
        source = request.form.get("source", "")
        bucket = request.form.get("bucket", "")
        item_id = request.form.get("id", "")
        prompt = (request.form.get("prompt") or "").strip()[:700]
        active = 1 if request.form.get("active") == "1" else 0
        if bucket not in pools or source not in {"base", "custom"} or len(prompt) < 5:
            abort(400)
        with db_connection() as conn:
            if source == "base":
                try:
                    index = int(item_id)
                    base[bucket][index]
                except (ValueError, IndexError):
                    abort(400)
                source_key = f"{bucket}:{index}"
                exists = conn.execute("SELECT source_key FROM admin_av_overrides WHERE source_key = ?", (source_key,)).fetchone()
                if exists:
                    conn.execute(
                        "UPDATE admin_av_overrides SET prompt = ?, active = ?, updated_at = ? WHERE source_key = ?",
                        (prompt, active, now_iso(), source_key),
                    )
                else:
                    conn.execute(
                        "INSERT INTO admin_av_overrides (source_key, bucket, source_index, prompt, active, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (source_key, bucket, index, prompt, active, now_iso()),
                    )
            else:
                conn.execute(
                    "UPDATE admin_av_custom SET prompt = ?, active = ?, updated_at = ? WHERE id = ? AND bucket = ?",
                    (prompt, active, now_iso(), item_id, bucket),
                )
            conn.commit()
        cache["loaded"] = 0.0
        refresh(force=True)
        log_action("av_prompt_edit", f"{bucket} / {source} / {item_id} modifié")
        return redirect(url_for("admin_av_content"))

    @app.route("/admin/action-verite-contenu/reinitialiser", methods=["POST"])
    @admin_required
    def admin_av_reset():
        verify_csrf()
        bucket = request.form.get("bucket", "")
        item_id = request.form.get("id", "")
        if bucket not in pools:
            abort(400)
        with db_connection() as conn:
            conn.execute("DELETE FROM admin_av_overrides WHERE source_key = ?", (f"{bucket}:{item_id}",))
            conn.commit()
        cache["loaded"] = 0.0
        refresh(force=True)
        log_action("av_prompt_reset", f"{bucket}:{item_id} réinitialisé")
        return redirect(url_for("admin_av_content"))

    @app.route("/admin/action-verite-contenu/supprimer", methods=["POST"])
    @admin_required
    def admin_av_delete():
        verify_csrf()
        item_id = request.form.get("id", "")
        with db_connection() as conn:
            row = conn.execute("SELECT bucket, prompt FROM admin_av_custom WHERE id = ?", (item_id,)).fetchone()
            conn.execute("DELETE FROM admin_av_custom WHERE id = ?", (item_id,))
            conn.commit()
        cache["loaded"] = 0.0
        refresh(force=True)
        log_action("av_prompt_delete", f"Supprimé : {row['prompt'][:120] if row else item_id}")
        return redirect(url_for("admin_av_content"))
