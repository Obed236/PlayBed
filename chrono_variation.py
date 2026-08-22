from random import choice

from flask import redirect, render_template, request, session, url_for

import extra_games as extra_games_module


MIN_TARGET_SECONDS = 5
MAX_TARGET_SECONDS = 30


def register_variable_chrono(app, games, game_content, save_score, current_pseudo):
    """Fait varier la durée cible du Chrono à chaque nouvelle partie."""

    games["chrono"]["name"] = "Chrono"
    games["chrono"]["description"] = (
        "Sans chronomètre visible, arrête le temps au plus près d’une durée choisie au hasard entre 5 et 30 secondes. "
        "La cible change à chaque nouvelle partie."
    )

    content = game_content.get("chrono")
    if content:
        content["headline"] = "Une nouvelle durée à viser à chaque partie."
        content["objective"] = (
            "Chrono teste ta perception du temps avec une cible différente à chaque partie. "
            "PlayBed choisit une durée entière entre 5 et 30 secondes, puis le chronomètre tourne sans afficher le temps écoulé."
        )
        content["rules"] = [
            "Une durée cible entre 5 et 30 secondes est choisie au début de chaque partie.",
            "La nouvelle cible est toujours différente de celle de la partie précédente.",
            "Le chronomètre démarre dès le lancement de la partie et aucun temps en cours n’est affiché.",
            "Appuie une seule fois sur « Stop » lorsque tu penses avoir atteint la durée demandée.",
            "Le résultat affiche ton temps réel et ton écart par rapport à la cible.",
        ]
        content["scoring"] = (
            "Plus ton temps est proche de la durée demandée, plus ton score est élevé. "
            "La même précision rapporte le même niveau de score, quelle que soit la cible."
        )

    def new_chrono_state():
        previous = session.get("extra_chrono")
        previous_target = previous.get("target") if isinstance(previous, dict) else None
        targets = [
            value
            for value in range(MIN_TARGET_SECONDS, MAX_TARGET_SECONDS + 1)
            if value != previous_target
        ]
        target = choice(targets)
        return {
            "game": "chrono",
            "target": target,
            "started_at": extra_games_module.time.time(),
            "finished": False,
            "saved": False,
            "message": f"Le chrono est parti. Arrête-le quand tu penses être à {target} secondes.",
        }

    # Le dispatcher des jeux supplémentaires résout cette fonction au moment
    # du démarrage : la remplacer ici suffit pour les nouvelles parties et
    # les redémarrages, y compris depuis un affrontement.
    extra_games_module._new_chrono_state = new_chrono_state

    def variable_chrono_view():
        if not current_pseudo():
            return redirect(url_for("home", need_pseudo=1) + "#player")

        state = session.get("extra_chrono")
        if not isinstance(state, dict) or "target" not in state:
            state = new_chrono_state()

        if request.method == "POST" and not state["finished"]:
            elapsed = max(0.0, extra_games_module.time.time() - float(state["started_at"]))
            target = float(state["target"])
            difference = abs(elapsed - target)
            state["elapsed"] = round(elapsed, 2)
            state["difference"] = round(difference, 2)
            state["points"] = max(100, 1500 - int(difference * 220))
            state["finished"] = True
            state["message"] = (
                f"Objectif : {int(target)}s. Tu as arrêté à {state['elapsed']:.2f}s, "
                f"soit {state['difference']:.2f}s d’écart."
            )
            if not state["saved"]:
                save_score("chrono", state["points"])
                state["saved"] = True

        session["extra_chrono"] = state
        return render_template(
            "extra_game.html",
            game="chrono",
            meta=games["chrono"],
            state=state,
            current_question=None,
            pseudo=current_pseudo(),
        )

    app.view_functions["extra_chrono"] = variable_chrono_view
