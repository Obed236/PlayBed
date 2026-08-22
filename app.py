import os

from flask import redirect, render_template, request, session, url_for

import core as core_module
from core import app, GAMES, db_connection, current_pseudo, init_db, save_score, load_words, load_quiz_questions
from engagement import register_engagement
from platform_routes import register_platform_routes, GUIDES, GAME_CONTENT
from editorial_guides import EDITORIAL_GUIDES
from extra_games import EXTRA_GAMES, EXTRA_GAME_CONTENT, register_extra_games
from chrono_variation import register_variable_chrono
from action_verite import ACTION_GAME, ACTION_GAME_CONTENT, register_action_verite
from action_verite_preferences import register_action_verite_preferences
from action_verite_no_repeat import register_action_verite_no_repeat
from action_verite_answers import register_action_verite_answers
from action_verite_recovery import register_action_verite_recovery
from versus import VersusManager
from creator_routes import register_creator_routes
from sitemap_routes import register_sitemap_route
from growth import register_growth
from admin_routes import register_admin_routes

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

# Le hook historique initialisait PostgreSQL avant absolument chaque requête,
# y compris les pages légales, robots.txt et le sitemap. On le remplace par
# une initialisation ciblée afin que les contenus publics restent accessibles
# même pendant une indisponibilité momentanée de la base.
for scope, functions in list(app.before_request_funcs.items()):
    app.before_request_funcs[scope] = [
        function for function in functions
        if function is not core_module.ensure_database
    ]

DATABASE_OPTIONAL_ENDPOINTS = {
    "static",
    "home",
    "about_page",
    "how_to_play_page",
    "faq_page",
    "privacy_page",
    "terms_page",
    "ads_txt",
    "robots_txt",
    "sitemap_xml",
    "health",
    "platform_game_detail",
    "platform_guides",
    "platform_guide_detail",
    "platform_news",
    "platform_contact",
    "platform_legal",
    "creator_page",
    "site_map_page",
    "pwa_manifest",
    "pwa_service_worker",
}


@app.before_request
def ensure_database_for_dynamic_routes():
    endpoint = request.endpoint
    if endpoint is None or endpoint in DATABASE_OPTIONAL_ENDPOINTS:
        return None
    init_db()
    return None


@app.after_request
def isolate_adult_game_from_indexing(response):
    path = request.path or ""
    if path.startswith("/action-verite") or path.startswith("/jeux/action-verite"):
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


# La page d'accueil affiche un compteur de scores, mais ce compteur ne doit
# jamais rendre tout le site inaccessible si PostgreSQL répond mal.
_original_home = app.view_functions.get("home")
if _original_home:
    def resilient_home():
        try:
            return _original_home()
        except Exception:
            app.logger.exception("Base de données indisponible sur la page d'accueil")
            return render_template(
                "index.html",
                games=GAMES,
                pseudo=current_pseudo(),
                total_scores=0,
            )

    app.view_functions["home"] = resilient_home


versus = VersusManager(app, GAMES, db_connection, current_pseudo, save_score)
# Les jeux historiques appellent core.save_score directement : on branche le
# gestionnaire de défis pour créditer le solde et enregistrer la manche active.
core_module.save_score = versus.save_score

register_platform_routes(app, platform_games, db_connection, current_pseudo)
register_extra_games(app, GAMES, current_pseudo, versus.save_score, load_words)
register_variable_chrono(app, GAMES, GAME_CONTENT, versus.save_score, current_pseudo)
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
register_admin_routes(app, GAMES, db_connection, current_pseudo, core_module)

# Le module admin possède un garde générique. On le remplace ici par une
# version plus légère qui ne recrée pas le schéma admin à chaque requête.
for scope, functions in list(app.before_request_funcs.items()):
    app.before_request_funcs[scope] = [
        function for function in functions
        if getattr(function, "__name__", "") != "enforce_admin_controls"
    ]


@app.before_request
def apply_admin_runtime_controls():
    if request.path.startswith("/admin"):
        return None

    endpoint = request.endpoint
    if endpoint in {
        "static",
        "health",
        "robots_txt",
        "ads_txt",
        "sitemap_xml",
        "pwa_manifest",
        "pwa_service_worker",
    }:
        return None

    # Les pages publiques historiquement indépendantes de PostgreSQL restent
    # indépendantes. La page d'accueil est la seule exception, car elle lit
    # déjà le compteur de scores avec une stratégie de repli.
    if endpoint in DATABASE_OPTIONAL_ENDPOINTS and endpoint != "home":
        return None

    game_slug = None
    if request.view_args:
        game_slug = request.view_args.get("game")
    if not game_slug:
        game_slug = {
            "/arcade/calcul": "calcul",
            "/arcade/mot-melange": "melange",
            "/arcade/suite-logique": "suite",
            "/arcade/pair-impair": "pair",
            "/arcade/chrono-10": "chrono",
        }.get(request.path)
    if not game_slug and (
        request.path.startswith("/action-verite")
        or request.path.startswith("/jeux/action-verite")
    ):
        game_slug = "action-verite"

    try:
        maintenance_enabled = False
        maintenance_message = "PlayBed est momentanément en maintenance. Reviens dans quelques instants."
        blocked = False
        disabled_game = False
        pseudo = current_pseudo()

        with db_connection() as conn:
            maintenance_row = conn.execute(
                "SELECT value FROM admin_settings WHERE key = ?",
                ("maintenance_mode",),
            ).fetchone()
            maintenance_enabled = bool(maintenance_row and maintenance_row["value"] == "1")

            if maintenance_enabled:
                message_row = conn.execute(
                    "SELECT value FROM admin_settings WHERE key = ?",
                    ("maintenance_message",),
                ).fetchone()
                if message_row and message_row["value"]:
                    maintenance_message = message_row["value"]

            if pseudo:
                blocked = bool(conn.execute(
                    "SELECT pseudo FROM admin_blocked_pseudos WHERE LOWER(pseudo) = LOWER(?)",
                    (pseudo,),
                ).fetchone())

            if game_slug in GAMES:
                game_row = conn.execute(
                    "SELECT value FROM admin_settings WHERE key = ?",
                    (f"game_enabled:{game_slug}",),
                ).fetchone()
                disabled_game = bool(game_row and game_row["value"] == "0")

        if maintenance_enabled:
            return render_template("maintenance.html", message=maintenance_message), 503

        if blocked:
            session.pop("pseudo", None)
            session.pop("current_game", None)
            return redirect(url_for("home", pseudo_blocked=1))

        if disabled_game:
            return render_template(
                "game_disabled.html",
                meta=GAMES[game_slug],
                pseudo=current_pseudo(),
            ), 503
    except Exception:
        # Si les tables admin n'existent pas encore ou si PostgreSQL répond mal,
        # les contrôles admin ne doivent pas rendre PlayBed inaccessible.
        app.logger.exception("Contrôles administrateur temporairement indisponibles")

    return None


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=True)
