import re
from datetime import datetime, timedelta, timezone
from random import choice

from flask import abort, redirect, request, session, url_for

from action_verite import NORMAL_DARES, NORMAL_TRUTHS


PREFERENCE_TTL_HOURS = 24

# Niveau « osé » : volontairement plus gênant et intime, mais sans contenu
# sexuel explicite, défi dangereux, humiliation forcée ou contact imposé.
DARING_TRUTHS = [
    "Qui dans ce groupe trouves-tu le plus séduisant ?",
    "Avec qui dans ce groupe accepterais-tu le plus facilement un rendez-vous ?",
    "As-tu déjà eu un crush sur un ami proche sans lui dire ?",
    "Quelle est la chose la plus gênante que tu aies faite pour attirer l’attention d’un crush ?",
    "As-tu déjà envoyé un message de flirt puis regretté immédiatement ?",
    "Quel est ton plus gros turn-off chez quelqu’un qui te plaît ?",
    "As-tu déjà fait semblant de ne pas être intéressé alors que tu l’étais vraiment ?",
    "Quelle personne de ton entourage t’a déjà attiré alors que tu savais que c’était une mauvaise idée ?",
    "As-tu déjà été attiré par deux personnes en même temps ?",
    "Quel est le plus gros mensonge que tu aies raconté pour éviter un rendez-vous ?",
    "As-tu déjà stalké le profil d’un crush beaucoup plus longtemps que tu ne veux l’avouer ?",
    "Quelle est la première chose qui peut te faire craquer chez quelqu’un ?",
    "Quel est le compliment le plus audacieux qu’on t’ait déjà fait ?",
    "As-tu déjà eu un crush sur quelqu’un présent dans cette pièce ou cette classe ?",
    "Si tu devais choisir, avec qui du groupe imaginerais-tu le plus facilement un baiser ?",
    "Quel est le rendez-vous le plus gênant que tu aies vécu ?",
    "As-tu déjà rendu quelqu’un jaloux volontairement ?",
    "Quelle conversation romantique aimerais-tu pouvoir effacer de ta mémoire ?",
    "As-tu déjà gardé des sentiments pour quelqu’un beaucoup trop longtemps ?",
    "Qui est la dernière personne à laquelle tu as pensé avant de dormir hier ?",
    "As-tu déjà relu plusieurs fois une conversation avec quelqu’un qui te plaît ?",
    "Quelle est ta plus grande faiblesse quand quelqu’un te plaît vraiment ?",
    "As-tu déjà dit « je ne veux rien de sérieux » alors que tu avais peur de t’attacher ?",
    "Quelle personne du groupe serait, selon toi, la plus dangereuse pour ton cœur ?",
]

DARING_DARES = [
    "Choisis un joueur volontaire et fais-lui un compliment vraiment charmeur.",
    "Regarde un joueur volontaire dans les yeux pendant 15 secondes sans rire.",
    "Fais ta meilleure phrase de drague à un joueur volontaire, sans le toucher.",
    "Montre ta meilleure technique de séduction en 20 secondes, sans contact physique.",
    "Choisis la personne du groupe avec qui tu formerais le meilleur couple fictif et explique pourquoi.",
    "Improvise un message de flirt très audacieux que tu n’enverras à personne.",
    "Fais une fausse déclaration de crush à un joueur volontaire pendant 15 secondes.",
    "Dis trois qualités qui pourraient vraiment te faire tomber amoureux de quelqu’un.",
    "Imite ta réaction si ton crush t’envoyait maintenant : « tu me manques ».",
    "Fais un compliment charmeur différent à deux joueurs volontaires.",
    "Joue une scène de premier rendez-vous très gênante avec un joueur volontaire pendant 20 secondes.",
    "Décris ton rendez-vous idéal comme si tu essayais de convaincre ton crush de venir.",
    "Laisse le groupe choisir un prénom fictif et invente une phrase de flirt que tu pourrais lui envoyer.",
    "Dis quel type de personnalité te ferait craquer en trois critères, sans citer de nom.",
    "Choisis un joueur volontaire et improvisez une scène où vous vous rencontrez pour la première fois dans un film romantique.",
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

    # Met à jour la page de règles sans modifier le moteur historique.
    content = game_content.get("action-verite")
    if content:
        content["objective"] = (
            "Action ou Vérité se joue de 2 à 5 personnes. Chaque joueur indique son âge puis, s’il est majeur, "
            "choisit individuellement entre le niveau Classique et le niveau Osé. Les propositions osées ne sont "
            "servies qu’aux joueurs majeurs qui les ont acceptées et uniquement dans un groupe entièrement majeur."
        )
        content["rules"] = [
            "Le groupe doit contenir entre 2 et 5 joueurs.",
            "Chaque joueur indique son prénom ou pseudo et son âge avant de commencer.",
            "Chaque joueur majeur choisit pour lui-même : Classique ou Osé.",
            "Un joueur ayant choisi Classique reçoit uniquement les questions et actions normales.",
            "Un joueur ayant choisi Osé peut recevoir des propositions plus gênantes et suggestives, sans contenu explicite ni action dangereuse.",
            "Si au moins un joueur est mineur, toute la partie reste automatiquement en mode Classique.",
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

        # Après création ou arrivée dans une classe, l’ancienne route a déjà
        # créé l’adhésion de session. On rattache alors le vote au joueur.
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

        # En local, le moteur historique construit la partie puis on ajoute le
        # vote individuel de chacun à l’état de session.
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
