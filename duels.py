import json
import secrets
from datetime import datetime, timedelta, timezone

from flask import redirect, render_template, request, session, url_for

_TABLE_READY = False


def register_duels(app, db_connection, current_pseudo, load_quiz_questions):
    def ensure_table():
        global _TABLE_READY
        if _TABLE_READY:
            return
        with db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS duels (
                    id TEXT PRIMARY KEY,
                    game TEXT NOT NULL,
                    creator TEXT NOT NULL,
                    questions_json TEXT NOT NULL,
                    creator_score INTEGER,
                    creator_finished_at TEXT,
                    opponent TEXT,
                    opponent_score INTEGER,
                    opponent_finished_at TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
        _TABLE_READY = True

    @app.before_request
    def ensure_duel_storage():
        ensure_table()

    def get_duel(duel_id):
        ensure_table()
        with db_connection() as conn:
            row = conn.execute("SELECT * FROM duels WHERE id = ?", (duel_id,)).fetchone()
        return dict(row) if row else None

    def is_expired(duel):
        try:
            created = datetime.fromisoformat(duel["created_at"])
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) - created > timedelta(days=7)
        except (TypeError, ValueError):
            return True

    @app.route("/duel/nouveau")
    def duel_create():
        pseudo = current_pseudo()
        if not pseudo:
            return redirect(url_for("home", need_pseudo=1) + "#player")
        questions = load_quiz_questions()
        selected = secrets.SystemRandom().sample(questions, k=min(10, len(questions)))
        duel_id = secrets.token_urlsafe(9).replace("-", "").replace("_", "")[:12]
        with db_connection() as conn:
            conn.execute(
                """
                INSERT INTO duels (id, game, creator, questions_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (duel_id, "quiz", pseudo, json.dumps(selected, ensure_ascii=False), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        session[f"duel:{duel_id}"] = {"role": "creator", "index": 0, "score": 0, "finished": False}
        return redirect(url_for("duel_play", duel_id=duel_id))

    @app.route("/duel/<duel_id>", methods=["GET", "POST"])
    def duel_play(duel_id):
        duel = get_duel(duel_id)
        if not duel or is_expired(duel):
            return render_template("404.html", pseudo=current_pseudo()), 404

        pseudo = current_pseudo()
        share_url = url_for("duel_play", duel_id=duel_id, _external=True, _scheme="https")
        questions = json.loads(duel["questions_json"])
        state_key = f"duel:{duel_id}"
        state = session.get(state_key)

        if not pseudo:
            return render_template(
                "duel.html", duel=duel, state=None, current_question=None, pseudo=None,
                share_url=share_url, waiting_for_pseudo=True, finished=False,
            )

        if not state:
            if pseudo == duel["creator"]:
                return render_template(
                    "duel.html", duel=duel, state=None, current_question=None, pseudo=pseudo,
                    share_url=share_url, locked=True, finished=bool(duel["creator_score"] is not None and duel["opponent_score"] is not None),
                )
            if duel["opponent"] and duel["opponent"] != pseudo:
                return render_template(
                    "duel.html", duel=duel, state=None, current_question=None, pseudo=pseudo,
                    share_url=share_url, full=True, finished=bool(duel["creator_score"] is not None and duel["opponent_score"] is not None),
                )
            if not duel["opponent"]:
                with db_connection() as conn:
                    conn.execute(
                        "UPDATE duels SET opponent = ? WHERE id = ? AND opponent IS NULL",
                        (pseudo, duel_id),
                    )
                    conn.commit()
                duel = get_duel(duel_id)
                if duel["opponent"] != pseudo:
                    return render_template(
                        "duel.html", duel=duel, state=None, current_question=None, pseudo=pseudo,
                        share_url=share_url, full=True, finished=bool(duel["creator_score"] is not None and duel["opponent_score"] is not None),
                    )
            state = {"role": "opponent", "index": 0, "score": 0, "finished": False}
            session[state_key] = state

        role = state["role"]
        already_finished = duel["creator_score"] is not None if role == "creator" else duel["opponent_score"] is not None
        if already_finished:
            state["finished"] = True

        if request.method == "POST" and not state["finished"]:
            index = int(state["index"])
            if 0 <= index < len(questions):
                answer = request.form.get("answer", "")
                current = questions[index]
                if answer == current["answer"]:
                    state["score"] += 1
                state["index"] += 1

            if state["index"] >= len(questions):
                state["finished"] = True
                final_score = int(state["score"]) * 100
                now = datetime.now(timezone.utc).isoformat()
                with db_connection() as conn:
                    if role == "creator":
                        conn.execute(
                            "UPDATE duels SET creator_score = ?, creator_finished_at = ? WHERE id = ? AND creator_score IS NULL",
                            (final_score, now, duel_id),
                        )
                    else:
                        conn.execute(
                            """
                            UPDATE duels SET opponent_score = ?, opponent_finished_at = ?
                            WHERE id = ? AND opponent = ? AND opponent_score IS NULL
                            """,
                            (final_score, now, duel_id, pseudo),
                        )
                    conn.commit()
                duel = get_duel(duel_id)
            session[state_key] = state

        current_question = None
        if not state["finished"] and state["index"] < len(questions):
            current_question = questions[state["index"]]

        duel = get_duel(duel_id)
        both_finished = duel["creator_score"] is not None and duel["opponent_score"] is not None
        return render_template(
            "duel.html",
            duel=duel,
            state=state,
            current_question=current_question,
            pseudo=pseudo,
            share_url=share_url,
            finished=both_finished,
            waiting_for_pseudo=False,
        )
