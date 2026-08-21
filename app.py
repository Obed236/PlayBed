import os

from core import app, GAMES, db_connection, current_pseudo, init_db
from engagement import register_engagement
from growth import register_growth
from platform_routes import register_platform_routes, GUIDES
from editorial_guides import EDITORIAL_GUIDES
from creator_routes import register_creator_routes
from sitemap_routes import register_sitemap_route

GUIDES.update(EDITORIAL_GUIDES)

register_platform_routes(app, GAMES, db_connection, current_pseudo)
register_engagement(app, GAMES, db_connection, current_pseudo)
register_growth(app, GAMES, db_connection, current_pseudo)
register_creator_routes(app, current_pseudo)
register_sitemap_route(app, GAMES, current_pseudo)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=True)
