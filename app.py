import os

from core import app, GAMES, db_connection, current_pseudo, init_db
from platform_routes import register_platform_routes

register_platform_routes(app, GAMES, db_connection, current_pseudo)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=True)
