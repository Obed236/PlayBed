from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import jsonify, redirect, render_template, request, url_for

PARIS_TZ = ZoneInfo("Europe/Paris")

CATEGORY_LABELS = {
    "Lettres": "Mots & lettres",
    "Logique": "Logique",
    "Culture": "Culture générale",
    "Quiz": "Quiz",
    "Mémoire": "Mémoire",
}


def _utc_iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _period_cutoffs():
    now = datetime.now(PARIS_TZ)
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week = day - timedelta(days=day.weekday())
    return _utc_iso(day), _utc_iso(week)


def level_from_xp(xp):
    xp = max(0, int(xp or 0))
    level = 1
    floor = 0
    while level < 100:
        step = 1000 + (level - 1) * 250
        if xp < floor + step:
            break
        floor += step
        level += 1
    next_step = 1000 + (level - 1) * 250
    current = xp - floor
    percent = min(100, round((current / next_step) * 100)) if next_step else 100
    return {
        "xp": xp,
        "level": level,
        "current": current,
        "needed": next_step,
        "percent": percent,
        "next_level": min(100, level + 1),
    }


def growth_for(db_connection, pseudo):
    empty = {
        "progress": level_from_xp(0),
        "daily_missions": [],
        "weekly_missions": [],
        "completed_daily": 0,
        "completed_weekly": 0,
    }
    if not pseudo:
        return empty

    day_cutoff, week_cutoff = _period_cutoffs()
    with db_connection() as conn:
        totals = conn.execute(
            """
            SELECT COUNT(*) AS games_played,
                   COALESCE(SUM(points), 0) AS total_points,
                   COALESCE(MAX(points), 0) AS best_score,
                   COUNT(DISTINCT game) AS distinct_games
            FROM scores WHERE pseudo = ?
            """,
            (pseudo,),
        ).fetchone()
        today = conn.execute(
            """
            SELECT COUNT(*) AS games_played,
                   COALESCE(SUM(points), 0) AS total_points,
                   COALESCE(MAX(points), 0) AS best_score,
                   COUNT(DISTINCT game) AS distinct_games
            FROM scores WHERE pseudo = ? AND created_at >= ?
            """,
            (pseudo, day_cutoff),
        ).fetchone()
        week = conn.execute(
            """
            SELECT COUNT(*) AS games_played,
                   COALESCE(SUM(points), 0) AS total_points,
                   COALESCE(MAX(points), 0) AS best_score,
                   COUNT(DISTINCT game) AS distinct_games
            FROM scores WHERE pseudo = ? AND created_at >= ?
            """,
            (pseudo, week_cutoff),
        ).fetchone()

    progress = level_from_xp(totals["total_points"])
    daily = [
        {"icon": "🎮", "name": "Première partie", "description": "Terminer une partie aujourd’hui", "value": int(today["games_played"] or 0), "target": 1},
        {"icon": "⭐", "name": "Score solide", "description": "Atteindre 700 points sur une partie", "value": int(today["best_score"] or 0), "target": 700},
        {"icon": "🧭", "name": "Explorateur du jour", "description": "Jouer à 2 jeux différents", "value": int(today["distinct_games"] or 0), "target": 2},
    ]
    weekly = [
        {"icon": "🔥", "name": "Régulier", "description": "Terminer 7 parties cette semaine", "value": int(week["games_played"] or 0), "target": 7},
        {"icon": "🎯", "name": "Polyvalent", "description": "Jouer à 3 jeux différents cette semaine", "value": int(week["distinct_games"] or 0), "target": 3},
        {"icon": "🏆", "name": "Chasseur de points", "description": "Gagner 5 000 points cette semaine", "value": int(week["total_points"] or 0), "target": 5000},
    ]
    for mission in daily + weekly:
        mission["completed"] = mission["value"] >= mission["target"]
        mission["percent"] = min(100, round((mission["value"] / mission["target"]) * 100)) if mission["target"] else 100

    return {
        "progress": progress,
        "daily_missions": daily,
        "weekly_missions": weekly,
        "completed_daily": sum(1 for item in daily if item["completed"]),
        "completed_weekly": sum(1 for item in weekly if item["completed"]),
    }


def register_growth(app, games, db_connection, current_pseudo):
    @app.context_processor
    def inject_growth():
        endpoint = request.endpoint or ""
        if endpoint not in {"home", "platform_profile", "platform_explore", "platform_challenge_share"}:
            return {"growth": None, "category_labels": CATEGORY_LABELS}
        return {
            "growth": growth_for(db_connection, current_pseudo()),
            "category_labels": CATEGORY_LABELS,
        }

    @app.route("/explorer")
    def platform_explore():
        return render_template(
            "explore.html",
            games=games,
            pseudo=current_pseudo(),
            category_labels=CATEGORY_LABELS,
        )

    @app.route("/defi/<game>/<int:target>")
    def platform_challenge_share(game, target):
        if game not in games or target < 100 or target > 10000:
            return redirect(url_for("home"))
        return render_template(
            "share_challenge.html",
            game=game,
            meta=games[game],
            target=target,
            pseudo=current_pseudo(),
        )

    @app.route("/developpeurs")
    def platform_developers():
        return render_template("developers.html", games=games, pseudo=current_pseudo())

    @app.route("/api/v1/games")
    def platform_games_api():
        payload = []
        for slug, game in games.items():
            payload.append({
                "slug": slug,
                "name": game["name"],
                "emoji": game["emoji"],
                "description": game["description"],
                "category": CATEGORY_LABELS.get(game["tag"], game["tag"]),
                "play_url": url_for("start_game", game=slug, _external=True),
                "details_url": url_for("platform_game_detail", game=slug, _external=True),
            })
        response = jsonify({"platform": "PlayBed", "version": "3", "games": payload})
        response.headers["Cache-Control"] = "public, max-age=300"
        return response
