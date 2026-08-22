from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import redirect, render_template, request, send_from_directory, url_for

PARIS_TZ = ZoneInfo("Europe/Paris")
VALID_PERIODS = {
    "jour": "Aujourd’hui",
    "semaine": "Cette semaine",
    "mois": "Ce mois",
}


def _local_day(value):
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(PARIS_TZ).date()


def _period_start(period):
    now = datetime.now(PARIS_TZ)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "jour":
        local_start = day_start
    elif period == "semaine":
        local_start = day_start - timedelta(days=day_start.weekday())
    elif period == "mois":
        local_start = day_start.replace(day=1)
    else:
        return None
    return local_start.astimezone(timezone.utc).isoformat()


def _score_filter(period):
    cutoff = _period_start(period)
    if cutoff is None:
        return "", ()
    return " WHERE created_at >= ?", (cutoff,)


def streak_for(db_connection, pseudo):
    if not pseudo:
        return {
            "current": 0,
            "best": 0,
            "played_today": False,
            "at_risk": False,
            "next_goal": 7,
        }

    with db_connection() as conn:
        rows = conn.execute(
            "SELECT created_at FROM scores WHERE pseudo = ? ORDER BY created_at DESC LIMIT 5000",
            (pseudo,),
        ).fetchall()

    days = sorted(
        {day for row in rows if (day := _local_day(row["created_at"])) is not None}
    )
    if not days:
        return {
            "current": 0,
            "best": 0,
            "played_today": False,
            "at_risk": False,
            "next_goal": 7,
        }

    best = 1
    run = 1
    for previous, current in zip(days, days[1:]):
        if current == previous + timedelta(days=1):
            run += 1
            best = max(best, run)
        else:
            run = 1

    today = datetime.now(PARIS_TZ).date()
    latest = days[-1]
    current_streak = 0
    if latest in {today, today - timedelta(days=1)}:
        current_streak = 1
        cursor = latest
        day_set = set(days)
        while cursor - timedelta(days=1) in day_set:
            cursor -= timedelta(days=1)
            current_streak += 1

    goals = (7, 30, 100, 365)
    next_goal = next((goal for goal in goals if current_streak < goal), current_streak + 100)

    return {
        "current": current_streak,
        "best": best,
        "played_today": today in set(days),
        "at_risk": current_streak > 0 and latest == today - timedelta(days=1),
        "next_goal": next_goal,
    }


def leaderboard_for(db_connection, games, period="general", limit=50):
    where_sql, params = _score_filter(period)
    with db_connection() as conn:
        overall = conn.execute(
            f"""
            SELECT pseudo, SUM(points) AS total_points, COUNT(*) AS games_played
            FROM scores
            {where_sql}
            GROUP BY pseudo
            ORDER BY total_points DESC, games_played ASC, pseudo ASC
            LIMIT ?
            """,
            params + (limit,),
        ).fetchall()

        best_by_game = {}
        for slug in games:
            if where_sql:
                game_where = "WHERE game = ? AND created_at >= ?"
                game_params = (slug, params[0])
            else:
                game_where = "WHERE game = ?"
                game_params = (slug,)
            best_by_game[slug] = conn.execute(
                f"""
                SELECT pseudo, MAX(points) AS points
                FROM scores
                {game_where}
                GROUP BY pseudo
                ORDER BY points DESC, pseudo ASC
                LIMIT 5
                """,
                game_params,
            ).fetchall()

    return overall, best_by_game


def rank_for(db_connection, pseudo, period="general"):
    if not pseudo:
        return None
    where_sql, params = _score_filter(period)
    with db_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT pseudo, SUM(points) AS total_points
            FROM scores
            {where_sql}
            GROUP BY pseudo
            ORDER BY total_points DESC, pseudo ASC
            """,
            params,
        ).fetchall()
    return next((index + 1 for index, row in enumerate(rows) if row["pseudo"] == pseudo), None)


def register_engagement(app, games, db_connection, current_pseudo):
    static_dir = Path(app.static_folder)

    @app.context_processor
    def inject_engagement():
        pseudo = current_pseudo()
        endpoint = request.endpoint or ""
        if not pseudo or endpoint not in {
            "platform_profile",
            "leaderboard",
            "platform_period_leaderboard",
        }:
            return {"engagement_streak": None, "engagement_ranks": {}}

        return {
            "engagement_streak": streak_for(db_connection, pseudo),
            "engagement_ranks": {
                "jour": rank_for(db_connection, pseudo, "jour"),
                "semaine": rank_for(db_connection, pseudo, "semaine"),
                "mois": rank_for(db_connection, pseudo, "mois"),
                "general": rank_for(db_connection, pseudo, "general"),
            },
        }

    @app.route("/classement/periode/<period>")
    def platform_period_leaderboard(period):
        if period not in VALID_PERIODS:
            return redirect(url_for("leaderboard"))
        overall, best_by_game = leaderboard_for(db_connection, games, period)
        return render_template(
            "leaderboard.html",
            overall=overall,
            best_by_game=best_by_game,
            games=games,
            pseudo=current_pseudo(),
            period=period,
            period_label=VALID_PERIODS[period],
        )

    @app.route("/manifest.webmanifest")
    def pwa_manifest():
        return send_from_directory(
            static_dir,
            "manifest.webmanifest",
            mimetype="application/manifest+json",
            max_age=3600,
        )

    @app.route("/service-worker.js")
    def pwa_service_worker():
        response = send_from_directory(
            static_dir,
            "service-worker.js",
            mimetype="application/javascript",
            max_age=0,
        )
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Cache-Control"] = "no-cache"
        return response
