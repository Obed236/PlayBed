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
    "suite": {
        "name": "Suite Logique",
        "emoji": "🔢",
        "description": "Observe une suite de nombres et trouve le terme suivant. Dix manches pour tester ton raisonnement et ta rapidité.",
        "tag": "Logique",
    },
    "pair": {
        "name": "Pair ou Impair",
        "emoji": "⚖️",
        "description": "Classe rapidement 15 nombres en pair ou impair. La précision et la vitesse déterminent ton score final.",
        "tag": "Rapidité",
    },
    "chrono": {
        "name": "Chrono 10",
        "emoji": "⏱️",
        "description": "Sans chronomètre visible, arrête le temps le plus près possible de 10 secondes. Chaque centième compte.",
        "tag": "Rapidité",
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
    "suite": {
        "headline": "Repère la règle et trouve le nombre suivant.",
        "objective": "Suite Logique affiche dix suites numériques générées aléatoirement. Chaque suite suit une progression simple que tu dois identifier avant de proposer le terme suivant.",
        "rules": [
            "Une partie contient 10 suites.",
            "Observe les quatre nombres affichés.",
            "Entre le nombre qui doit logiquement suivre.",
            "La réponse correcte est révélée après chaque tentative.",
        ],
        "scoring": "Chaque bonne réponse vaut 100 points, avec un bonus de rapidité à la fin de la partie.",
        "tips": [
            "Commence par regarder la différence entre deux termes consécutifs.",
            "Vérifie que la même règle fonctionne sur toute la suite.",
            "Ne complique pas trop vite : les suites proposées restent volontairement lisibles.",
        ],
        "skills": "Raisonnement logique, calcul mental et reconnaissance de motifs.",
    },
    "pair": {
        "headline": "Pair ou impair, sans perdre le rythme.",
        "objective": "Pair ou Impair enchaîne quinze nombres. Tu dois déterminer immédiatement si chacun est divisible par deux.",
        "rules": [
            "Une partie contient 15 nombres.",
            "Choisis « Pair » ou « Impair » pour chaque nombre.",
            "La partie avance immédiatement après ton choix.",
            "Le score final dépend des bonnes réponses et du temps total.",
        ],
        "scoring": "Chaque bonne réponse rapporte des points et un bonus récompense les parties rapides.",
        "tips": [
            "Regarde uniquement le dernier chiffre du nombre.",
            "0, 2, 4, 6 et 8 indiquent toujours un nombre pair.",
            "Ne relis pas tout le nombre : concentre-toi sur son unité.",
        ],
        "skills": "Automatisme numérique, concentration et rapidité.",
    },
    "chrono": {
        "headline": "Arrête le temps au plus près de 10 secondes.",
        "objective": "Chrono 10 teste ta perception du temps. Dès que la partie commence, aucun chronomètre ne s’affiche : compte mentalement puis arrête quand tu penses que 10 secondes se sont écoulées.",
        "rules": [
            "Le chronomètre démarre au lancement de la partie.",
            "Aucune durée en cours n’est affichée.",
            "Appuie une seule fois sur « Stop » lorsque tu penses être à 10 secondes.",
            "Le résultat affiche ensuite ton temps réel et ton écart.",
        ],
        "scoring": "Plus ton temps est proche de 10,00 secondes, plus ton score est élevé. Un résultat très éloigné rapporte peu de points.",
        "tips": [
            "Compte avec un rythme régulier plutôt qu’en accélérant.",
            "Évite de regarder une horloge extérieure pour garder l’intérêt du défi.",
            "Compare plusieurs tentatives pour ajuster ton rythme mental.",
        ],
        "skills": "Perception temporelle, concentration et contrôle du rythme.",
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


def _new_suite_state():
    questions = []
    for _ in range(10):
        start = randint(1, 35)
        step = choice([2, 3, 4, 5, 6, 7, -2, -3, -4])
        values = [start + step * index for index in range(4)]
        questions.append({"label": " · ".join(str(value) for value in values) + " · ?", "answer": start + step * 4})
    return {
        "game": "suite",
        "questions": questions,
        "index": 0,
        "correct": 0,
        "started_at": time.time(),
        "finished": False,
        "saved": False,
        "message": "Trouve le nombre suivant.",
    }


def _new_pair_state():
    numbers = [randint(10, 999) for _ in range(15)]
    return {
        "game": "pair",
        "numbers": numbers,
        "index": 0,
        "correct": 0,
        "started_at": time.time(),
        "finished": False,
        "saved": False,
        "message": "Pair ou impair ?",
    }


def _new_chrono_state():
    return {
        "game": "chrono",
        "started_at": time.time(),
        "finished": False,
        "saved": False,
        "message": "Le chrono est parti. Arrête-le quand tu penses être à 10 secondes.",
    }


def _finish_accuracy_game(state, save_score, game, correct, total, elapsed, speed_pool, speed_cost):
    state["finished"] = True
    state["elapsed"] = elapsed
    state["points"] = correct * 100 + max(0, speed_pool - elapsed * speed_cost)
    if not state["saved"]:
        save_score(game, state["points"])
        state["saved"] = True
    state["message"] = f"Terminé : {correct}/{total} en {elapsed}s."


def register_extra_games(app, games, current_pseudo, save_score, load_words):
    original_start = app.view_functions["start_game"]
    original_play = app.view_functions["play_game"]
    original_restart = app.view_functions["restart_game"]

    route_by_game = {
        "calcul": "extra_calcul",
        "melange": "extra_melange",
        "suite": "extra_suite",
        "pair": "extra_pair",
        "chrono": "extra_chrono",
    }

    def start_dispatch(game):
        if game in route_by_game:
            if not current_pseudo():
                return redirect(url_for("home", need_pseudo=1) + "#player")
            if game == "calcul":
                session["extra_calcul"] = _new_calcul_state()
            elif game == "melange":
                session["extra_melange"] = _new_melange_state(load_words)
            elif game == "suite":
                session["extra_suite"] = _new_suite_state()
            elif game == "pair":
                session["extra_pair"] = _new_pair_state()
            elif game == "chrono":
                session["extra_chrono"] = _new_chrono_state()
            return redirect(url_for(route_by_game[game]))
        return original_start(game)

    def play_dispatch(game):
        if game in route_by_game:
            return redirect(url_for(route_by_game[game]))
        return original_play(game)

    def restart_dispatch(game):
        if game in route_by_game:
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
                    elapsed = max(1, int(time.time() - float(state["started_at"])))
                    _finish_accuracy_game(state, save_score, "calcul", state["correct"], 10, elapsed, 500, 3)
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

    @app.route("/arcade/suite-logique", methods=["GET", "POST"])
    def extra_suite():
        if not current_pseudo():
            return redirect(url_for("home", need_pseudo=1) + "#player")
        state = session.get("extra_suite") or _new_suite_state()
        if request.method == "POST" and not state["finished"]:
            try:
                answer = int(request.form.get("answer", ""))
            except ValueError:
                state["message"] = "Entre un nombre valide."
            else:
                current = state["questions"][state["index"]]
                if answer == current["answer"]:
                    state["correct"] += 1
                    state["message"] = "Bonne déduction !"
                else:
                    state["message"] = f"La réponse était {current['answer']}."
                state["index"] += 1
                if state["index"] >= len(state["questions"]):
                    elapsed = max(1, int(time.time() - float(state["started_at"])))
                    _finish_accuracy_game(state, save_score, "suite", state["correct"], 10, elapsed, 400, 2)
        session["extra_suite"] = state
        current_question = None if state["finished"] else state["questions"][state["index"]]
        return render_template("extra_game.html", game="suite", meta=games["suite"], state=state, current_question=current_question, pseudo=current_pseudo())

    @app.route("/arcade/pair-impair", methods=["GET", "POST"])
    def extra_pair():
        if not current_pseudo():
            return redirect(url_for("home", need_pseudo=1) + "#player")
        state = session.get("extra_pair") or _new_pair_state()
        if request.method == "POST" and not state["finished"]:
            answer = (request.form.get("answer") or "").lower()
            if answer in {"pair", "impair"}:
                number = int(state["numbers"][state["index"]])
                expected = "pair" if number % 2 == 0 else "impair"
                if answer == expected:
                    state["correct"] += 1
                    state["message"] = "Exact !"
                else:
                    state["message"] = f"{number} est {expected}."
                state["index"] += 1
                if state["index"] >= len(state["numbers"]):
                    elapsed = max(1, int(time.time() - float(state["started_at"])))
                    state["finished"] = True
                    state["elapsed"] = elapsed
                    state["points"] = state["correct"] * 80 + max(0, 300 - elapsed * 2)
                    if not state["saved"]:
                        save_score("pair", state["points"])
                        state["saved"] = True
                    state["message"] = f"Terminé : {state['correct']}/15 en {elapsed}s."
        session["extra_pair"] = state
        current_question = None if state["finished"] else {"number": state["numbers"][state["index"]]}
        return render_template("extra_game.html", game="pair", meta=games["pair"], state=state, current_question=current_question, pseudo=current_pseudo())

    @app.route("/arcade/chrono-10", methods=["GET", "POST"])
    def extra_chrono():
        if not current_pseudo():
            return redirect(url_for("home", need_pseudo=1) + "#player")
        state = session.get("extra_chrono") or _new_chrono_state()
        if request.method == "POST" and not state["finished"]:
            elapsed = max(0.0, time.time() - float(state["started_at"]))
            difference = abs(elapsed - 10.0)
            state["elapsed"] = round(elapsed, 2)
            state["difference"] = round(difference, 2)
            state["points"] = max(100, 1500 - int(difference * 220))
            state["finished"] = True
            state["message"] = f"Tu as arrêté à {state['elapsed']:.2f}s, soit {state['difference']:.2f}s d’écart."
            if not state["saved"]:
                save_score("chrono", state["points"])
                state["saved"] = True
        session["extra_chrono"] = state
        return render_template("extra_game.html", game="chrono", meta=games["chrono"], state=state, current_question=None, pseudo=current_pseudo())
