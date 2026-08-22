from functools import wraps

from flask import redirect, session, url_for
from werkzeug.exceptions import Forbidden


# Les routes Action ou Vérité restent protégées : une action non autorisée
# n'est jamais exécutée. En revanche, au lieu d'afficher la page Flask 403,
# on ramène le joueur vers un écran où il peut continuer ou rejoindre la salle.
RECOVERABLE_ENDPOINTS = (
    "av_room_start",
    "av_room_choose",
    "av_room_next",
    "av_room_close",
    "av_room_answer",
    "av_room_preference",
)


def register_action_verite_recovery(app):
    def safe_redirect(code):
        code = str(code or "").strip()
        memberships = session.get("av_memberships")
        has_membership = isinstance(memberships, dict) and bool(memberships.get(code))

        if len(code) == 4 and code.isdigit():
            if has_membership:
                return redirect(url_for("av_room", code=code))
            return redirect(url_for("av_join_room", code=code))
        return redirect(url_for("av_home"))

    for endpoint in RECOVERABLE_ENDPOINTS:
        original = app.view_functions.get(endpoint)
        if not original:
            continue

        @wraps(original)
        def protected_view(*args, __original=original, **kwargs):
            try:
                return __original(*args, **kwargs)
            except Forbidden:
                # Cas courant à distance : un autre téléphone a déjà fait
                # avancer la partie, la salle a changé d'état ou la session
                # n'est plus reconnue. On ne réalise pas l'action demandée ;
                # on renvoie simplement vers l'état actuel de la salle.
                return safe_redirect(kwargs.get("code"))

        app.view_functions[endpoint] = protected_view
