"""Couche de règles de tour pour L'Imposteur.

Le projet historique garde son implémentation dans ``imposteur.py``. Ce paquet la
charge puis renforce l'ordre des descriptions sans casser les routes existantes.
"""

from copy import deepcopy
from datetime import datetime, timezone
from functools import wraps
from itertools import combinations
import importlib.util
import json
from pathlib import Path
import secrets

from flask import redirect, session, url_for


_LEGACY_PATH = Path(__file__).resolve().parent.parent / "imposteur.py"
_SPEC = importlib.util.spec_from_file_location("_playbed_imposteur_legacy", _LEGACY_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("Impossible de charger l'implémentation historique de L'Imposteur.")
_legacy = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_legacy)

IMPOSTEUR_GAME = deepcopy(_legacy.IMPOSTEUR_GAME)
IMPOSTEUR_GAME_CONTENT = deepcopy(_legacy.IMPOSTEUR_GAME_CONTENT)

_rules = IMPOSTEUR_GAME_CONTENT["imposteur"]["rules"]
_turn_rule = (
    "Les descriptions se font dans un ordre imposé : un citoyen parle toujours "
    "avant un imposteur. À 3 joueurs, l’imposteur parle obligatoirement en deuxième."
)
if _turn_rule not in _rules:
    _rules.insert(4, _turn_rule)

_tips = IMPOSTEUR_GAME_CONTENT["imposteur"]["tips"]
_tips[1] = (
    "Si tu es imposteur, écoute le citoyen qui parle avant toi puis donne un indice "
    "crédible sans copier le sien."
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def register_imposteur(app, games, game_content, db_connection, current_pseudo):
    """Enregistre le jeu historique puis ajoute un vrai tour de parole."""

    _legacy.register_imposteur(app, games, game_content, db_connection, current_pseudo)

    def room_state(code):
        with db_connection() as conn:
            row = conn.execute(
                "SELECT status, round_no, result_message, updated_at "
                "FROM im_rooms WHERE code = ?",
                (code,),
            ).fetchone()
        return dict(row) if row else None

    def member_token(code):
        memberships = session.get("im_memberships")
        if not isinstance(memberships, dict):
            return None
        return memberships.get(code)

    def ordered_players(code, alive_only=False):
        sql = (
            "SELECT player_token, name, role, alive, player_order "
            "FROM im_players WHERE room_code = ?"
        )
        params = [code]
        if alive_only:
            sql += " AND alive = 1"
        sql += " ORDER BY player_order ASC"
        with db_connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def clue_tokens(code, round_no):
        with db_connection() as conn:
            rows = conn.execute(
                "SELECT player_token FROM im_clues "
                "WHERE room_code = ? AND round_no = ?",
                (code, int(round_no)),
            ).fetchall()
        return {row["player_token"] for row in rows}

    def current_turn(code, round_no=None):
        room = room_state(code)
        if not room or room["status"] != "playing":
            return None
        round_no = int(round_no if round_no is not None else room["round_no"])
        already_played = clue_tokens(code, round_no)
        for player in ordered_players(code, alive_only=True):
            if player["player_token"] not in already_played:
                return player
        return None

    def set_message(code, message):
        with db_connection() as conn:
            conn.execute(
                "UPDATE im_rooms SET result_message = ?, updated_at = ? WHERE code = ?",
                (message, _now(), code),
            )
            conn.commit()

    def build_role_safe_order(players):
        """Retourne un ordre où chaque imposteur vient juste après un citoyen.

        Les imposteurs ne peuvent donc être ni premiers, ni derniers, ni consécutifs.
        À trois joueurs avec un imposteur, sa position est forcément la deuxième.
        """
        alive = [p for p in players if bool(p["alive"])]
        citizens = [p for p in alive if p["role"] == "citizen"]
        impostors = [p for p in alive if p["role"] == "impostor"]
        if not alive or not impostors or len(citizens) <= len(impostors):
            return alive

        rng = secrets.SystemRandom()
        old_order = [p["player_token"] for p in alive]
        n = len(alive)
        k = len(impostors)

        possible_positions = [
            combo
            for combo in combinations(range(1, n - 1), k)
            if all((pos - 1) not in combo for pos in combo)
        ]
        if not possible_positions:
            return alive

        best = None
        for _ in range(24):
            positions = set(rng.choice(possible_positions))
            shuffled_citizens = citizens[:]
            shuffled_impostors = impostors[:]
            rng.shuffle(shuffled_citizens)
            rng.shuffle(shuffled_impostors)

            citizen_index = 0
            impostor_index = 0
            ordered = []
            for position in range(n):
                if position in positions:
                    ordered.append(shuffled_impostors[impostor_index])
                    impostor_index += 1
                else:
                    ordered.append(shuffled_citizens[citizen_index])
                    citizen_index += 1

            best = ordered
            if [p["player_token"] for p in ordered] != old_order:
                break
        return best or alive

    def assign_clue_order(code):
        players = ordered_players(code)
        alive = [p for p in players if bool(p["alive"])]
        dead = [p for p in players if not bool(p["alive"])]
        ordered_alive = build_role_safe_order(alive)
        if not ordered_alive:
            return

        with db_connection() as conn:
            position = 0
            for player in ordered_alive + dead:
                conn.execute(
                    "UPDATE im_players SET player_order = ? "
                    "WHERE room_code = ? AND player_token = ?",
                    (position, code, player["player_token"]),
                )
                position += 1
            conn.commit()

    def announce_turn(code, prefix=None):
        room = room_state(code)
        if not room or room["status"] != "playing":
            return
        turn = current_turn(code, room["round_no"])
        if not turn:
            return
        message = f"🎙️ C’est au tour de {turn['name']} de donner sa description."
        if prefix:
            message = f"{prefix} {message}"
        set_message(code, message)

    original_start = app.view_functions.get("im_start")
    original_clue = app.view_functions.get("im_clue")
    original_vote = app.view_functions.get("im_vote")
    original_leave = app.view_functions.get("im_leave")

    if original_start:
        @wraps(original_start)
        def start_with_order(code):
            response = original_start(code)
            room = room_state(code)
            if room and room["status"] == "playing":
                assign_clue_order(code)
                announce_turn(code, "La partie commence.")
            return response

        app.view_functions["im_start"] = start_with_order

    if original_clue:
        @wraps(original_clue)
        def clue_in_turn(code):
            room = room_state(code)
            if room and room["status"] == "playing":
                turn = current_turn(code, room["round_no"])
                token = member_token(code)
                if turn and token != turn["player_token"]:
                    announce_turn(code)
                    return redirect(url_for("im_room", code=code))

            response = original_clue(code)
            room_after = room_state(code)
            if room_after and room_after["status"] == "playing":
                announce_turn(code)
            return response

        app.view_functions["im_clue"] = clue_in_turn

    if original_vote:
        @wraps(original_vote)
        def vote_then_reorder(code):
            before = room_state(code)
            response = original_vote(code)
            after = room_state(code)
            if (
                before
                and after
                and before["status"] == "voting"
                and after["status"] == "playing"
                and int(after["round_no"]) > int(before["round_no"])
            ):
                result = after.get("result_message")
                assign_clue_order(code)
                announce_turn(code, f"{result} Nouveau tour." if result else "Nouveau tour.")
            return response

        app.view_functions["im_vote"] = vote_then_reorder

    if original_leave:
        @wraps(original_leave)
        def leave_then_reorder(code):
            before = room_state(code)
            response = original_leave(code)
            after = room_state(code)
            if (
                before
                and after
                and after["status"] == "playing"
                and int(after["round_no"]) > int(before["round_no"])
            ):
                result = after.get("result_message")
                assign_clue_order(code)
                announce_turn(code, result or "Nouveau tour.")
            return response

        app.view_functions["im_leave"] = leave_then_reorder

    # L'ancien template affiche le formulaire à tous les joueurs vivants. On
    # conserve le template, mais on masque immédiatement le formulaire pour les
    # joueurs hors-tour. Le serveur vérifie aussi l'ordre ci-dessus : contourner
    # le JavaScript ne permet donc pas de jouer avant son tour.
    base_render_template = _legacy.render_template

    def render_template_with_turn(template_name, *args, **context):
        html = base_render_template(template_name, *args, **context)
        if template_name != "imposteur_room.html":
            return html

        room = context.get("room")
        member = context.get("member")
        if not room or not member or room.get("status") != "playing":
            return html

        turn = current_turn(room["code"], room["round_no"])
        if not turn:
            return html

        is_current = member.get("player_token") == turn["player_token"]
        has_clue = bool(context.get("member_clue"))
        is_alive = bool(member.get("alive"))
        turn_name = json.dumps(turn["name"], ensure_ascii=False)
        should_hide = json.dumps(bool(is_alive and not has_clue and not is_current))

        script = f"""
<script>
(() => {{
    const turnName = {turn_name};
    const shouldHide = {should_hide};
    const clueForm = document.querySelector('form[action$="/indice"]');
    if (!clueForm) return;

    const notice = document.createElement('p');
    notice.className = shouldHide ? 'muted' : 'message';
    notice.textContent = shouldHide
        ? `Attends : c’est au tour de ${{turnName}} de donner sa description.`
        : '🎙️ C’est à toi de donner ta description.';

    if (shouldHide) {{
        clueForm.replaceWith(notice);
    }} else {{
        clueForm.parentNode.insertBefore(notice, clueForm);
    }}
}})();
</script>
"""
        marker = "</body>"
        if marker in html:
            return html.replace(marker, script + marker, 1)
        return html + script

    _legacy.render_template = render_template_with_turn
