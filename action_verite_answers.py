import re
from datetime import datetime, timedelta, timezone

from flask import abort, redirect, request, session, url_for


ANSWER_TTL_HOURS = 24
MAX_RESPONSE_LENGTH = 500


def _now():
    return datetime.now(timezone.utc).isoformat()


def register_action_verite_answers(app, db_connection):
    def ensure_answers_table():
        with db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS av_answers (
                    room_code TEXT PRIMARY KEY,
                    player_token TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_text TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=ANSWER_TTL_HOURS)).isoformat()
            conn.execute("DELETE FROM av_answers WHERE created_at < ?", (cutoff,))
            conn.commit()

    def membership_token(code):
        memberships = session.get("av_memberships")
        if not isinstance(memberships, dict):
            return None
        return memberships.get(code)

    def room_for(code):
        with db_connection() as conn:
            row = conn.execute(
                "SELECT code, status, turn_index, current_kind, current_prompt, updated_at FROM av_rooms WHERE code = ?",
                (code,),
            ).fetchone()
        return dict(row) if row else None

    def players_for(code):
        with db_connection() as conn:
            rows = conn.execute(
                "SELECT player_token, name, player_order FROM av_players WHERE room_code = ? ORDER BY player_order ASC",
                (code,),
            ).fetchall()
        return [dict(row) for row in rows]

    def current_answer(code):
        with db_connection() as conn:
            row = conn.execute(
                "SELECT player_name, kind, status, response_text, created_at FROM av_answers WHERE room_code = ?",
                (code,),
            ).fetchone()
        return dict(row) if row else None

    ensure_answers_table()

    @app.context_processor
    def inject_action_verite_answer():
        if request.endpoint != "av_room":
            return {"av_response": None}
        code = ((request.view_args or {}).get("code") or "").strip()
        if not re.fullmatch(r"\d{4}", code) or not membership_token(code):
            return {"av_response": None}
        return {"av_response": current_answer(code)}

    @app.before_request
    def require_answer_before_next_turn():
        if request.method != "POST":
            return None
        match = re.fullmatch(r"/action-verite/classe/(\d{4})/suivant", request.path)
        if not match:
            return None
        code = match.group(1)
        room = room_for(code)
        if room and room["current_prompt"] and not current_answer(code):
            return redirect(url_for("av_room", code=code))
        return None

    @app.route("/action-verite/classe/<code>/repondre", methods=["POST"])
    def av_room_answer(code):
        if not re.fullmatch(r"\d{4}", code):
            abort(404)

        ensure_answers_table()
        room = room_for(code)
        token = membership_token(code)
        players = players_for(code) if room else []
        if not room or room["status"] != "playing" or not room["current_prompt"] or not token or not players:
            abort(403)

        current = players[int(room["turn_index"]) % len(players)]
        if current["player_token"] != token:
            abort(403)

        mode = (request.form.get("mode") or "answer").strip().lower()
        raw_text = (request.form.get("answer_text") or "").strip()

        if mode == "pass":
            status = "passed"
            response_text = ""
        elif room["current_kind"] == "verite":
            if not raw_text or len(raw_text) > MAX_RESPONSE_LENGTH:
                return redirect(url_for("av_room", code=code))
            status = "answered"
            response_text = raw_text
        elif room["current_kind"] == "action":
            if len(raw_text) > MAX_RESPONSE_LENGTH:
                return redirect(url_for("av_room", code=code))
            status = "done"
            response_text = raw_text
        else:
            abort(400)

        now = _now()
        with db_connection() as conn:
            conn.execute("DELETE FROM av_answers WHERE room_code = ?", (code,))
            conn.execute(
                """
                INSERT INTO av_answers (
                    room_code, player_token, player_name, kind, status, response_text, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    code,
                    current["player_token"],
                    current["name"],
                    room["current_kind"],
                    status,
                    response_text,
                    now,
                ),
            )
            conn.execute("UPDATE av_rooms SET updated_at = ? WHERE code = ?", (now, code))
            conn.commit()
        return redirect(url_for("av_room", code=code))

    @app.after_request
    def clear_action_verite_answer(response):
        if request.method != "POST" or response.status_code >= 400:
            return response
        match = re.fullmatch(
            r"/action-verite/classe/(\d{4})/(choisir|suivant|fermer)",
            request.path,
        )
        if not match:
            return response
        ensure_answers_table()
        code = match.group(1)
        with db_connection() as conn:
            conn.execute("DELETE FROM av_answers WHERE room_code = ?", (code,))
            conn.commit()
        return response
