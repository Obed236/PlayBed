import re
from datetime import datetime, timedelta, timezone
from random import choice

from flask import abort, redirect, request, session, url_for

from action_verite import NORMAL_DARES, NORMAL_TRUTHS


PREFERENCE_TTL_HOURS = 24

# 0 = Classique, 1 = Osé, 2 = Très osé.
# Les niveaux adultes restent non graphiques : pas de description explicite
# d'actes sexuels, pas de danger, pas d'humiliation forcée et pas de contact imposé.
DARING_TRUTHS = [
    "Qui dans ce groupe te plaît le plus physiquement ?",
    "Avec qui dans ce groupe accepterais-tu le plus facilement un rendez-vous ?",
    "Qui du groupe aimerais-tu embrasser si tu devais choisir ?",
    "As-tu déjà eu des sentiments pour un ami proche sans lui dire ?",
    "As-tu déjà été attiré par quelqu’un alors que tu savais que c’était une mauvaise idée ?",
    "As-tu déjà été attiré par deux personnes en même temps ?",
    "As-tu déjà eu des sentiments pour la personne avec qui sortait un ami ?",
    "As-tu déjà embrassé quelqu’un puis regretté juste après ?",
    "As-tu déjà embrassé quelqu’un pour rendre une autre personne jalouse ?",
    "As-tu déjà rendu quelqu’un jaloux exprès ?",
    "As-tu déjà caché une relation ou un début de relation à quelqu’un ?",
    "As-tu déjà menti sur tes sentiments pour ne pas avouer qu’une personne te plaisait ?",
    "As-tu déjà fait semblant de ne pas être intéressé alors que la personne te plaisait vraiment ?",
    "Quelle est la chose la plus gênante que tu aies faite pour attirer l’attention d’une personne qui te plaisait ?",
    "As-tu déjà envoyé un message très gênant à une personne qui te plaisait puis regretté ?",
    "As-tu déjà supprimé un message juste après l’avoir envoyé parce que tu avais honte ?",
    "As-tu déjà relu plusieurs fois une discussion avec une personne qui te plaisait ?",
    "Quel est le rendez-vous le plus gênant que tu aies vécu ?",
    "Si tu devais sortir avec une personne de ce groupe, qui choisirais-tu ?",
    "As-tu déjà pensé à sortir avec quelqu’un présent dans ce groupe ?",
    "As-tu déjà eu envie d’embrasser quelqu’un sans jamais lui dire ?",
    "Quel est ton plus gros secret amoureux que tu acceptes de raconter ?",
    "As-tu déjà menti à la personne avec qui tu étais en couple au sujet d’une autre personne ?",
    "As-tu déjà regretté de ne pas avoir tenté ta chance avec quelqu’un ?",
]

DARING_DARES = [
    "Choisis une personne volontaire du groupe et dis-lui ce que tu trouves le plus attirant chez elle.",
    "Regarde une personne volontaire dans les yeux pendant 20 secondes sans détourner le regard.",
    "Choisis une personne volontaire et fais-lui une déclaration très directe comme si elle te plaisait vraiment.",
    "Choisis la personne du groupe que tu inviterais à un rendez-vous et explique pourquoi.",
    "Dis à une personne volontaire trois choses qui pourraient te faire craquer chez elle.",
    "Fais ta meilleure phrase pour séduire une personne volontaire, sans la toucher.",
    "Choisis une personne volontaire et joue une scène de premier rendez-vous très gênante pendant 20 secondes.",
    "Dis quelle personne du groupe pourrait le plus facilement te faire tomber amoureux.",
    "Choisis une personne du groupe avec qui tu formerais le meilleur couple et explique pourquoi.",
    "Improvise un message très direct que tu pourrais envoyer à une personne qui te plaît, sans l’envoyer.",
    "Fais une fausse déclaration d’amour à une personne volontaire pendant 20 secondes.",
    "Choisis une personne volontaire et dis-lui quel serait votre rendez-vous idéal.",
    "Choisis deux personnes du groupe et dis laquelle tu inviterais à un rendez-vous si tu devais choisir.",
    "Dis qui du groupe tu choisirais pour passer une soirée en tête-à-tête.",
    "Fais semblant d’avouer tes sentiments à une personne volontaire devant tout le groupe.",
]

VERY_DARING_TRUTHS = [
    "As-tu déjà eu une relation d’un soir ?",
    "As-tu déjà couché avec quelqu’un puis regretté le lendemain ?",
    "As-tu déjà eu une relation seulement physique sans vouloir être en couple ?",
    "As-tu déjà menti sur ton expérience sexuelle ?",
    "As-tu déjà caché à quelqu’un que tu avais une relation intime avec une autre personne ?",
    "As-tu déjà eu envie de coucher avec quelqu’un de ce groupe ?",
    "Si tu devais choisir une personne du groupe pour passer une nuit avec elle, qui choisirais-tu ?",
    "Qui dans ce groupe t’attire le plus sexuellement ?",
    "As-tu déjà envoyé une photo intime à quelqu’un ?",
    "As-tu déjà envoyé un message très chaud puis regretté ?",
    "As-tu déjà eu une relation intime avec quelqu’un que personne autour de toi ne connaissait ?",
    "As-tu déjà eu une relation intime avec quelqu’un puis coupé tout contact ?",
    "As-tu déjà eu envie d’une relation uniquement physique avec quelqu’un qui voulait plus ?",
    "As-tu déjà menti à ton partenaire sur ton attirance pour une autre personne ?",
    "As-tu déjà eu une aventure avec un ami ou une amie ?",
    "Quelle est la situation intime la plus gênante que tu aies vécue ?",
    "As-tu déjà eu peur que quelqu’un découvre avec qui tu avais passé la nuit ?",
    "As-tu déjà regretté d’avoir passé la nuit avec quelqu’un ?",
    "As-tu déjà eu une relation intime avec l’ex d’un ami ou d’une amie ?",
    "As-tu déjà caché une infidélité ?",
    "As-tu déjà été infidèle sans l’avouer ?",
    "As-tu déjà imaginé une nuit avec quelqu’un que tu connais bien ?",
    "Quelle personne du groupe te mettrait le plus mal à l’aise si elle te disait vouloir coucher avec toi ?",
    "Qui du groupe aurait le plus de chances de te faire craquer si vous étiez seuls tous les deux ?",
    "Quel est le plus gros secret lié à ta vie sexuelle que tu acceptes de dire ?",
    "Quelle question sur ta vie sexuelle te gênerait le plus si le groupe te la posait ?",
    "As-tu déjà fait croire que tu avais moins d’expérience intime que tu en avais vraiment ?",
    "As-tu déjà eu une relation avec quelqu’un que tu ne voulais surtout pas présenter à tes proches ?",
]

VERY_DARING_DARES = [
    "Dis quelle personne du groupe t’attire le plus sexuellement.",
    "Choisis une personne volontaire et dis-lui franchement si tu pourrais imaginer passer une nuit avec elle.",
    "Dis quelle personne du groupe tu choisirais pour une relation seulement physique.",
    "Choisis deux personnes du groupe et dis avec laquelle tu pourrais le plus facilement imaginer passer une nuit.",
    "Raconte, sans donner de détails explicites, ton moment intime le plus gênant.",
    "Dis ce qui te fait le plus craquer physiquement chez quelqu’un.",
    "Dis si, en ce moment, tu préfères une relation sérieuse ou une relation seulement physique, et pourquoi.",
    "Dis quelle personne du groupe te mettrait le plus mal à l’aise si elle t’avouait une attirance sexuelle.",
    "Choisis une personne volontaire et dis-lui si elle correspond à ton type physiquement.",
    "Dis devant le groupe quelle limite est la plus importante pour toi dans l’intimité.",
    "Dis quelle question sur ta vie sexuelle te gêne le plus, sans être obligé d’y répondre.",
    "Choisis une personne volontaire et dis-lui ce qui pourrait te faire accepter de passer une nuit avec elle.",
    "Dis avec quelle personne du groupe tu serais le plus gêné de te retrouver seul toute une nuit.",
    "Explique, sans détails explicites, ce qui rend un moment intime vraiment réussi pour toi.",
    "Dis quelle personne du groupe tu ne voudrais surtout pas entendre te dire qu’elle est attirée sexuellement par toi.",
]


def _now():
    return datetime.now(timezone.utc).isoformat()


def _pick_prompt(kind, level):
    level = 2 if level >= 2 else 1 if level == 1 else 0
    if kind == "verite":
        if level == 2:
            return choice(VERY_DARING_TRUTHS)
        if level == 1:
            return choice(DARING_TRUTHS)
        return choice(NORMAL_TRUTHS)
    if level == 2:
        return choice(VERY_DARING_DARES)
    if level == 1:
        return choice(DARING_DARES)
    return choice(NORMAL_DARES)


def register_action_verite_preferences(app, db_connection, game_content):
    def ensure_table():
        with db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS av_preferences (
                    player_token TEXT PRIMARY KEY,
                    room_code TEXT NOT NULL,
                    daring INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=PREFERENCE_TTL_HOURS)).isoformat()
            conn.execute("DELETE FROM av_preferences WHERE created_at < ?", (cutoff,))
            conn.commit()

    def memberships():
        value = session.get("av_memberships")
        return value if isinstance(value, dict) else {}

    def room_for(code):
        with db_connection() as conn:
            row = conn.execute(
                "SELECT code, status, turn_index, current_kind, current_prompt, updated_at FROM av_rooms WHERE code = ?",
                (code,),
            ).fetchone()
        return dict(row) if row else None

    def players_for(code):
        with db_connection() as conn:
            rows = conn.execute(
                "SELECT player_token, name, is_adult, player_order FROM av_players WHERE room_code = ? ORDER BY player_order ASC",
                (code,),
            ).fetchall()
        return [dict(row) for row in rows]

    def preference_level(token):
        if not token:
            return 0
        with db_connection() as conn:
            row = conn.execute("SELECT daring FROM av_preferences WHERE player_token = ?", (token,)).fetchone()
        if not row:
            return 0
        try:
            value = int(row["daring"])
        except (TypeError, ValueError):
            return 0
        return 2 if value >= 2 else 1 if value == 1 else 0

    def save_preference(code, token, level):
        level = 2 if level >= 2 else 1 if level == 1 else 0
        now = _now()
        with db_connection() as conn:
            conn.execute("DELETE FROM av_preferences WHERE player_token = ?", (token,))
            conn.execute(
                "INSERT INTO av_preferences (player_token, room_code, daring, created_at) VALUES (?, ?, ?, ?)",
                (token, code, level, now),
            )
            conn.execute("UPDATE av_rooms SET updated_at = ? WHERE code = ?", (now, code))
            conn.commit()

    def requested_level(mode):
        return {"classic": 0, "daring": 1, "very_daring": 2}.get(mode, -1)

    ensure_table()

    content = game_content.get("action-verite")
    if content:
        content["objective"] = (
            "Action ou Vérité se joue de 2 à 5 personnes. Chaque majeur choisit pour lui-même entre Classique, Osé et Très osé. "
            "Très osé est réservé aux adultes et contient des questions très intimes, y compris sur la vie sexuelle, sans détails graphiques. "
            "Un joueur peut toujours passer une question ou une action."
        )
        content["rules"] = [
            "Le groupe doit contenir entre 2 et 5 joueurs.",
            "Chaque joueur indique son prénom ou pseudo et son âge avant de commencer.",
            "Chaque majeur choisit pour lui-même : Classique, Osé ou Très osé.",
            "Classique reste sur les questions et actions normales.",
            "Osé pose des questions plus personnelles et gênantes.",
            "Très osé peut aborder la vie intime et sexuelle avec des mots simples, sans détails graphiques.",
            "Un joueur peut toujours passer si une question ou une action va trop loin pour lui.",
            "Si au moins un joueur est mineur, toute la partie reste en Classique.",
            "À chaque tour, le joueur concerné choisit Action ou Vérité.",
        ]

    original_choose = app.view_functions.get("av_room_choose")
    if original_choose:
        def choose_with_personal_preference(code):
            response = original_choose(code)
            if not re.fullmatch(r"\d{4}", code):
                return response
            room = room_for(code)
            players = players_for(code) if room else []
            if not room or not players or not room.get("current_prompt"):
                return response
            current = players[int(room["turn_index"]) % len(players)]
            all_adults = all(bool(player["is_adult"]) for player in players)
            level = preference_level(current["player_token"]) if all_adults and bool(current["is_adult"]) else 0
            kind = room.get("current_kind")
            if kind not in {"action", "verite"}:
                return response
            now = _now()
            with db_connection() as conn:
                conn.execute(
                    "UPDATE av_rooms SET current_prompt = ?, updated_at = ? WHERE code = ?",
                    (_pick_prompt(kind, level), now, code),
                )
                conn.commit()
            return response

        app.view_functions["av_room_choose"] = choose_with_personal_preference

    @app.context_processor
    def inject_action_verite_preferences():
        empty = {
            "av_level_by_token": {},
            "av_level_available": False,
            "av_member_level": 0,
            "av_daring_by_token": {},
            "av_daring_available": False,
            "av_member_daring": False,
        }
        if request.endpoint != "av_room":
            return empty
        code = ((request.view_args or {}).get("code") or "").strip()
        token = memberships().get(code)
        if not re.fullmatch(r"\d{4}", code) or not token:
            return empty
        players = players_for(code)
        mapping = {player["player_token"]: preference_level(player["player_token"]) for player in players}
        available = bool(players) and all(bool(player["is_adult"]) for player in players)
        return {
            "av_level_by_token": mapping,
            "av_level_available": available,
            "av_member_level": int(mapping.get(token, 0)),
            "av_daring_by_token": mapping,
            "av_daring_available": available,
            "av_member_daring": bool(mapping.get(token, 0)),
        }

    @app.route("/action-verite/classe/<code>/preference", methods=["POST"])
    def av_room_preference(code):
        if not re.fullmatch(r"\d{4}", code):
            abort(404)
        room = room_for(code)
        token = memberships().get(code)
        players = players_for(code) if room else []
        if not room or room["status"] != "waiting" or not token:
            abort(403)
        member = next((player for player in players if player["player_token"] == token), None)
        if not member:
            abort(403)
        mode = (request.form.get("content_mode") or "classic").strip().lower()
        level = requested_level(mode)
        if level < 0:
            abort(400)
        save_preference(code, token, level if bool(member["is_adult"]) else 0)
        return redirect(url_for("av_room", code=code))

    @app.after_request
    def save_join_and_local_preferences(response):
        path = request.path

        if request.method == "POST" and path in {
            "/action-verite/classe/creer",
            "/action-verite/classe/rejoindre",
        } and 300 <= response.status_code < 400:
            location = response.headers.get("Location", "")
            match = re.search(r"/action-verite/classe/(\d{4})(?:$|[?#])", location)
            if match:
                code = match.group(1)
                token = memberships().get(code)
                try:
                    age = int(request.form.get("age", ""))
                except (TypeError, ValueError):
                    age = 0
                level = requested_level((request.form.get("content_mode") or "classic").strip().lower())
                if token:
                    save_preference(code, token, level if age >= 18 and level >= 0 else 0)

        if request.method == "POST" and path == "/action-verite/local" and 300 <= response.status_code < 400:
            action = (request.form.get("action") or "").strip().lower()
            state = session.get("av_local")
            if isinstance(state, dict) and state.get("players"):
                if action == "setup":
                    modes = request.form.getlist("player_mode")
                    for index, player in enumerate(state["players"]):
                        requested = modes[index] if index < len(modes) else "classic"
                        level = requested_level(requested)
                        player["level"] = level if bool(player.get("is_adult")) and level >= 0 else 0
                        player["daring"] = player["level"] > 0
                    session["av_local"] = state
                elif action == "choose" and state.get("prompt"):
                    players = state["players"]
                    current = players[int(state.get("turn_index", 0)) % len(players)]
                    level = int(current.get("level", 1 if current.get("daring") else 0)) if state.get("adult_mode") else 0
                    kind = state.get("kind")
                    if kind in {"action", "verite"}:
                        state["prompt"] = _pick_prompt(kind, level)
                        session["av_local"] = state

        return response
