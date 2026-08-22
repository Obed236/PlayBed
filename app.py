import os

import core as core_module
from core import app, GAMES, db_connection, current_pseudo, init_db, save_score, load_words, load_quiz_questions
from engagement import register_engagement
from platform_routes import register_platform_routes, GUIDES, GAME_CONTENT
from editorial_guides import EDITORIAL_GUIDES
from extra_games import EXTRA_GAMES, EXTRA_GAME_CONTENT, register_extra_games
from action_verite import ACTION_GAME, ACTION_GAME_CONTENT, register_action_verite
from action_verite_preferences import register_action_verite_preferences
from action_verite_no_repeat import register_action_verite_no_repeat
from action_verite_answers import register_action_verite_answers
from action_verite_recovery import register_action_verite_recovery
from versus import VersusManager
from creator_routes import register_creator_routes
from sitemap_routes import register_sitemap_route
from growth import register_growth

GUIDES.update(EDITORIAL_GUIDES)
GAMES.update(EXTRA_GAMES)
GAMES.update(ACTION_GAME)
GAME_CONTENT.update(EXTRA_GAME_CONTENT)
GAME_CONTENT.update(ACTION_GAME_CONTENT)


class PlatformGames(dict):
    """Expose le catalogue complet tout en limitant le défi quotidien aux jeux scorés compatibles."""
    def keys(self):
        excluded = set(EXTRA_GAMES) | set(ACTION_GAME)
        return [slug for slug in super().keys() if slug not in excluded]


platform_games = PlatformGames(GAMES)
versus = VersusManager(app, GAMES, db_connection, current_pseudo, save_score)
# Les jeux historiques appellent core.save_score directement : on branche le
# gestionnaire de défis pour créditer le solde et enregistrer la manche active.
core_module.save_score = versus.save_score

register_platform_routes(app, platform_games, db_connection, current_pseudo)
register_extra_games(app, GAMES, current_pseudo, versus.save_score, load_words)
register_action_verite(app, GAMES, GAME_CONTENT, db_connection, current_pseudo)
register_action_verite_preferences(app, db_connection, GAME_CONTENT)
register_action_verite_no_repeat(app, db_connection)
register_action_verite_answers(app, db_connection)
# À enregistrer après les autres modules Action ou Vérité pour entourer
# leurs routes finales sans modifier leurs contrôles d'autorisation.
register_action_verite_recovery(app)
# Les gardes de défi doivent entourer les routes finales de démarrage/reprise.
versus.register_routes()
register_engagement(app, GAMES, db_connection, current_pseudo)
register_growth(app, GAMES, db_connection, current_pseudo)
register_creator_routes(app, current_pseudo)
register_sitemap_route(app, GAMES, current_pseudo)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=True)
