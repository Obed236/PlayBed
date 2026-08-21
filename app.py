import os

from core import app, GAMES, db_connection, current_pseudo, init_db, save_score, load_words, load_quiz_questions, USE_POSTGRES
from engagement import register_engagement
from platform_routes import register_platform_routes, GUIDES, GAME_CONTENT
from editorial_guides import EDITORIAL_GUIDES
from extra_games import EXTRA_GAMES, EXTRA_GAME_CONTENT, register_extra_games
from duels import register_duels
from international import register_international
from performance import register_performance
from creator_routes import register_creator_routes
from sitemap_routes import register_sitemap_route
from growth import register_growth

GUIDES.update(EDITORIAL_GUIDES)
GAMES.update(EXTRA_GAMES)
GAME_CONTENT.update(EXTRA_GAME_CONTENT)


class PlatformGames(dict):
    """Expose the full catalog while keeping legacy daily-challenge rotation on its supported games."""
    def keys(self):
        return [slug for slug in super().keys() if slug not in EXTRA_GAMES]


platform_games = PlatformGames(GAMES)


def v3_health():
    return {
        "status": "ok",
        "version": "3",
        "games": len(GAMES),
        "database": "postgresql" if USE_POSTGRES else "sqlite",
    }


app.view_functions["health"] = v3_health

register_platform_routes(app, platform_games, db_connection, current_pseudo)
register_extra_games(app, GAMES, current_pseudo, save_score, load_words)
register_duels(app, db_connection, current_pseudo, load_quiz_questions)
register_engagement(app, GAMES, db_connection, current_pseudo)
register_growth(app, GAMES, db_connection, current_pseudo)
register_international(app, GAMES, current_pseudo)
register_creator_routes(app, current_pseudo)
register_sitemap_route(app, GAMES, current_pseudo)
register_performance(app)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=True)
