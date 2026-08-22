import re
from datetime import datetime, timedelta, timezone
from random import choice

from flask import abort, redirect, request, session, url_for

from action_verite import NORMAL_DARES, NORMAL_TRUTHS


PREFERENCE_TTL_HOURS = 24

# Niveau « Osé » : des questions plus personnelles et plus gênantes,
# avec des mots simples. Pas de contenu explicite, pas de danger,
# pas d'humiliation forcée et pas de contact imposé.
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
    "As-tu déjà regardé très longtemps le profil d’une personne qui te plaisait sans lui parler ?",
    "Quel est le plus gros mensonge que tu aies raconté pour éviter un rendez-vous ?",
    "Quel est le rendez-vous le plus gênant que tu aies vécu ?",
    "Quelle personne présente ici pourrait le plus facilement te faire craquer ?",
    "Quelle personne du groupe serait la plus dangereuse pour ton cœur ?",
    "Si tu devais sortir avec une personne de ce groupe, qui choisirais-tu ?",
    "Si tu devais passer une soirée en tête-à-tête avec une personne du groupe, qui choisirais-tu ?",
    "Qui du groupe serait, selon toi, le meilleur partenaire pour toi ?",
    "As-tu déjà pensé à sortir avec quelqu’un présent dans ce groupe ?",
    "As-tu déjà eu envie d’embrasser quelqu’un sans jamais lui dire ?",
    "Quelle est la chose la plus folle que tu aies faite par amour ou par attirance ?",
    "Quel est ton plus gros secret amoureux que tu acceptes de raconter ?",
    "As-tu déjà menti à la personne avec qui tu étais en couple au sujet d’une autre personne ?",
    "As-tu déjà parlé à quelqu’un juste parce que tu le trouvais très beau ou très belle ?",
    "Qui est la dernière personne à laquelle tu as pensé avant de dormir hier soir ?",
    "Quelle personne de ton passé pourrais-tu revoir si elle te le demandait aujourd’hui ?",
    "As-tu déjà regretté d’avoir quitté quelqu’un ?",
    "As-tu déjà regretté de ne pas avoir tenté ta chance avec quelqu’un ?",
    "Quelle est la première chose que tu regardes chez une personne qui te plaît ?",
    "Quelle est ta plus grande faiblesse quand quelqu’un te plaît vraiment ?",
    "Qu’est-ce qui peut te faire tomber amoureux très vite ?",
    "As-tu déjà dit que tu ne voulais rien de sérieux alors que tu avais peur de t’attacher ?",
    "Quelle personne du groupe serait la plus difficile à oublier après une relation ?",
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
    "Dis devant le groupe quel type de personne te fait le plus craquer.",
    "Choisis deux personnes du groupe et dis laquelle tu inviterais à un rendez-vous si tu devais choisir.",
    "Fais semblant de rencontrer pour la première fois une personne volontaire qui te plaît beaucoup.",
    "Choisis une personne volontaire et dis-lui le compliment le plus gênant que tu oses lui faire.",
    "Dis qui du groupe tu choisirais pour passer une soirée en tête-à-tête.",
    "Choisis une personne volontaire et explique en 20 secondes pourquoi elle pourrait te plaire.",
    "Fais semblant d’avouer tes sentiments à une personne volontaire devant tout le groupe.",
    "Dis quelle personne du groupe serait, selon toi, la plus difficile à oublier après une relation.",
]


def _now():
    return datetime.now(timezone.utc).isoformat()


def _pick_prompt(kind, daring):
    if kind == "verite":
        return choice(DARING_TRUTHS if daring else NORMAL_TRUTHS)
    return choice(DARING_DARES if daring else NORMAL_DARES)


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

    def preference_for(token):
        if not token:
            return False
        with db_connection() as conn:
            row = conn.execute("SELECT daring FROM av_preferences WHERE player_token = ?", (token,)).fetchone()
        return bool(row and row["daring"])

    def save_preference(code, token, daring):
        now = _now()
        with db_connection() as conn:
            conn.execute("DELETE FROM av_preferences WHERE player_token = ?", (token,))
            conn.execute(
                "INSERT INTO av_preferences (player_token, room_code, daring, created_at) VALUES (?, ?, ?, ?)",
                (token, code, 1 if daring else 0, now),
            )
            conn.execute("UPDATE av_rooms SET updated_at = ? WHERE code = ?", (now, code))
            conn.commit()

    ensure_table()

    content = game_content.get("action-verite")
    if content:
        content["objective"] = (
            "Action ou Vérité se joue de 2 à 5 personnes. Chaque joueur indique son âge puis, s’il est majeur, "
            "choisit pour lui-même entre Classique et Osé. Le niveau Osé contient des questions plus personnelles "
            "et plus gênantes. Un joueur peut toujours passer une question ou une action s’il ne veut pas répondre."
        )
        content["rules"] = [
            "Le groupe doit contenir entre 2 et 5 joueurs.",
            "Chaque joueur indique son prénom ou pseudo et son âge avant de commencer.",
            "Chaque joueur majeur choisit pour lui-même : Classique ou Osé.",
            "Un joueur en Classique reçoit seulement les questions et actions normales.",
            "Un joueur en Osé reçoit des questions plus personnelles et plus gênantes.",
            "Un joueur peut toujours passer si une question ou une action va trop loin pour lui.",
            "Si au moins un joueur est mineur, toute la partie reste en Classique.",
            "À chaque tour, le joueur concerné choisit Action ou Vérité.",
            "Une classe privée peut être créée pour jouer à distance avec un code à 4 chiffres.",
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
            daring = all_adults and bool(current["is_adult"]) and preference_for(current["player_token"])
            kind = room.get("current_kind")
            if kind not in {"action", "verite"}:
                return response
            now = _now()
            with db_connection() as conn:
                conn.execute(
                    "UPDATE av_rooms SET current_prompt = ?, updated_at = ? WHERE code = ?",
                    (_pick_prompt(kind, daring), now, code),
                )
                conn.commit()
            return response

        app.view_functions["av_room_choose"] = choose_with_personal_preference

    @app.context_processor
    def inject_action_verite_preferences():
        if request.endpoint != "av_room":
            return {
                "av_daring_by_token": {},
                "av_daring_available": False,
                "av_member_daring": False,
            }
        code = ((request.view_args or {}).get("code") or "").strip()
        token = memberships().get(code)
        if not re.fullmatch(r"\d{4}", code) or not token:
            return {
                "av_daring_by_token": {},
                "av_daring_available": False,
                "av_member_daring": False,
            }
        players = players_for(code)
        mapping = {player["player_token"]: preference_for(player["player_token"]) for player in players}
        return {
            "av_daring_by_token": mapping,
            "av_daring_available": bool(players) and all(bool(player["is_adult"]) for player in players),
            "av_member_daring": bool(mapping.get(token)),
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
        if mode not in {"classic", "daring"}:
            abort(400)
        save_preference(code, token, bool(member["is_adult"]) and mode == "daring")
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
                mode = (request.form.get("content_mode") or "classic").strip().lower()
                if token:
                    save_preference(code, token, age >= 18 and mode == "daring")

        if request.method == "POST" and path == "/action-verite/local" and 300 <= response.status_code < 400:
            action = (request.form.get("action") or "").strip().lower()
            state = session.get("av_local")
            if isinstance(state, dict) and state.get("players"):
                if action == "setup":
                    modes = request.form.getlist("player_mode")
                    for index, player in enumerate(state["players"]):
                        requested = modes[index] if index < len(modes) else "classic"
                        player["daring"] = bool(player.get("is_adult")) and requested == "daring"
                    session["av_local"] = state
                elif action == "choose" and state.get("prompt"):
                    players = state["players"]
                    current = players[int(state.get("turn_index", 0)) % len(players)]
                    daring = bool(state.get("adult_mode")) and bool(current.get("is_adult")) and bool(current.get("daring"))
                    kind = state.get("kind")
                    if kind in {"action", "verite"}:
                        state["prompt"] = _pick_prompt(kind, daring)
                        session["av_local"] = state

        return response
