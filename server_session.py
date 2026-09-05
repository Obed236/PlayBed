import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from flask.json.tag import TaggedJSONSerializer
from flask.sessions import SessionInterface, SessionMixin
from itsdangerous import BadSignature, Signer
from werkzeug.datastructures import CallbackDict


SID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,128}$")


class ServerSideSession(CallbackDict, SessionMixin):
    def __init__(self, initial=None, sid=None, new=False):
        def on_update(session):
            session.modified = True

        super().__init__(initial, on_update)
        self.sid = sid
        self.new = new
        self.modified = False


class DatabaseSessionInterface(SessionInterface):
    serializer = TaggedJSONSerializer()

    def __init__(self, db_connection):
        self.db_connection = db_connection
        self._schema_ready = False

    def _ensure_schema(self):
        if self._schema_ready:
            return
        with self.db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS web_sessions (
                    sid TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()
        self._schema_ready = True

    @staticmethod
    def _now():
        return datetime.now(timezone.utc)

    @staticmethod
    def _new_sid():
        return secrets.token_urlsafe(32)

    def _signer(self, app):
        if not app.secret_key:
            return None
        return Signer(app.secret_key, salt="playbed-server-session-v1")

    def _decode_sid(self, app, value):
        if not value:
            return None
        signer = self._signer(app)
        if signer is None:
            return None
        try:
            sid = signer.unsign(value).decode("utf-8")
        except (BadSignature, UnicodeDecodeError):
            return None
        return sid if SID_PATTERN.fullmatch(sid) else None

    def _encode_sid(self, app, sid):
        signer = self._signer(app)
        if signer is None:
            raise RuntimeError("SECRET_KEY requis pour signer l'identifiant de session.")
        return signer.sign(sid.encode("utf-8")).decode("utf-8")

    def open_session(self, app, request):
        cookie_name = self.get_cookie_name(app)
        sid = self._decode_sid(app, request.cookies.get(cookie_name))
        if not sid:
            return ServerSideSession(sid=self._new_sid(), new=True)

        try:
            self._ensure_schema()
            with self.db_connection() as conn:
                row = conn.execute(
                    "SELECT data, expires_at FROM web_sessions WHERE sid = ?",
                    (sid,),
                ).fetchone()
            if not row:
                return ServerSideSession(sid=self._new_sid(), new=True)

            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= self._now():
                try:
                    with self.db_connection() as conn:
                        conn.execute("DELETE FROM web_sessions WHERE sid = ?", (sid,))
                        conn.commit()
                except Exception:
                    app.logger.exception("Impossible de supprimer une session expirée")
                return ServerSideSession(sid=self._new_sid(), new=True)

            data = self.serializer.loads(row["data"])
            if not isinstance(data, dict):
                data = {}
            return ServerSideSession(data, sid=sid, new=False)
        except Exception:
            app.logger.exception("Impossible de charger la session serveur")
            return ServerSideSession(sid=self._new_sid(), new=True)

    def save_session(self, app, session, response):
        cookie_name = self.get_cookie_name(app)
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)
        secure = self.get_cookie_secure(app)
        httponly = self.get_cookie_httponly(app)
        samesite = self.get_cookie_samesite(app)

        if not session:
            if getattr(session, "sid", None):
                try:
                    self._ensure_schema()
                    with self.db_connection() as conn:
                        conn.execute("DELETE FROM web_sessions WHERE sid = ?", (session.sid,))
                        conn.commit()
                except Exception:
                    app.logger.exception("Impossible de supprimer la session serveur")
            response.delete_cookie(
                cookie_name,
                domain=domain,
                path=path,
                secure=secure,
                httponly=httponly,
                samesite=samesite,
            )
            response.vary.add("Cookie")
            return

        if not session.modified and not session.permanent and not session.new:
            return

        now = self._now()
        if session.permanent:
            expires = now + app.permanent_session_lifetime
            cookie_expires = expires
        else:
            ttl_hours = int(app.config.get("SESSION_SERVER_TTL_HOURS", 24))
            expires = now + timedelta(hours=max(1, ttl_hours))
            cookie_expires = None

        payload = self.serializer.dumps(dict(session))
        sid = getattr(session, "sid", None) or self._new_sid()
        session.sid = sid

        try:
            self._ensure_schema()
            with self.db_connection() as conn:
                existing = conn.execute(
                    "SELECT sid FROM web_sessions WHERE sid = ?",
                    (sid,),
                ).fetchone()
                if existing:
                    conn.execute(
                        "UPDATE web_sessions SET data = ?, expires_at = ?, updated_at = ? WHERE sid = ?",
                        (payload, expires.isoformat(), now.isoformat(), sid),
                    )
                else:
                    conn.execute(
                        "INSERT INTO web_sessions (sid, data, expires_at, updated_at) VALUES (?, ?, ?, ?)",
                        (sid, payload, expires.isoformat(), now.isoformat()),
                    )

                if secrets.randbelow(100) == 0:
                    conn.execute(
                        "DELETE FROM web_sessions WHERE expires_at < ?",
                        (now.isoformat(),),
                    )
                conn.commit()
        except Exception:
            app.logger.exception("Impossible d'enregistrer la session serveur")
            return

        response.set_cookie(
            cookie_name,
            self._encode_sid(app, sid),
            expires=cookie_expires,
            httponly=httponly,
            secure=secure,
            samesite=samesite,
            path=path,
            domain=domain,
        )
        response.vary.add("Cookie")


def register_server_side_sessions(app, db_connection):
    """Store all Flask session data in PostgreSQL/SQLite instead of the browser cookie."""
    app.session_interface = DatabaseSessionInterface(db_connection)

    secure_cookie = bool(app.config.get("SESSION_COOKIE_SECURE", False))
    app.config["SESSION_COOKIE_NAME"] = (
        "__Host-playbed_session" if secure_cookie else "playbed_session_dev"
    )
    app.config["SESSION_COOKIE_PATH"] = "/"
    app.config["SESSION_COOKIE_DOMAIN"] = None
    app.config.setdefault("SESSION_SERVER_TTL_HOURS", int(os.environ.get("PLAYBED_SESSION_TTL_HOURS", "24")))
