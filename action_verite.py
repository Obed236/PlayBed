import re
import secrets
from datetime import datetime, timedelta, timezone
from random import choice

from flask import abort, jsonify, redirect, render_template, request, session, url_for

ACTION_GAME = {
    "action-verite": {
        "name": "Action ou Vérité",
        "emoji": "🎭",
        "description": "Joue à 2 à 5 personnes sur un seul téléphone ou dans une classe privée à distance avec un code à 4 chiffres. Le contenu s’adapte automatiquement à l’âge du groupe.",
        "tag": "Groupe",
    }
}

ACTION_GAME_CONTENT = {
    "action-verite": {
        "headline": "Un jeu de groupe qui s’adapte à l’âge des joueurs.",
        "objective": "Action ou Vérité se joue de 2 à 5 personnes. Chaque joueur indique son âge au début afin que PlayBed choisisse un niveau de contenu adapté. Si au moins un joueur a moins de 18 ans, seules les questions et actions grand public sont proposées. Si tous les joueurs sont majeurs, des propositions plus audacieuses mais toujours non dangereuses et non explicites peuvent apparaître.",
        "rules": [
            "Le groupe doit contenir entre 2 et 5 joueurs.",
            "Chaque joueur indique son prénom ou pseudo et son âge avant de commencer.",
            "À chaque tour, le joueur concerné choisit Action ou Vérité.",
            "S’il y a au moins un mineur dans le groupe, le mode reste automatiquement grand public.",
            "Si tous les joueurs ont 18 ans ou plus, le jeu peut mélanger contenu classique et contenu 18+ léger.",
            "Une classe privée peut être créée pour jouer à distance avec un code à 4 chiffres.",
        ],
        "scoring": "Action ou Vérité n’utilise pas de score et n’influence pas les classements PlayBed.",
        "tips": [
            "Personne n’est obligé d’accepter une action ou de répondre à une question qui le met mal à l’aise.",
            "Le créateur d’une classe privée peut démarrer la partie dès que 2 à 5 joueurs ont rejoint.",
            "Ne partage le code de classe qu’avec les personnes que tu veux inviter.",
        ],
        "skills": "Ambiance de groupe, spontanéité et discussion.",
    }
}

NORMAL_TRUTHS = [
    "Quelle est la chose la plus drôle qui t’est arrivée récemment ?",
    "Quelle habitude aimerais-tu changer chez toi ?",
    "Quel est ton talent le plus inutile ?",
    "Quel est le dernier mensonge sans importance que tu as raconté ?",
    "Quelle chanson connais-tu presque entièrement par cœur ?",
    "Quel est ton plus gros moment de gêne en public ?",
    "Si tu pouvais partir demain n’importe où, où irais-tu ?",
    "Quelle personne du groupe te fait le plus rire ?",
    "Quel est le pire cadeau que tu aies reçu ?",
    "Quelle peur un peu ridicule as-tu encore ?",
    "Quel métier aurais-tu aimé tester pendant une semaine ?",
    "Quel est ton plus grand défaut selon toi ?",
    "Quelle série ou quel film peux-tu revoir plusieurs fois ?",
    "Quel est le truc le plus bizarre que tu aies déjà mangé ?",
    "Quelle application utilises-tu beaucoup trop ?",
    "Quelle décision impulsive t’a finalement rendu heureux ?",
]

NORMAL_DARES = [
    "Fais une imitation d’un joueur du groupe pendant 20 secondes.",
    "Parle avec un accent inventé jusqu’à ton prochain tour.",
    "Fais 10 secondes de danse sans musique.",
    "Laisse le groupe choisir un mot que tu dois placer dans ta prochaine phrase.",
    "Fais le bruit de trois animaux différents sans rire.",
    "Raconte une blague, même mauvaise.",
    "Fais une pose de star pendant 10 secondes.",
    "Chante le refrain d’une chanson de ton choix.",
    "Donne un compliment sincère à la personne à ta gauche.",
    "Fais semblant de présenter la météo pendant 20 secondes.",
    "Essaie de dire l’alphabet à l’envers le plus loin possible.",
    "Parle très lentement pendant les deux prochaines phrases.",
    "Mime une émotion et laisse le groupe la deviner.",
    "Fais un mini-discours de 20 secondes pour vendre un objet banal autour de toi.",
]

ADULT_TRUTHS = [
    "Quel est ton plus gros red flag dans une relation ?",
    "Quel est le compliment qui t’a le plus marqué ?",
    "Quel est ton date le plus gênant ou le plus raté ?",
    "As-tu déjà eu un crush que personne ici ne soupçonnerait ?",
    "Quelle qualité te séduit le plus chez quelqu’un ?",
    "Quel est ton plus grand deal-breaker amoureux ?",
    "Quelle est la chose la plus audacieuse que tu aies faite pour plaire à quelqu’un ?",
    "Qui dans le groupe serait le plus capable de réussir un rendez-vous improvisé ?",
    "As-tu déjà regretté d’avoir envoyé un message trop vite ?",
    "Quel est le type de personnalité qui t’attire le plus ?",
    "Quelle situation romantique t’a déjà mis très mal à l’aise ?",
    "Quelle est la première chose que tu remarques généralement chez quelqu’un ?",
]

ADULT_DARES = [
    "Fais une déclaration romantique complètement improvisée à un joueur volontaire.",
    "Fais une imitation volontairement exagérée d’une scène de séduction pendant 20 secondes.",
    "Donne un compliment différent à chaque personne du groupe.",
    "Laisse le groupe te choisir un surnom jusqu’à ton prochain tour.",
    "Fais 20 secondes de danse lente ou dramatique, seul ou avec un volontaire.",
    "Lis ta dernière phrase envoyée dans une conversation non privée, si tu es à l’aise de la partager.",
    "Décris ton rendez-vous idéal en 30 secondes comme si tu vendais un voyage de luxe.",
    "Fais un regard de cinéma dramatique à la personne choisie par le groupe pendant 10 secondes, sans la toucher.",
    "Choisis quelqu’un de volontaire et improvisez ensemble une fausse scène de demande en mariage pendant 20 secondes.",
    "Raconte une anecdote romantique gênante que tu acceptes de partager.",
]

_TABLE_READY = False
ROOM_TTL_HOURS = 24


def _now():
    return datetime.now(timezone.utc).isoformat()


def _clean_name(value):
    value = (value or "").strip()
    if not 2 <= len(value) <= 20:
        return None
    if not re.fullmatch(r"[A-Za-zÀ-ÿ0-9 _-]+", value):
        return None
    return value


def _parse_age(value):
    try:
        age = int(value)
    except (TypeError, ValueError):
        return None
    if not 13 <= age <= 100:
        return None
    return age


def _prompt(kind, adult_mode):
    if kind == "verite":
        pool = NORMAL_TRUTHS + (ADULT_TRUTHS if adult_mode else [])
    else:
        pool = NORMAL_DARES + (ADULT_DARES if adult_mode else [])
    return choice(pool)


def register_action_verite(app, games, game_content, db_connection, current_pseudo):
    global _TABLE_READY

    def ensure_tables():
        global _TABLE_READY
        if _TABLE_READY:
            return
        with db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS av_rooms (
                    code TEXT PRIMARY KEY,
                    creator_token TEXT NOT NULL,
                    status TEXT NOT NULL,
                    turn_index INTEGER NOT NULL,
                    current_kind TEXT,
                    current_prompt TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS av_players (
                    player_token TEXT PRIMARY KEY,
                    room_code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    is_adult INTEGER NOT NULL,
                    player_order INTEGER NOT NULL,
                    joined_at TEXT NOT NULL
                )
            """)
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=ROOM_TTL_HOURS)).isoformat()
            conn.execute("DELETE FROM av_players WHERE room_code IN (SELECT code FROM av_rooms WHERE created_at < ?)", (cutoff,))
            conn.execute("DELETE FROM av_rooms WHERE created_at < ?", (cutoff,))
            conn.commit()
        _TABLE_READY = True

    def memberships():
        value = session.get("av_memberships")
        return value if isinstance(value, dict) else {}

    def remember_membership(code, token):
        value = memberships()
        value[code] = token
        session["av_memberships"] = value

    def room_for(code):
        ensure_tables()
        with db_connection() as conn:
            row = conn.execute("SELECT * FROM av_rooms WHERE code = ?", (code,)).fetchone()
        return dict(row) if row else None

    def players_for(code):
        ensure_tables()
        with db_connection() as conn:
            rows = conn.execute(
                "SELECT player_token, name, is_adult, player_order, joined_at FROM av_players WHERE room_code = ? ORDER BY player_order ASC",
                (code,),
            ).fetchall()
        return [dict(row) for row in rows]

    def player_for_session(code):
        token = memberships().get(code)
        if not token:
            return None
        with db_connection() as conn:
            row = conn.execute(
                "SELECT player_token, name, is_adult, player_order FROM av_players WHERE room_code = ? AND player_token = ?",
                (code, token),
            ).fetchone()
        return dict(row) if row else None

    def touch_room(code, *, status=None, turn_index=None, kind_marker="__keep__", prompt_marker="__keep__"):
        room = room_for(code)
        if not room:
            return
        status = room["status"] if status is None else status
        turn_index = room["turn_index"] if turn_index is None else turn_index
        kind = room["current_kind"] if kind_marker == "__keep__" else kind_marker
        prompt = room["current_prompt"] if prompt_marker == "__keep__" else prompt_marker
        with db_connection() as conn:
            conn.execute(
                "UPDATE av_rooms SET status = ?, turn_index = ?, current_kind = ?, current_prompt = ?, updated_at = ? WHERE code = ?",
                (status, turn_index, kind, prompt, _now(), code),
            )
            conn.commit()

    original_start = app.view_functions["start_game"]

    def start_dispatch(game):
        if game == "action-verite":
            return redirect(url_for("av_home"))
        return original_start(game)

    app.view_functions["start_game"] = start_dispatch

    @app.route("/action-verite")
    def av_home():
        return render_template("action_verite_home.html", pseudo=current_pseudo())

    @app.route("/action-verite/local", methods=["GET", "POST"])
    def av_local():
        error = None
        state = session.get("av_local")
        if request.method == "POST":
            action = request.form.get("action") or ""
            if action == "setup":
                names = request.form.getlist("player_name")
                ages = request.form.getlist("player_age")
                try:
                    count = int(request.form.get("player_count", "0"))
                except ValueError:
                    count = 0
                if not 2 <= count <= 5:
                    error = "Choisis entre 2 et 5 joueurs."
                else:
                    players = []
                    seen = set()
                    for index in range(count):
                        name = _clean_name(names[index] if index < len(names) else "")
                        age = _parse_age(ages[index] if index < len(ages) else "")
                        if not name or age is None:
                            error = "Chaque joueur doit avoir un pseudo valide et un âge entre 13 et 100 ans."
                            break
                        if name.casefold() in seen:
                            error = "Utilise un pseudo différent pour chaque joueur."
                            break
                        seen.add(name.casefold())
                        players.append({"name": name, "is_adult": age >= 18})
                    if not error:
                        state = {
                            "players": players,
                            "turn_index": 0,
                            "kind": None,
                            "prompt": None,
                            "round": 1,
                            "adult_mode": all(player["is_adult"] for player in players),
                        }
                        session["av_local"] = state
                        return redirect(url_for("av_local"))
            elif state and action == "choose":
                kind = request.form.get("kind")
                if kind in {"action", "verite"} and not state.get("prompt"):
                    state["kind"] = kind
                    state["prompt"] = _prompt(kind, bool(state.get("adult_mode")))
                    session["av_local"] = state
                    return redirect(url_for("av_local"))
            elif state and action == "next":
                total = len(state["players"])
                next_index = (int(state["turn_index"]) + 1) % total
                if next_index == 0:
                    state["round"] = int(state.get("round", 1)) + 1
                state["turn_index"] = next_index
                state["kind"] = None
                state["prompt"] = None
                session["av_local"] = state
                return redirect(url_for("av_local"))
            elif action == "reset":
                session.pop("av_local", None)
                return redirect(url_for("av_local"))

        current_player = None
        if state and state.get("players"):
            current_player = state["players"][int(state["turn_index"]) % len(state["players"])]
        return render_template(
            "action_verite_local.html",
            pseudo=current_pseudo(),
            state=state,
            current_player=current_player,
            error=error,
        )

    @app.route("/action-verite/classe/creer", methods=["GET", "POST"])
    def av_create_room():
        ensure_tables()
        error = None
        if request.method == "POST":
            name = _clean_name(request.form.get("name"))
            age = _parse_age(request.form.get("age"))
            if not name or age is None:
                error = "Entre un pseudo valide et un âge entre 13 et 100 ans."
            else:
                code = None
                with db_connection() as conn:
                    for _ in range(100):
                        candidate = f"{secrets.randbelow(10000):04d}"
                        exists = conn.execute("SELECT code FROM av_rooms WHERE code = ?", (candidate,)).fetchone()
                        if not exists:
                            code = candidate
                            break
                    if not code:
                        error = "Impossible de créer une classe pour le moment. Réessaie."
                    else:
                        creator_token = secrets.token_urlsafe(18)
                        now = _now()
                        conn.execute(
                            "INSERT INTO av_rooms (code, creator_token, status, turn_index, current_kind, current_prompt, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (code, creator_token, "waiting", 0, None, None, now, now),
                        )
                        conn.execute(
                            "INSERT INTO av_players (player_token, room_code, name, is_adult, player_order, joined_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (creator_token, code, name, 1 if age >= 18 else 0, 0, now),
                        )
                        conn.commit()
                        remember_membership(code, creator_token)
                        return redirect(url_for("av_room", code=code))
        return render_template("action_verite_create.html", pseudo=current_pseudo(), error=error)

    @app.route("/action-verite/classe/rejoindre", methods=["GET", "POST"])
    def av_join_room():
        ensure_tables()
        error = None
        code_value = (request.args.get("code") or request.form.get("code") or "").strip()
        if request.method == "POST":
            code = code_value
            name = _clean_name(request.form.get("name"))
            age = _parse_age(request.form.get("age"))
            if not re.fullmatch(r"\d{4}", code):
                error = "Le code doit contenir exactement 4 chiffres."
            elif not name or age is None:
                error = "Entre un pseudo valide et un âge entre 13 et 100 ans."
            else:
                room = room_for(code)
                if not room:
                    error = "Cette classe n’existe pas ou a expiré."
                elif room["status"] != "waiting":
                    error = "La partie a déjà commencé."
                else:
                    players = players_for(code)
                    if len(players) >= 5:
                        error = "Cette classe contient déjà 5 joueurs."
                    elif name.casefold() in {player["name"].casefold() for player in players}:
                        error = "Ce pseudo est déjà utilisé dans cette classe."
                    else:
                        token = secrets.token_urlsafe(18)
                        now = _now()
                        with db_connection() as conn:
                            conn.execute(
                                "INSERT INTO av_players (player_token, room_code, name, is_adult, player_order, joined_at) VALUES (?, ?, ?, ?, ?, ?)",
                                (token, code, name, 1 if age >= 18 else 0, len(players), now),
                            )
                            conn.execute("UPDATE av_rooms SET updated_at = ? WHERE code = ?", (now, code))
                            conn.commit()
                        remember_membership(code, token)
                        return redirect(url_for("av_room", code=code))
        return render_template(
            "action_verite_join.html",
            pseudo=current_pseudo(),
            error=error,
            code_value=code_value,
        )

    @app.route("/action-verite/classe/<code>")
    def av_room(code):
        if not re.fullmatch(r"\d{4}", code):
            abort(404)
        room = room_for(code)
        if not room:
            abort(404)
        players = players_for(code)
        member = player_for_session(code)
        if not member:
            return redirect(url_for("av_join_room", code=code))
        current_player = None
        if players and room["status"] == "playing":
            current_player = players[int(room["turn_index"]) % len(players)]
        adult_mode = bool(players) and all(bool(player["is_adult"]) for player in players)
        is_creator = member["player_token"] == room["creator_token"]
        is_current = bool(current_player and current_player["player_token"] == member["player_token"])
        return render_template(
            "action_verite_room.html",
            pseudo=current_pseudo(),
            room=room,
            players=players,
            member=member,
            current_player=current_player,
            adult_mode=adult_mode,
            is_creator=is_creator,
            is_current=is_current,
        )

    @app.route("/action-verite/classe/<code>/demarrer", methods=["POST"])
    def av_room_start(code):
        room = room_for(code)
        member = player_for_session(code)
        if not room or not member or member["player_token"] != room["creator_token"]:
            abort(403)
        players = players_for(code)
        if not 2 <= len(players) <= 5:
            return redirect(url_for("av_room", code=code))
        touch_room(code, status="playing", turn_index=0, kind_marker=None, prompt_marker=None)
        return redirect(url_for("av_room", code=code))

    @app.route("/action-verite/classe/<code>/choisir", methods=["POST"])
    def av_room_choose(code):
        room = room_for(code)
        players = players_for(code)
        member = player_for_session(code)
        if not room or room["status"] != "playing" or not players or not member:
            abort(403)
        current = players[int(room["turn_index"]) % len(players)]
        if current["player_token"] != member["player_token"]:
            abort(403)
        kind = request.form.get("kind")
        if kind not in {"action", "verite"}:
            abort(400)
        adult_mode = all(bool(player["is_adult"]) for player in players)
        touch_room(code, kind_marker=kind, prompt_marker=_prompt(kind, adult_mode))
        return redirect(url_for("av_room", code=code))

    @app.route("/action-verite/classe/<code>/suivant", methods=["POST"])
    def av_room_next(code):
        room = room_for(code)
        players = players_for(code)
        member = player_for_session(code)
        if not room or room["status"] != "playing" or not players or not member:
            abort(403)
        current = players[int(room["turn_index"]) % len(players)]
        is_creator = member["player_token"] == room["creator_token"]
        if current["player_token"] != member["player_token"] and not is_creator:
            abort(403)
        next_index = (int(room["turn_index"]) + 1) % len(players)
        touch_room(code, turn_index=next_index, kind_marker=None, prompt_marker=None)
        return redirect(url_for("av_room", code=code))

    @app.route("/action-verite/classe/<code>/fermer", methods=["POST"])
    def av_room_close(code):
        room = room_for(code)
        member = player_for_session(code)
        if not room or not member or member["player_token"] != room["creator_token"]:
            abort(403)
        with db_connection() as conn:
            conn.execute("DELETE FROM av_players WHERE room_code = ?", (code,))
            conn.execute("DELETE FROM av_rooms WHERE code = ?", (code,))
            conn.commit()
        value = memberships()
        value.pop(code, None)
        session["av_memberships"] = value
        return redirect(url_for("av_home"))

    @app.route("/action-verite/classe/<code>/etat")
    def av_room_state(code):
        room = room_for(code)
        member = player_for_session(code)
        if not room or not member:
            return jsonify({"available": False}), 404
        return jsonify({
            "available": True,
            "status": room["status"],
            "updated_at": room["updated_at"],
            "players": len(players_for(code)),
        })
