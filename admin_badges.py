import os

from flask import g

from admin_linking import register_admin_linking


def register_admin_badges(app, db_connection):
    """Expose active PlayBed admin identities to public/admin templates."""

    # Register the explicit admin <-> player pseudo association first.
    register_admin_linking(app, db_connection)

    def load_admin_identities():
        cached = getattr(g, "playbed_admin_identities", None)
        if cached is not None:
            return cached

        identities = {}
        primary_username = os.environ.get("PLAYBED_ADMIN_USERNAME", "").strip()

        try:
            with db_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS admin_player_links (
                        admin_key TEXT PRIMARY KEY,
                        player_pseudo TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                conn.commit()

                links = conn.execute(
                    "SELECT admin_key, player_pseudo FROM admin_player_links"
                ).fetchall()
                link_map = {
                    row["admin_key"]: (row["player_pseudo"] or "").strip()
                    for row in links
                    if (row["player_pseudo"] or "").strip()
                }

                rows = conn.execute(
                    "SELECT id, username, role, active FROM admin_accounts WHERE active = 1"
                ).fetchall()
        except Exception:
            # Le site doit continuer à fonctionner même si les tables admin
            # ne sont pas encore disponibles pendant un déploiement.
            link_map = {}
            rows = []

        if primary_username:
            player_pseudo = link_map.get("environment") or primary_username
            identities[player_pseudo.casefold()] = {
                "username": primary_username,
                "player_pseudo": player_pseudo,
                "role": "super_admin",
                "label": "Super-admin",
                "icon": "👑",
            }

        for row in rows:
            username = (row["username"] or "").strip()
            if not username:
                continue
            role = row["role"] or "admin"
            player_pseudo = link_map.get(f"account:{row['id']}") or username
            identities[player_pseudo.casefold()] = {
                "username": username,
                "player_pseudo": player_pseudo,
                "role": role,
                "label": "Super-admin" if role == "super_admin" else "Admin",
                "icon": "👑" if role == "super_admin" else "🛡️",
            }

        g.playbed_admin_identities = identities
        return identities

    def admin_identity(pseudo):
        value = (str(pseudo) if pseudo is not None else "").strip()
        if not value:
            return None
        return load_admin_identities().get(value.casefold())

    @app.context_processor
    def inject_admin_identity_helpers():
        return {"admin_identity": admin_identity}
