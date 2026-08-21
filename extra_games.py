import time
from random import choice, randint, sample

from flask import redirect, render_template, request, session, url_for

EXTRA_GAMES = {
    "calcul": {
        "name": "Calcul Mental",
        "emoji": "🧮",
        "description": "Résous 10 opérations le plus précisément et rapidement possible. Les bonnes réponses et le temps total déterminent ton score.",
        "tag": "Logique",
    },
    "melange": {
        "name": "Mot Mélangé",
        "emoji": "🔀",
        "description": "Remets les lettres dans le bon ordre pour retrouver le mot caché. Moins tu utilises d'essais, meilleur est ton score.",
        "tag": "Lettres",
    },
}

EXTRA_GAME_CONTENT = {
    "calcul": {
        "headline": "Dix opérations pour tester ta vitesse de calcul.",
        "objective": "Calcul Mental propose dix additions, soustractions ou multiplications générées par le serveur. L’objectif est de répondre juste tout en gardant un bon rythme.",
        "rules": [
            "Une partie contient 10 opérations.",
            "Entre une réponse numérique puis valide-la.",
            "Les questions avancent une par une.",
            "Le score final dépend du nombre de bonnes réponses et du temps écoulé.",
        ],
        "scoring": "Chaque bonne réponse rapporte une base importante de points. Un bonus de rapidité est ajouté à la fin de la série.",
        "tips": [
            "Lis le signe avant de calculer.",
            "Privilégie la précision : une erreur coûte plus qu’une seconde gagnée.",
            "Pour les multiplications, décompose mentalement les nombres lorsque c’est utile.",
        ],
        "skills": "Calcul mental, concentration et rapidité.",
    },
    "melange": {
        "headline": "Retrouve le mot à partir de ses lettres mélangées.",
        "objective": "Mot Mélangé sélectionne un mot puis en mélange les lettres. Tu dois reconstruire le mot original en utilisant le moins d’essais possible.",
        "rules": [
            "Un mot est choisi au début de la partie.",
            "Toutes ses lettres sont affichées dans un ordre différent.",
            "Tu disposes de cinq essais pour retrouver le mot.",
            "La partie se termine dès que le mot est trouvé ou après le cinquième essai.",
        ],
        "scoring": "Trouver le mot rapidement rapporte davantage de points. Le score diminue à chaque tentative supplémentaire.",
        "tips": [
            "Repère d’abord les voyelles et les groupes de consonnes plausibles.",
            "Cherche les terminaisons françaises fréquentes.",
            "Teste mentalement plusieurs positions avant de valider une réponse.",
        ],
        "skills": "Vocabulaire, reconnaissance de motifs et déduction.",
    },
}


def _new_calcul_state():
    questions = []
    for _ in range(10):
        operation = choice(("+", "-", "×"))
        if operation == "+":
            a, b = randint(5, 70), randint(5, 70)
            answer = a + b
        elif operation == "-":
            a, b = randint(20, 99), randint(2, 60)
            if b > a:
                a, b = b, a
            answer = a - b
        else:
            a, b = randint(2, 12), randint(2, 12)
            answer = a * b
        questions.append({"label": f"{a} {operation} {b}", "answer": answer})
    return {
        "game": "calcul",
        "questions": questions,
        "index": 0,
        "correct": 0,
        "started_at": time.time(),
        "finished": False,
        "saved": False,
        "message": "À toi de calculer !",
    }


def _scramble(word):
    letters = list(word)
    for _ in range(10):
        shuffled = "".join(sample(letters, len(letters)))
        if shuffled.lower() != word.lower():
            return shuffled
    return "".join(reversed(letters))


def _new_melange_state(load_words):
    eligible = [word for word in load_words() if 5 <= len(word) <= 10 and word.isalpha()]
    word = choice(eligible or load_words()).lower()
    return {
        "game": "melange",
        "word": word,
        "scrambled": _scramble(word).upper(),
        "attempts": 0,
        "finished": False,
        "won": False,
        "saved": False,
        "message": "Remets les lettres dans le bon ordre.",
    }


def register_extra_games(app, games, current_pseudo, save_score, load_words):
    original_start = app.view_functions["start_game"]
    original_play = app.view_functions["play_game"]
    original_restart = app.view_functions["restart_game"]

    def start_dispatch(game):
        if game == "calcul":
            if not current_pseudo():
                return redirect(url_for("home", need_pseudo=1) + "#player")
            session["extra_calcul"] = _new_calcul_state()
            return redirect(url_for("extra_calcul"))
        if game == "melange":
            if not current_pseudo():
                return redirect(url_for("home", need_pseudo=1) + "#player")
            session["extra_melange"] = _new_melange_state(load_words)
            return redirect(url_for("extra_melange"))
        return original_start(game)

    def play_dispatch(game):
        if game == "calcul":
            return redirect(url_for("extra_calcul"))
        if game == "melange":
            return redirect(url_for("extra_melange"))
        return original_play(game)

    def restart_dispatch(game):
        if game in {"calcul", "melange"}:
            return start_dispatch(game)
        return original_restart(game)

    app.view_functions["start_game"] = start_dispatch
    app.view_functions["play_game"] = play_dispatch
    app.view_functions["restart_game"] = restart_dispatch

    @app.route("/arcade/calcul", methods=["GET", "POST"])
    def extra_calcul():
        if not current_pseudo():
            return redirect(url_for("home", need_pseudo=1) + "#player")
        state = session.get("extra_calcul") or _new_calcul_state()
        if request.method == "POST" and not state["finished"]:
            try:
                answer = int(request.form.get("answer", ""))
            except ValueError:
                state["message"] = "Entre un nombre valide."
            else:
                current = state["questions"][state["index"]]
                if answer == current["answer"]:
                    state["correct"] += 1
                    state["message"] = "Bonne réponse !"
                else:
                    state["message"] = f"La bonne réponse était {current['answer']}."
                state["index"] += 1
                if state["index"] >= len(state["questions"]):
                    state["finished"] = True
                    elapsed = max(1, int(time.time() - float(state["started_at"])))
                    state["elapsed"] = elapsed
                    state["points"] = state["correct"] * 100 + max(0, 500 - elapsed * 3)
                    if not state["saved"]:
                        save_score("calcul", state["points"])
                        state["saved"] = True
                    state["message"] = f"Terminé : {state['correct']}/10 en {elapsed}s."
        session["extra_calcul"] = state
        current_question = None if state["finished"] else state["questions"][state["index"]]
        return render_template("extra_game.html", game="calcul", meta=games["calcul"], state=state, current_question=current_question, pseudo=current_pseudo())

    @app.route("/arcade/mot-melange", methods=["GET", "POST"])
    def extra_melange():
        if not current_pseudo():
            return redirect(url_for("home", need_pseudo=1) + "#player")
        state = session.get("extra_melange") or _new_melange_state(load_words)
        if request.method == "POST" and not state["finished"]:
            guess = (request.form.get("guess") or "").strip().lower()
            state["attempts"] += 1
            if guess == state["word"]:
                state["finished"] = True
                state["won"] = True
                state["points"] = max(200, 1300 - state["attempts"] * 140)
                state["message"] = f"Bravo ! Le mot était « {state['word']} »."
            elif state["attempts"] >= 5:
                state["finished"] = True
                state["won"] = False
                state["points"] = 0
                state["message"] = f"Perdu. Le mot était « {state['word']} »."
            else:
                state["message"] = f"Ce n’est pas le bon mot. Il te reste {5 - state['attempts']} essai(s)."
            if state["finished"] and not state["saved"]:
                save_score("melange", state["points"])
                state["saved"] = True
        session["extra_melange"] = state
        return render_template("extra_game.html", game="melange", meta=games["melange"], state=state, current_question=None, pseudo=current_pseudo())
