import re
import secrets
from datetime import datetime, timedelta, timezone

from flask import abort, redirect, render_template, request, session, url_for


STARTING_BALANCE = 1000
MIN_STAKE = 50
MAX_STAKE = 10000
MATCH_TTL_HOURS = 72
NON_SCORED_GAMES = {"action-verite"}
EXTRA_SESSION_KEYS = {
    "calcul": "extra_calcul",
    "melange": "extra_melange",
    "suite": "extra_suite",
    "pair": "extra_pair",
    "chrono": "extra_chrono",
}


def _now():
    return datetime.now(timezone.utc).isoformat()


class VersusManager:
    def __init__(self, app, games, db_connection, current_pseudo, base_save_score):
        self.app = app
        self.games = games
        self.db_connection = db_connection
        self.current_pseudo = current_pseudo
        self.base_save_score = base_save_score
        self._routes_registered = False
        self.ensure_tables()

    @property
    def scored_games(self):
        return {slug: meta for slug, meta in self.games.items() if slug not in NON_SCORED_GAMES}

    def ensure_tables(self):
        with self.db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS versus_wallets (
                    player_token TEXT PRIMARY KEY,
                    pseudo TEXT NOT NULL,
                    balance INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS versus_matches (
                    id TEXT PRIMARY KEY,
                    game TEXT NOT NULL,
                    creator_token TEXT NOT NULL,
                    creator_name TEXT NOT NULL,
                    opponent_token TEXT,
                    opponent_name TEXT,
                    stake INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    creator_score INTEGER,
                    opponent_score INTEGER,
                    winner_name TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    finished_at TEXT
                )
            """)
            conn.commit()
        self.cleanup_expired_matches()

    def player_token(self):
        token = session.get("versus_player_token")
        if not isinstance(token, str) or len(token) < 20:
            token = secrets.token_urlsafe(24)
            session["versus_player_token"] = token
        return token

    def wallet(self, create=True):
        pseudo = self.current_pseudo()
        if not pseudo:
            return None
        token = self.player_token()
        with self.db_connection() as conn:
            row = conn.execute(
                "SELECT player_token, pseudo, balance FROM versus_wallets WHERE player_token = ?",
                (token,),
            ).fetchone()
            if not row and create:
                now = _now()
                conn.execute(
                    "INSERT INTO versus_wallets (player_token, pseudo, balance, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (token, pseudo, STARTING_BALANCE, now, now),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT player_token, pseudo, balance FROM versus_wallets WHERE player_token = ?",
                    (token,),
                ).fetchone()
            elif row and row["pseudo"] != pseudo:
                conn.execute(
                    "UPDATE versus_wallets SET pseudo = ?, updated_at = ? WHERE player_token = ?",
                    (pseudo, _now(), token),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT player_token, pseudo, balance FROM versus_wallets WHERE player_token = ?",
                    (token,),
                ).fetchone()
        return dict(row) if row else None

    def _change_balance(self, conn, token, delta):
        row = conn.execute(
            "SELECT balance FROM versus_wallets WHERE player_token = ?",
            (token,),
        ).fetchone()
        if not row:
            return False
        new_balance = int(row["balance"]) + int(delta)
        if new_balance < 0:
            return False
        conn.execute(
            "UPDATE versus_wallets SET balance = ?, updated_at = ? WHERE player_token = ?",
            (new_balance, _now(), token),
        )
        return True

    def get_match(self, match_id):
        if not re.fullmatch(r"[A-Za-z0-9]{8,16}", match_id or ""):
            return None
        with self.db_connection() as conn:
            row = conn.execute("SELECT * FROM versus_matches WHERE id = ?", (match_id,)).fetchone()
        return dict(row) if row else None

    def role_for(self, match, token=None):
        token = token or session.get("versus_player_token")
        if not token or not match:
            return None
        if match["creator_token"] == token:
            return "creator"
        if match.get("opponent_token") == token:
            return "opponent"
        return None

    def _settle_if_ready(self, match_id):
        match = self.get_match(match_id)
        if not match or match["status"] != "playing":
            return match
        if match["creator_score"] is None or match["opponent_score"] is None:
            return match

        creator_score = int(match["creator_score"])
        opponent_score = int(match["opponent_score"])
        stake = int(match["stake"])
        winner_name = None
        now = _now()

        with self.db_connection() as conn:
            current = conn.execute("SELECT * FROM versus_matches WHERE id = ?", (match_id,)).fetchone()
            if not current or current["status"] != "playing":
                return dict(current) if current else None

            if creator_score > opponent_score:
                self._change_balance(conn, match["creator_token"], stake * 2)
                winner_name = match["creator_name"]
            elif opponent_score > creator_score:
                self._change_balance(conn, match["opponent_token"], stake * 2)
                winner_name = match["opponent_name"]
            else:
                self._change_balance(conn, match["creator_token"], stake)
                self._change_balance(conn, match["opponent_token"], stake)

            conn.execute(
                "UPDATE versus_matches SET status = ?, winner_name = ?, updated_at = ?, finished_at = ? WHERE id = ?",
                ("finished", winner_name, now, now, match_id),
            )
            conn.commit()
        return self.get_match(match_id)

    def cleanup_expired_matches(self):
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=MATCH_TTL_HOURS)).isoformat()
        with self.db_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM versus_matches WHERE status IN ('waiting', 'playing') AND created_at < ?",
                (cutoff,),
            ).fetchall()
            for raw in rows:
                match = dict(raw)
                stake = int(match["stake"])
                now = _now()
                if match["status"] == "waiting":
                    self._change_balance(conn, match["creator_token"], stake)
                    conn.execute(
                        "UPDATE versus_matches SET status = 'cancelled', updated_at = ?, finished_at = ? WHERE id = ?",
                        (now, now, match["id"]),
                    )
                else:
                    creator_done = match["creator_score"] is not None
                    opponent_done = match["opponent_score"] is not None
                    if creator_done and not opponent_done:
                        self._change_balance(conn, match["creator_token"], stake * 2)
                        conn.execute(
                            "UPDATE versus_matches SET status = 'finished', winner_name = ?, updated_at = ?, finished_at = ? WHERE id = ?",
                            (match["creator_name"], now, now, match["id"]),
                        )
                    elif opponent_done and not creator_done:
                        self._change_balance(conn, match["opponent_token"], stake * 2)
                        conn.execute(
                            "UPDATE versus_matches SET status = 'finished', winner_name = ?, updated_at = ?, finished_at = ? WHERE id = ?",
                            (match["opponent_name"], now, now, match["id"]),
                        )
                    else:
                        self._change_balance(conn, match["creator_token"], stake)
                        if match.get("opponent_token"):
                            self._change_balance(conn, match["opponent_token"], stake)
                        conn.execute(
                            "UPDATE versus_matches SET status = 'cancelled', updated_at = ?, finished_at = ? WHERE id = ?",
                            (now, now, match["id"]),
                        )
            conn.commit()

    def save_score(self, game, points):
        self.base_save_score(game, points)
        pseudo = self.current_pseudo()
        if not pseudo or game not in self.scored_games:
            return

        wallet = self.wallet(create=True)
        token = wallet["player_token"] if wallet else None
        points = max(0, min(int(points), 10000))
        if token and points:
            with self.db_connection() as conn:
                self._change_balance(conn, token, points)
                conn.commit()

        active = session.get("versus_active_match")
        if not isinstance(active, dict) or active.get("game") != game:
            return
        match_id = active.get("id")
        match = self.get_match(match_id)
        role = self.role_for(match, token)
        if not match or match["status"] != "playing" or not role:
            session.pop("versus_active_match", None)
            return

        score_field = "creator_score" if role == "creator" else "opponent_score"
        if match.get(score_field) is None:
            with self.db_connection() as conn:
                conn.execute(
                    f"UPDATE versus_matches SET {score_field} = ?, updated_at = ? WHERE id = ? AND {score_field} IS NULL",
                    (points, _now(), match_id),
                )
                conn.commit()
        session.pop("versus_active_match", None)
        self._settle_if_ready(match_id)

    def register_routes(self):
        if self._routes_registered:
            return
        self._routes_registered = True
        app = self.app

        original_start = app.view_functions.get("start_game")
        original_restart = app.view_functions.get("restart_game")

        if original_start:
            def versus_start_guard(game):
                active = session.get("versus_active_match")
                if isinstance(active, dict):
                    match = self.get_match(active.get("id"))
                    token = session.get("versus_player_token")
                    role = self.role_for(match, token)
                    expected_game = match.get("game") if match else None
                    if not match or match.get("status") != "playing" or not role:
                        session.pop("versus_active_match", None)
                    elif game != expected_game:
                        return redirect(url_for("versus_match", match_id=match["id"]))
                    elif active.get("started"):
                        return redirect(url_for("play_game", game=game))
                    else:
                        active["started"] = True
                        session["versus_active_match"] = active
                return original_start(game)
            app.view_functions["start_game"] = versus_start_guard

        if original_restart:
            def versus_restart_guard(game):
                active = session.get("versus_active_match")
                if isinstance(active, dict) and active.get("game") == game:
                    match = self.get_match(active.get("id"))
                    if match and match.get("status") == "playing":
                        return redirect(url_for("play_game", game=game))
                return original_restart(game)
            app.view_functions["restart_game"] = versus_restart_guard

        @app.context_processor
        def inject_versus_wallet():
            if not self.current_pseudo():
                return {"versus_wallet": None}
            endpoint = request.endpoint or ""
            if endpoint not in {"home", "versus_home", "versus_match", "platform_profile"}:
                return {"versus_wallet": None}
            return {"versus_wallet": self.wallet(create=True)}

        @app.route("/affronter", methods=["GET", "POST"])
        def versus_home():
            pseudo = self.current_pseudo()
            if not pseudo:
                return redirect(url_for("home", need_pseudo=1) + "#player")
            self.cleanup_expired_matches()
            wallet = self.wallet(create=True)
            error = None
            selected_game = (request.args.get("jeu") or request.form.get("game") or "quiz").strip()

            if request.method == "POST":
                game = (request.form.get("game") or "").strip()
                try:
                    stake = int(request.form.get("stake", "0"))
                except (TypeError, ValueError):
                    stake = 0
                if game not in self.scored_games:
                    error = "Choisis un jeu avec un score."
                elif stake < MIN_STAKE or stake > MAX_STAKE:
                    error = f"La mise doit être comprise entre {MIN_STAKE} et {MAX_STAKE} points."
                elif stake > int(wallet["balance"]):
                    error = "Tu n’as pas assez de points de défi pour cette mise."
                else:
                    match_id = secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:10]
                    now = _now()
                    with self.db_connection() as conn:
                        if not self._change_balance(conn, wallet["player_token"], -stake):
                            error = "Solde insuffisant."
                        else:
                            conn.execute(
                                """
                                INSERT INTO versus_matches (
                                    id, game, creator_token, creator_name, stake, status, created_at, updated_at
                                ) VALUES (?, ?, ?, ?, ?, 'waiting', ?, ?)
                                """,
                                (match_id, game, wallet["player_token"], pseudo, stake, now, now),
                            )
                            conn.commit()
                    if not error:
                        return redirect(url_for("versus_match", match_id=match_id))

            token = wallet["player_token"]
            with self.db_connection() as conn:
                recent_rows = conn.execute(
                    """
                    SELECT * FROM versus_matches
                    WHERE creator_token = ? OR opponent_token = ?
                    ORDER BY created_at DESC LIMIT 12
                    """,
                    (token, token),
                ).fetchall()
            recent = [dict(row) for row in recent_rows]
            return render_template(
                "versus.html",
                pseudo=pseudo,
                wallet=wallet,
                games=self.scored_games,
                selected_game=selected_game if selected_game in self.scored_games else "quiz",
                recent=recent,
                error=error,
                min_stake=MIN_STAKE,
                max_stake=MAX_STAKE,
            )

        @app.route("/affronter/<match_id>")
        def versus_match(match_id):
            self.cleanup_expired_matches()
            match = self.get_match(match_id)
            if not match:
                abort(404)
            pseudo = self.current_pseudo()
            wallet = self.wallet(create=True) if pseudo else None
            token = wallet["player_token"] if wallet else None
            role = self.role_for(match, token)
            share_url = url_for("versus_match", match_id=match_id, _external=True, _scheme="https")
            return render_template(
                "versus_match.html",
                pseudo=pseudo,
                wallet=wallet,
                match=match,
                role=role,
                meta=self.games.get(match["game"], {}),
                share_url=share_url,
                min_stake=MIN_STAKE,
            )

        @app.route("/affronter/<match_id>/accepter", methods=["POST"])
        def versus_accept(match_id):
            pseudo = self.current_pseudo()
            if not pseudo:
                return redirect(url_for("home", need_pseudo=1) + "#player")
            match = self.get_match(match_id)
            wallet = self.wallet(create=True)
            if not match or match["status"] != "waiting":
                return redirect(url_for("versus_match", match_id=match_id))
            if match["creator_token"] == wallet["player_token"]:
                return redirect(url_for("versus_match", match_id=match_id))
            stake = int(match["stake"])
            if int(wallet["balance"]) < stake:
                return redirect(url_for("versus_match", match_id=match_id, solde=1))

            now = _now()
            with self.db_connection() as conn:
                current = conn.execute("SELECT status FROM versus_matches WHERE id = ?", (match_id,)).fetchone()
                if not current or current["status"] != "waiting":
                    return redirect(url_for("versus_match", match_id=match_id))
                if not self._change_balance(conn, wallet["player_token"], -stake):
                    return redirect(url_for("versus_match", match_id=match_id, solde=1))
                conn.execute(
                    """
                    UPDATE versus_matches
                    SET opponent_token = ?, opponent_name = ?, status = 'playing', updated_at = ?
                    WHERE id = ? AND status = 'waiting'
                    """,
                    (wallet["player_token"], pseudo, now, match_id),
                )
                conn.commit()
            return redirect(url_for("versus_match", match_id=match_id))

        @app.route("/affronter/<match_id>/jouer")
        def versus_play(match_id):
            pseudo = self.current_pseudo()
            if not pseudo:
                return redirect(url_for("home", need_pseudo=1) + "#player")
            match = self.get_match(match_id)
            wallet = self.wallet(create=True)
            role = self.role_for(match, wallet["player_token"] if wallet else None)
            if not match or match["status"] != "playing" or not role:
                return redirect(url_for("versus_match", match_id=match_id))
            score_field = "creator_score" if role == "creator" else "opponent_score"
            if match.get(score_field) is not None:
                return redirect(url_for("versus_match", match_id=match_id))

            session.pop("current_game", None)
            extra_key = EXTRA_SESSION_KEYS.get(match["game"])
            if extra_key:
                session.pop(extra_key, None)
            session["versus_active_match"] = {"id": match_id, "game": match["game"], "started": False}
            return redirect(url_for("start_game", game=match["game"]))

        @app.route("/affronter/<match_id>/annuler", methods=["POST"])
        def versus_cancel(match_id):
            match = self.get_match(match_id)
            wallet = self.wallet(create=False)
            token = wallet["player_token"] if wallet else None
            role = self.role_for(match, token)
            if not match or not role or match["status"] not in {"waiting", "playing"}:
                return redirect(url_for("versus_match", match_id=match_id))
            if match["creator_score"] is not None or match["opponent_score"] is not None:
                return redirect(url_for("versus_match", match_id=match_id))

            stake = int(match["stake"])
            with self.db_connection() as conn:
                self._change_balance(conn, match["creator_token"], stake)
                if match.get("opponent_token"):
                    self._change_balance(conn, match["opponent_token"], stake)
                conn.execute(
                    "UPDATE versus_matches SET status = 'cancelled', updated_at = ?, finished_at = ? WHERE id = ?",
                    (_now(), _now(), match_id),
                )
                conn.commit()
            session.pop("versus_active_match", None)
            return redirect(url_for("versus_home"))
