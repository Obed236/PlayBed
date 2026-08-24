import os

from flask import g


def register_admin_badges(app, db_connection):
    """Expose active PlayBed admin identities to public/admin templates."""

    def load_admin_identities():
        cached = getattr(g, "playbed_admin_identities", None)
        if cached is not None:
            return cached

        identities = {}
        primary_username = os.environ.get("PLAYBED_ADMIN_USERNAME", "").strip()
        if primary_username:
            identities[primary_username.casefold()] = {
                "username": primary_username,
                "role": "super_admin",
                "label": "Super-admin",
                "icon": "👑",
            }

        try:
            with db_connection() as conn:
                rows = conn.execute(
                    "SELECT username, role, active FROM admin_accounts WHERE active = 1"
                ).fetchall()
            for row in rows:
                username = (row["username"] or "").strip()
                if not username:
                    continue
                role = row["role"] or "admin"
                identities[username.casefold()] = {
                    "username": username,
                    "role": role,
                    "label": "Super-admin" if role == "super_admin" else "Admin",
                    "icon": "👑" if role == "super_admin" else "🛡️",
                }
        except Exception:
            # Le site doit continuer à fonctionner même si la table admin
            # n'est pas encore disponible pendant un déploiement.
            pass

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
