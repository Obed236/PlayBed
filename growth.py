from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import abort, redirect, render_template, request, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

PARIS_TZ = ZoneInfo("Europe/Paris")
MONTHS_FR = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)


def _period_start(period):
    now = datetime.now(PARIS_TZ)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        start -= timedelta(days=start.weekday())
    elif period == "month":
        start = start.replace(day=1)
    return start.astimezone(timezone.utc).isoformat()


def _aggregate(db_connection, pseudo, cutoff=None):
    sql = """
        SELECT COUNT(*) AS games_played,
               COALESCE(SUM(points), 0) AS total_points,
               COALESCE(MAX(points), 0) AS best_score,
               COUNT(DISTINCT game) AS distinct_games
        FROM scores WHERE pseudo = ?
    """
    params = [pseudo]
    if cutoff:
        sql += " AND created_at >= ?"
        params.append(cutoff)
    with db_connection() as conn:
        row = conn.execute(sql, tuple(params)).fetchone()
    return {
        "games_played": int(row["games_played"] or 0),
        "total_points": int(row["total_points"] or 0),
        "best_score": int(row["best_score"] or 0),
        "distinct_games": int(row["distinct_games"] or 0),
    }


def progression_for(db_connection, pseudo):
    if not pseudo:
        return None
    stats = _aggregate(db_connection, pseudo)
    xp = stats["total_points"] // 5 + stats["games_played"] * 25 + stats["distinct_games"] * 100
    level = 1
    floor = 0
    needed = 500
    while xp >= floor + needed:
        floor += needed
        level += 1
        needed = 500 + (level - 1) * 250
    current = xp - floor
    percent = min(100, round((current / needed) * 100)) if needed else 100
    return {
        "xp": xp,
        "level": level,
        "current": current,
        "needed": needed,
        "percent": percent,
        "next_level": level + 1,
        "stats": stats,
    }


def missions_for(db_connection, pseudo):
    if not pseudo:
        return {"daily": [], "weekly": []}
    daily = _aggregate(db_connection, pseudo, _period_start("day"))
    weekly = _aggregate(db_connection, pseudo, _period_start("week"))

    daily_missions = [
        {"title": "Échauffement", "description": "Terminer 2 parties aujourd’hui", "current": daily["games_played"], "target": 2, "reward": "+ activité"},
        {"title": "Score du jour", "description": "Cumuler 1 500 points aujourd’hui", "current": daily["total_points"], "target": 1500, "reward": "+ progression"},
        {"title": "Explorateur", "description": "Jouer à 2 jeux différents aujourd’hui", "current": daily["distinct_games"], "target": 2, "reward": "+ variété"},
    ]
    weekly_missions = [
        {"title": "Régulier", "description": "Terminer 10 parties cette semaine", "current": weekly["games_played"], "target": 10, "reward": "+ activité"},
        {"title": "Chasseur de points", "description": "Cumuler 7 500 points cette semaine", "current": weekly["total_points"], "target": 7500, "reward": "+ classement"},
        {"title": "Tour de PlayBed", "description": "Jouer à 4 jeux différents cette semaine", "current": weekly["distinct_games"], "target": 4, "reward": "+ exploration"},
    ]
    for mission in daily_missions + weekly_missions:
        mission["completed"] = mission["current"] >= mission["target"]
        mission["percent"] = min(100, round((mission["current"] / mission["target"]) * 100)) if mission["target"] else 100
    return {"daily": daily_missions, "weekly": weekly_missions}


def trending_for(db_connection, games):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT game, COUNT(*) AS plays
            FROM scores
            WHERE created_at >= ?
            GROUP BY game
            ORDER BY plays DESC
            LIMIT 5
            """,
            (cutoff,),
        ).fetchall()
    return [
        {"slug": row["game"], "plays": int(row["plays"]), **games[row["game"]]}
        for row in rows if row["game"] in games
    ]


def season_info():
    now = datetime.now(PARIS_TZ)
    return {
        "name": f"Saison {MONTHS_FR[now.month - 1].capitalize()} {now.year}",
        "period": "mois",
    }


def register_growth(app, games, db_connection, current_pseudo):
    serializer = URLSafeTimedSerializer(app.secret_key, salt="playbed-challenge-v1")

    @app.context_processor
    def inject_growth():
        endpoint = request.endpoint or ""
        data = {
            "growth_progress": None,
            "growth_missions": {"daily": [], "weekly": []},
            "growth_trending": [],
            "growth_season": season_info(),
        }
        if endpoint not in {"home", "platform_profile", "leaderboard", "platform_period_leaderboard"}:
            return data
        pseudo = current_pseudo()
        if pseudo:
            data["growth_progress"] = progression_for(db_connection, pseudo)
            data["growth_missions"] = missions_for(db_connection, pseudo)
        if endpoint == "home":
            data["growth_trending"] = trending_for(db_connection, games)
        return data

    @app.route("/joueur/<pseudo>")
    def growth_public_profile(pseudo):
        if not pseudo or len(pseudo) > 20:
            abort(404)
        stats = _aggregate(db_connection, pseudo)
        if stats["games_played"] == 0:
            abort(404)
        with db_connection() as conn:
            recent = conn.execute(
                "SELECT game, points, created_at FROM scores WHERE pseudo = ? ORDER BY created_at DESC LIMIT 10",
                (pseudo,),
            ).fetchall()
            by_game_rows = conn.execute(
                """
                SELECT game, COUNT(*) AS games_played, MAX(points) AS best_points, SUM(points) AS total_points
                FROM scores WHERE pseudo = ? GROUP BY game ORDER BY total_points DESC
                """,
                (pseudo,),
            ).fetchall()
            ranking = conn.execute(
                "SELECT pseudo, SUM(points) AS total_points FROM scores GROUP BY pseudo ORDER BY total_points DESC, pseudo ASC"
            ).fetchall()
        rank = next((index + 1 for index, row in enumerate(ranking) if row["pseudo"] == pseudo), None)
        by_game = {row["game"]: dict(row) for row in by_game_rows if row["game"] in games}
        return render_template(
            "public_profile.html",
            viewed_pseudo=pseudo,
            pseudo=current_pseudo(),
            stats=stats,
            progression=progression_for(db_connection, pseudo),
            rank=rank,
            recent=[dict(row) for row in recent if row["game"] in games],
            by_game=by_game,
            games=games,
        )

    @app.route("/defi/creer/<game>")
    def growth_create_challenge(game):
        pseudo = current_pseudo()
        if not pseudo:
            return redirect(url_for("home", need_pseudo=1) + "#player")
        if game not in games:
            abort(404)
        with db_connection() as conn:
            row = conn.execute(
                "SELECT MAX(points) AS best FROM scores WHERE pseudo = ? AND game = ?",
                (pseudo, game),
            ).fetchone()
        target = int(row["best"] or 500)
        payload = {
            "challenger": pseudo,
            "game": game,
            "target": target,
            "created": datetime.now(timezone.utc).date().isoformat(),
        }
        token = serializer.dumps(payload)
        return redirect(url_for("growth_challenge", token=token))

    @app.route("/defi/<token>")
    def growth_challenge(token):
        try:
            challenge = serializer.loads(token, max_age=60 * 60 * 24 * 30)
        except (BadSignature, SignatureExpired):
            abort(404)
        game = challenge.get("game")
        if game not in games:
            abort(404)
        share_url = url_for("growth_challenge", token=token, _external=True, _scheme="https")
        return render_template(
            "challenge.html",
            challenge=challenge,
            game=game,
            meta=games[game],
            pseudo=current_pseudo(),
            share_url=share_url,
        )

    @app.route("/developpeurs")
    def growth_developers():
        return render_template("developers.html", pseudo=current_pseudo(), games=games)
