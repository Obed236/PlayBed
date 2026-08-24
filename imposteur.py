import re
import secrets
from datetime import datetime, timedelta, timezone
from random import choice, sample

from flask import abort, jsonify, redirect, render_template, request, session, url_for


IMPOSTEUR_GAME = {
    "imposteur": {
        "name": "L'Imposteur",
        "emoji": "🕵️",
        "description": "Joue à plusieurs en ligne : découvre ton rôle en secret, donne un indice, discute puis vote pour démasquer l’imposteur. Salons publics ou privés.",
        "tag": "Groupe",
    }
}

IMPOSTEUR_GAME_CONTENT = {
    "imposteur": {
        "headline": "Observe les indices, bluffe et trouve l’imposteur.",
        "objective": "Chaque joueur reçoit un rôle secret. Les citoyens voient tous le même mot, tandis que l’imposteur doit le deviner grâce aux indices sans se faire repérer. Après les indices, tout le monde vote.",
        "rules": [
            "Une partie se joue de 3 à 12 joueurs.",
            "Le créateur choisit un salon public ou privé et le nombre d’imposteurs.",
            "Les citoyens voient le mot secret. Les imposteurs voient uniquement leur rôle.",
            "Chaque joueur encore en jeu donne un indice court sans écrire directement le mot secret.",
            "Quand tous les indices sont donnés, le vote s’ouvre automatiquement.",
            "Le joueur qui reçoit le plus de voix est éliminé. En cas d’égalité, personne n’est éliminé.",
            "Les citoyens gagnent quand tous les imposteurs sont éliminés.",
            "Les imposteurs gagnent lorsqu’ils sont aussi nombreux que les citoyens encore en jeu.",
        ],
        "scoring": "L’Imposteur est un jeu social multijoueur. Il n’ajoute pas de points au classement général PlayBed.",
        "tips": [
            "Si tu es citoyen, donne un indice assez précis pour aider les autres sans révéler le mot.",
            "Si tu es imposteur, écoute les indices avant de choisir un mot qui paraît crédible.",
            "Observe les indices trop vagues, trop précis ou qui semblent copiés sur ceux des autres.",
        ],
        "skills": "Déduction, bluff, observation et communication.",
    }
}

WORDS = [
    ("Animaux", "éléphant"), ("Animaux", "girafe"), ("Animaux", "dauphin"), ("Animaux", "tigre"),
    ("Animaux", "pingouin"), ("Animaux", "crocodile"), ("Animaux", "papillon"), ("Animaux", "requin"),
    ("Nourriture", "pizza"), ("Nourriture", "couscous"), ("Nourriture", "chocolat"), ("Nourriture", "burger"),
    ("Nourriture", "pastèque"), ("Nourriture", "croissant"), ("Nourriture", "spaghetti"), ("Nourriture", "fromage"),
    ("Objets", "parapluie"), ("Objets", "téléphone"), ("Objets", "valise"), ("Objets", "miroir"),
    ("Objets", "clavier"), ("Objets", "bougie"), ("Objets", "lunettes"), ("Objets", "montre"),
    ("Lieux", "aéroport"), ("Lieux", "cinéma"), ("Lieux", "plage"), ("Lieux", "école"),
    ("Lieux", "hôpital"), ("Lieux", "stade"), ("Lieux", "musée"), ("Lieux", "restaurant"),
    ("Métiers", "médecin"), ("Métiers", "pilote"), ("Métiers", "pompier"), ("Métiers", "professeur"),
    ("Métiers", "cuisinier"), ("Métiers", "avocat"), ("Métiers", "journaliste"), ("Métiers", "architecte"),
    ("Loisirs", "football"), ("Loisirs", "danse"), ("Loisirs", "lecture"), ("Loisirs", "cinéma"),
    ("Loisirs", "gaming"), ("Loisirs", "natation"), ("Loisirs", "voyage"), ("Loisirs", "musique"),
    ("Nature", "volcan"), ("Nature", "océan"), ("Nature", "forêt"), ("Nature", "désert"),
    ("Nature", "orage"), ("Nature", "montagne"), ("Nature", "rivière"), ("Nature", "neige"),
    ("Transport", "avion"), ("Transport", "métro"), ("Transport", "vélo"), ("Transport", "bateau"),
    ("Transport", "train"), ("Transport", "moto"), ("Transport", "hélicoptère"), ("Transport", "bus"),
]

ROOM_TTL_HOURS = 18
_TABLE_READY = False
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _valid_code(value):
    value = (value or "").strip().upper()
    return value if re.fullmatch(r"[A-Z2-9]{6}", value) else None


def _clean_text(value, min_length=1, max_length=240):
    value = " ".join((value or "").strip().split())
    if not min_length <= len(value) <= max_length:
        return None
    return value


def register_imposteur(app, games, game_content, db_connection, current_pseudo):
    global _TABLE_READY

    def ensure_tables():
        global _TABLE_READY
        if _TABLE_READY:
            return
        with db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS im_rooms (
                    code TEXT PRIMARY KEY,
                    creator_token TEXT NOT NULL,
                    visibility TEXT NOT NULL,
                    status TEXT NOT NULL,
                    max_players INTEGER NOT NULL,
                    impostor_count INTEGER NOT NULL,
                    round_no INTEGER NOT NULL,
                    secret_word TEXT,
                    category TEXT,
                    winner TEXT,
                    result_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS im_players (
                    player_token TEXT PRIMARY KEY,
                    room_code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT,
                    alive INTEGER NOT NULL,
                    player_order INTEGER NOT NULL,
                    joined_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS im_clues (
                    clue_token TEXT PRIMARY KEY,
                    room_code TEXT NOT NULL,
                    round_no INTEGER NOT NULL,
                    player_token TEXT NOT NULL,
                    clue TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS im_votes (
                    vote_token TEXT PRIMARY KEY,
                    room_code TEXT NOT NULL,
                    round_no INTEGER NOT NULL,
                    voter_token TEXT NOT NULL,
                    target_token TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS im_messages (
                    message_token TEXT PRIMARY KEY,
                    room_code TEXT NOT NULL,
                    player_token TEXT NOT NULL,
                    name TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=ROOM_TTL_HOURS)).isoformat()
            stale = conn.execute("SELECT code FROM im_rooms WHERE created_at < ?", (cutoff,)).fetchall()
            for row in stale:
                code = row["code"]
                conn.execute("DELETE FROM im_clues WHERE room_code = ?", (code,))
                conn.execute("DELETE FROM im_votes WHERE room_code = ?", (code,))
                conn.execute("DELETE FROM im_messages WHERE room_code = ?", (code,))
                conn.execute("DELETE FROM im_players WHERE room_code = ?", (code,))
                conn.execute("DELETE FROM im_rooms WHERE code = ?", (code,))
            conn.commit()
        _TABLE_READY = True

    def memberships():
        value = session.get("im_memberships")
        return value if isinstance(value, dict) else {}

    def remember_membership(code, token):
        value = memberships()
        value[code] = token
        session["im_memberships"] = value

    def forget_membership(code):
        value = memberships()
        value.pop(code, None)
        session["im_memberships"] = value

    def room_for(code):
        ensure_tables()
        code = _valid_code(code)
        if not code:
            return None
        with db_connection() as conn:
            row = conn.execute("SELECT * FROM im_rooms WHERE code = ?", (code,)).fetchone()
        return dict(row) if row else None

    def players_for(code):
        ensure_tables()
        with db_connection() as conn:
            rows = conn.execute(
                "SELECT player_token, name, role, alive, player_order, joined_at "
                "FROM im_players WHERE room_code = ? ORDER BY player_order ASC",
                (code,),
            ).fetchall()
        return [dict(row) for row in rows]

    def member_for(code):
        token = memberships().get(code)
        if not token:
            return None
        with db_connection() as conn:
            row = conn.execute(
                "SELECT player_token, name, role, alive, player_order "
                "FROM im_players WHERE room_code = ? AND player_token = ?",
                (code, token),
            ).fetchone()
        return dict(row) if row else None

    def update_room(code, **changes):
        if not changes:
            return
        changes["updated_at"] = _now()
        allowed = {
            "status", "max_players", "impostor_count", "round_no", "secret_word",
            "category", "winner", "result_message", "updated_at",
        }
        payload = [(key, value) for key, value in changes.items() if key in allowed]
        if not payload:
            return
        assignments = ", ".join(f"{key} = ?" for key, _ in payload)
        params = [value for _, value in payload] + [code]
        with db_connection() as conn:
            conn.execute(f"UPDATE im_rooms SET {assignments} WHERE code = ?", tuple(params))
            conn.commit()

    def touch(code):
        update_room(code, updated_at=_now())

    def delete_room(code):
        with db_connection() as conn:
            conn.execute("DELETE FROM im_clues WHERE room_code = ?", (code,))
            conn.execute("DELETE FROM im_votes WHERE room_code = ?", (code,))
            conn.execute("DELETE FROM im_messages WHERE room_code = ?", (code,))
            conn.execute("DELETE FROM im_players WHERE room_code = ?", (code,))
            conn.execute("DELETE FROM im_rooms WHERE code = ?", (code,))
            conn.commit()

    def public_rooms():
        ensure_tables()
        with db_connection() as conn:
            rooms = conn.execute(
                "SELECT * FROM im_rooms WHERE visibility = ? AND status = ? "
                "ORDER BY updated_at DESC LIMIT 30",
                ("public", "waiting"),
            ).fetchall()
            result = []
            for raw in rooms:
                room = dict(raw)
                count = conn.execute(
                    "SELECT COUNT(*) AS n FROM im_players WHERE room_code = ?",
                    (room["code"],),
                ).fetchone()["n"]
                room["player_count"] = int(count)
                if int(count) < int(room["max_players"]):
                    result.append(room)
        return result

    def generate_code(conn):
        for _ in range(200):
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
            if not conn.execute("SELECT code FROM im_rooms WHERE code = ?", (code,)).fetchone():
                return code
        return None

    def join_room(code):
        room = room_for(code)
        pseudo = current_pseudo()
        if not room:
            return None, "Cette salle n’existe plus."
        if not pseudo:
            return None, "Choisis d’abord un pseudo PlayBed."
        if room["status"] != "waiting":
            return None, "La partie a déjà commencé."
        existing = member_for(code)
        if existing:
            return existing, None

        players = players_for(code)
        if len(players) >= int(room["max_players"]):
            return None, "Cette salle est pleine."
        if any(player["name"].casefold() == pseudo.casefold() for player in players):
            return None, "Ce pseudo est déjà présent dans cette salle."

        token = secrets.token_urlsafe(24)
        with db_connection() as conn:
            conn.execute(
                "INSERT INTO im_players "
                "(player_token, room_code, name, role, alive, player_order, joined_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (token, code, pseudo, None, 1, len(players), _now()),
            )
            conn.commit()
        remember_membership(code, token)
        touch(code)
        return member_for(code), None

    def clues_for(code, round_no):
        with db_connection() as conn:
            rows = conn.execute(
                "SELECT c.player_token, c.clue, c.created_at, p.name "
                "FROM im_clues c JOIN im_players p ON p.player_token = c.player_token "
                "WHERE c.room_code = ? AND c.round_no = ? ORDER BY p.player_order ASC",
                (code, round_no),
            ).fetchall()
        return [dict(row) for row in rows]

    def votes_for(code, round_no):
        with db_connection() as conn:
            rows = conn.execute(
                "SELECT voter_token, target_token FROM im_votes "
                "WHERE room_code = ? AND round_no = ?",
                (code, round_no),
            ).fetchall()
        return [dict(row) for row in rows]

    def messages_for(code):
        with db_connection() as conn:
            rows = conn.execute(
                "SELECT name, message, created_at FROM im_messages "
                "WHERE room_code = ? ORDER BY created_at DESC LIMIT 40",
                (code,),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def check_win(code, result_message=None):
        players = players_for(code)
        alive = [p for p in players if bool(p["alive"])]
        impostors = [p for p in alive if p["role"] == "impostor"]
        citizens = [p for p in alive if p["role"] == "citizen"]
        if not impostors:
            update_room(
                code,
                status="finished",
                winner="citizens",
                result_message=result_message or "Tous les imposteurs ont été éliminés.",
            )
            return True
        if len(impostors) >= len(citizens):
            update_room(
                code,
                status="finished",
                winner="impostors",
                result_message=result_message or "Les imposteurs sont désormais aussi nombreux que les citoyens.",
            )
            return True
        return False

    def resolve_vote(code):
        room = room_for(code)
        if not room or room["status"] != "voting":
            return
        round_no = int(room["round_no"])
        players = players_for(code)
        alive = [player for player in players if bool(player["alive"])]
        votes = votes_for(code, round_no)
        if len(votes) < len(alive):
            return

        counts = {}
        for vote in votes:
            target = vote["target_token"]
            if target == "skip":
                continue
            counts[target] = counts.get(target, 0) + 1

        message = "Aucun joueur n’a été éliminé."
        if counts:
            highest = max(counts.values())
            leaders = [token for token, total in counts.items() if total == highest]
            if len(leaders) == 1:
                target_token = leaders[0]
                eliminated = next(
                    (player for player in alive if player["player_token"] == target_token),
                    None,
                )
                if eliminated:
                    with db_connection() as conn:
                        conn.execute(
                            "UPDATE im_players SET alive = 0 WHERE room_code = ? AND player_token = ?",
                            (code, target_token),
                        )
                        conn.commit()
                    if eliminated["role"] == "impostor":
                        message = f"{eliminated['name']} a été éliminé : c’était un imposteur."
                    else:
                        message = f"{eliminated['name']} a été éliminé : c’était un citoyen."
            else:
                message = "Égalité au vote : personne n’est éliminé."

        if check_win(code, message):
            return

        update_room(
            code,
            status="playing",
            round_no=round_no + 1,
            result_message=message,
        )

    original_start = app.view_functions["start_game"]

    def start_dispatch(game):
        if game == "imposteur":
            return redirect(url_for("im_home"))
        return original_start(game)

    app.view_functions["start_game"] = start_dispatch

    @app.route("/imposteur")
    def im_home():
        return render_template(
            "imposteur_home.html",
            pseudo=current_pseudo(),
            public_rooms=public_rooms(),
            error=request.args.get("error"),
            info=request.args.get("info"),
            code_value=(request.args.get("code") or "").upper(),
        )

    @app.route("/imposteur/creer", methods=["GET", "POST"])
    def im_create():
        if not current_pseudo():
            return redirect(url_for("home", need_pseudo=1) + "#player")
        error = None
        if request.method == "POST":
            visibility = request.form.get("visibility")
            try:
                max_players = int(request.form.get("max_players", "6"))
                impostor_count = int(request.form.get("impostor_count", "1"))
            except ValueError:
                max_players = 0
                impostor_count = 0

            if visibility not in {"public", "private"}:
                error = "Choisis une salle publique ou privée."
            elif not 3 <= max_players <= 12:
                error = "Choisis entre 3 et 12 joueurs."
            else:
                max_impostors = max(1, min(3, (max_players - 1) // 3))
                if not 1 <= impostor_count <= max_impostors:
                    error = f"Pour {max_players} joueurs, choisis entre 1 et {max_impostors} imposteur(s)."

            if not error:
                creator_token = secrets.token_urlsafe(24)
                now = _now()
                with db_connection() as conn:
                    code = generate_code(conn)
                    if not code:
                        error = "Impossible de créer une salle pour le moment."
                    else:
                        conn.execute(
                            "INSERT INTO im_rooms "
                            "(code, creator_token, visibility, status, max_players, impostor_count, "
                            "round_no, secret_word, category, winner, result_message, created_at, updated_at) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                code, creator_token, visibility, "waiting", max_players,
                                impostor_count, 0, None, None, None, None, now, now,
                            ),
                        )
                        conn.execute(
                            "INSERT INTO im_players "
                            "(player_token, room_code, name, role, alive, player_order, joined_at) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (creator_token, code, current_pseudo(), None, 1, 0, now),
                        )
                        conn.commit()
                        remember_membership(code, creator_token)
                        return redirect(url_for("im_room", code=code))

        return render_template("imposteur_create.html", pseudo=current_pseudo(), error=error)

    @app.route("/imposteur/rejoindre", methods=["POST"])
    def im_join_private():
        if not current_pseudo():
            return redirect(url_for("home", need_pseudo=1) + "#player")
        code = _valid_code(request.form.get("code"))
        if not code:
            return redirect(url_for("im_home", error="Entre un code de salle valide."))
        _, error = join_room(code)
        if error:
            return redirect(url_for("im_home", error=error, code=code))
        return redirect(url_for("im_room", code=code))

    @app.route("/imposteur/public/<code>/rejoindre", methods=["POST"])
    def im_join_public(code):
        room = room_for(code)
        if not room or room["visibility"] != "public":
            abort(404)
        if not current_pseudo():
            return redirect(url_for("home", need_pseudo=1) + "#player")
        _, error = join_room(code)
        if error:
            return redirect(url_for("im_home", error=error))
        return redirect(url_for("im_room", code=code))

    @app.route("/imposteur/<code>")
    def im_room(code):
        code = _valid_code(code)
        if not code:
            abort(404)
        room = room_for(code)
        if not room:
            abort(404)
        member = member_for(code)
        if not member:
            if room["visibility"] == "public" and room["status"] == "waiting":
                return redirect(url_for("im_home", info="Rejoins la salle publique depuis la liste."))
            return redirect(url_for("im_home", code=code, info="Entre le code pour rejoindre cette salle."))

        players = players_for(code)
        round_no = int(room["round_no"])
        clues = clues_for(code, round_no) if round_no > 0 else []
        votes = votes_for(code, round_no) if round_no > 0 else []
        member_clue = next((item for item in clues if item["player_token"] == member["player_token"]), None)
        member_voted = any(item["voter_token"] == member["player_token"] for item in votes)
        is_creator = member["player_token"] == room["creator_token"]
        alive_players = [player for player in players if bool(player["alive"])]
        return render_template(
            "imposteur_room.html",
            pseudo=current_pseudo(),
            room=room,
            players=players,
            alive_players=alive_players,
            member=member,
            is_creator=is_creator,
            clues=clues,
            votes_cast=len(votes),
            member_clue=member_clue,
            member_voted=member_voted,
            messages=messages_for(code),
            reveal_word=room["secret_word"] if member["role"] == "citizen" else None,
        )

    @app.route("/imposteur/<code>/demarrer", methods=["POST"])
    def im_start(code):
        room = room_for(code)
        member = member_for(code)
        if not room or not member or member["player_token"] != room["creator_token"]:
            abort(403)
        if room["status"] != "waiting":
            return redirect(url_for("im_room", code=code))

        players = players_for(code)
        if len(players) < 3:
            return redirect(url_for("im_room", code=code))
        impostor_count = min(int(room["impostor_count"]), max(1, (len(players) - 1) // 2))
        impostor_tokens = set(sample([p["player_token"] for p in players], k=impostor_count))
        category, word = choice(WORDS)

        with db_connection() as conn:
            for player in players:
                role = "impostor" if player["player_token"] in impostor_tokens else "citizen"
                conn.execute(
                    "UPDATE im_players SET role = ?, alive = 1 WHERE room_code = ? AND player_token = ?",
                    (role, code, player["player_token"]),
                )
            conn.execute("DELETE FROM im_clues WHERE room_code = ?", (code,))
            conn.execute("DELETE FROM im_votes WHERE room_code = ?", (code,))
            conn.commit()

        update_room(
            code,
            status="playing",
            round_no=1,
            secret_word=word,
            category=category,
            winner=None,
            result_message="La partie commence. Donnez chacun un indice.",
        )
        return redirect(url_for("im_room", code=code))

    @app.route("/imposteur/<code>/indice", methods=["POST"])
    def im_clue(code):
        room = room_for(code)
        member = member_for(code)
        if not room or not member or room["status"] != "playing" or not bool(member["alive"]):
            abort(403)

        clue = _clean_text(request.form.get("clue"), 2, 40)
        if not clue:
            return redirect(url_for("im_room", code=code))
        if room["secret_word"] and clue.casefold() == str(room["secret_word"]).casefold():
            return redirect(url_for("im_room", code=code))

        round_no = int(room["round_no"])
        with db_connection() as conn:
            exists = conn.execute(
                "SELECT clue_token FROM im_clues WHERE room_code = ? AND round_no = ? AND player_token = ?",
                (code, round_no, member["player_token"]),
            ).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO im_clues "
                    "(clue_token, room_code, round_no, player_token, clue, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (secrets.token_urlsafe(18), code, round_no, member["player_token"], clue, _now()),
                )
                conn.commit()

        clues = clues_for(code, round_no)
        alive_count = len([player for player in players_for(code) if bool(player["alive"])])
        if len(clues) >= alive_count:
            update_room(code, status="voting", result_message="Tous les indices sont donnés. À vous de voter.")
        else:
            touch(code)
        return redirect(url_for("im_room", code=code))

    @app.route("/imposteur/<code>/vote", methods=["POST"])
    def im_vote(code):
        room = room_for(code)
        member = member_for(code)
        if not room or not member or room["status"] != "voting" or not bool(member["alive"]):
            abort(403)

        target = request.form.get("target") or ""
        alive = [player for player in players_for(code) if bool(player["alive"])]
        valid_targets = {player["player_token"] for player in alive}
        if target != "skip" and target not in valid_targets:
            abort(400)

        round_no = int(room["round_no"])
        with db_connection() as conn:
            exists = conn.execute(
                "SELECT vote_token FROM im_votes WHERE room_code = ? AND round_no = ? AND voter_token = ?",
                (code, round_no, member["player_token"]),
            ).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO im_votes "
                    "(vote_token, room_code, round_no, voter_token, target_token, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (secrets.token_urlsafe(18), code, round_no, member["player_token"], target, _now()),
                )
                conn.commit()

        touch(code)
        resolve_vote(code)
        return redirect(url_for("im_room", code=code))

    @app.route("/imposteur/<code>/chat", methods=["POST"])
    def im_chat(code):
        room = room_for(code)
        member = member_for(code)
        if not room or not member or room["status"] == "finished":
            abort(403)
        if room["status"] in {"playing", "voting"} and not bool(member["alive"]):
            abort(403)

        message = _clean_text(request.form.get("message"), 1, 240)
        if message:
            with db_connection() as conn:
                conn.execute(
                    "INSERT INTO im_messages "
                    "(message_token, room_code, player_token, name, message, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        secrets.token_urlsafe(18), code, member["player_token"],
                        member["name"], message, _now(),
                    ),
                )
                conn.commit()
            touch(code)
        return redirect(url_for("im_room", code=code))

    @app.route("/imposteur/<code>/rejouer", methods=["POST"])
    def im_replay(code):
        room = room_for(code)
        member = member_for(code)
        if not room or not member or member["player_token"] != room["creator_token"]:
            abort(403)
        if room["status"] != "finished":
            return redirect(url_for("im_room", code=code))
        with db_connection() as conn:
            conn.execute("UPDATE im_players SET role = NULL, alive = 1 WHERE room_code = ?", (code,))
            conn.execute("DELETE FROM im_clues WHERE room_code = ?", (code,))
            conn.execute("DELETE FROM im_votes WHERE room_code = ?", (code,))
            conn.commit()
        update_room(
            code,
            status="waiting",
            round_no=0,
            secret_word=None,
            category=None,
            winner=None,
            result_message="Nouvelle partie prête.",
        )
        return redirect(url_for("im_room", code=code))

    @app.route("/imposteur/<code>/quitter", methods=["POST"])
    def im_leave(code):
        room = room_for(code)
        member = member_for(code)
        if not room or not member:
            return redirect(url_for("im_home"))
        if member["player_token"] == room["creator_token"]:
            delete_room(code)
            forget_membership(code)
            return redirect(url_for("im_home", info="La salle a été fermée."))

        if room["status"] == "waiting":
            with db_connection() as conn:
                conn.execute(
                    "DELETE FROM im_players WHERE room_code = ? AND player_token = ?",
                    (code, member["player_token"]),
                )
                conn.commit()
            forget_membership(code)
            touch(code)
        elif room["status"] in {"playing", "voting"}:
            with db_connection() as conn:
                conn.execute(
                    "UPDATE im_players SET alive = 0 WHERE room_code = ? AND player_token = ?",
                    (code, member["player_token"]),
                )
                conn.commit()
            forget_membership(code)
            if not check_win(code, f"{member['name']} a quitté la partie."):
                update_room(
                    code,
                    status="playing",
                    round_no=int(room["round_no"]) + 1,
                    result_message=f"{member['name']} a quitté la partie. Nouveau tour.",
                )
        else:
            forget_membership(code)
        return redirect(url_for("im_home"))

    @app.route("/imposteur/<code>/fermer", methods=["POST"])
    def im_close(code):
        room = room_for(code)
        member = member_for(code)
        if not room or not member or member["player_token"] != room["creator_token"]:
            abort(403)
        delete_room(code)
        forget_membership(code)
        return redirect(url_for("im_home", info="La salle a été fermée."))

    @app.route("/imposteur/<code>/etat")
    def im_state(code):
        room = room_for(code)
        member = member_for(code)
        if not room or not member:
            return jsonify({"available": False}), 404
        round_no = int(room["round_no"])
        players = players_for(code)
        alive = [player for player in players if bool(player["alive"])]
        return jsonify({
            "available": True,
            "status": room["status"],
            "round": round_no,
            "updated_at": room["updated_at"],
            "players": len(players),
            "alive": len(alive),
            "clues": len(clues_for(code, round_no)) if round_no > 0 else 0,
            "votes": len(votes_for(code, round_no)) if round_no > 0 else 0,
        })
