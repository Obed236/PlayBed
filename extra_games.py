import time
from collections import Counter
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
    "code": {
        "name": "Code Secret",
        "emoji": "🔐",
        "description": "Déduis un code de quatre chiffres grâce aux indices de position. Chaque tentative rapproche du bon code.",
        "tag": "Logique",
    },
    "suite": {
        "name": "Suites Logiques",
        "emoji": "🧩",
        "description": "Trouve le prochain nombre de 10 suites arithmétiques et teste ta capacité à repérer rapidement une règle.",
        "tag": "Logique",
    },
    "mot5": {
        "name": "Mot Mystère",
        "emoji": "🟩",
        "description": "Retrouve un mot français de cinq lettres en six essais grâce aux indices sur les lettres bien ou mal placées.",
        "tag": "Lettres",
    },
}

EXTRA_GAME_CONTENT = {
    "calcul": {
        "headline": "Dix opérations pour tester ta vitesse de calcul.",
        "objective": "Calcul Mental propose dix additions, soustractions ou multiplications générées par le serveur. L’objectif est de répondre juste tout en gardant un bon rythme.",
        "rules": ["Une partie contient 10 opérations.", "Entre une réponse numérique puis valide-la.", "Les questions avancent une par une.", "Le score final dépend du nombre de bonnes réponses et du temps écoulé."],
        "scoring": "Chaque bonne réponse rapporte une base importante de points. Un bonus de rapidité est ajouté à la fin de la série.",
        "tips": ["Lis le signe avant de calculer.", "Privilégie la précision : une erreur coûte plus qu’une seconde gagnée.", "Pour les multiplications, décompose mentalement les nombres lorsque c’est utile."],
        "skills": "Calcul mental, concentration et rapidité.",
    },
    "melange": {
        "headline": "Retrouve le mot à partir de ses lettres mélangées.",
        "objective": "Mot Mélangé sélectionne un mot puis en mélange les lettres. Tu dois reconstruire le mot original en utilisant le moins d’essais possible.",
        "rules": ["Un mot est choisi au début de la partie.", "Toutes ses lettres sont affichées dans un ordre différent.", "Tu disposes de cinq essais pour retrouver le mot.", "La partie se termine dès que le mot est trouvé ou après le cinquième essai."],
        "scoring": "Trouver le mot rapidement rapporte davantage de points. Le score diminue à chaque tentative supplémentaire.",
        "tips": ["Repère d’abord les voyelles et les groupes de consonnes plausibles.", "Cherche les terminaisons françaises fréquentes.", "Teste mentalement plusieurs positions avant de valider une réponse."],
        "skills": "Vocabulaire, reconnaissance de motifs et déduction.",
    },
    "code": {
        "headline": "Quatre chiffres, des indices et une seule combinaison correcte.",
        "objective": "Code Secret te demande de retrouver quatre chiffres différents. Après chaque tentative, PlayBed indique combien de chiffres sont à la bonne place et combien sont présents mais mal placés.",
        "rules": ["Le code contient quatre chiffres différents.", "Chaque proposition doit contenir exactement quatre chiffres.", "Un indice « bien placé » signifie que le chiffre et sa position sont corrects.", "Un indice « mal placé » signifie que le chiffre existe dans le code mais à une autre position.", "Tu disposes de dix tentatives."],
        "scoring": "Une résolution rapide rapporte davantage de points. Le score diminue avec chaque tentative utilisée.",
        "tips": ["Commence par quatre chiffres différents.", "Utilise les indices pour éliminer des positions plutôt que changer tout le code.", "Quand quatre chiffres sont identifiés, concentre-toi uniquement sur leur ordre."],
        "skills": "Déduction, logique et élimination de possibilités.",
    },
    "suite": {
        "headline": "Repère la règle et trouve le nombre suivant.",
        "objective": "Suites Logiques propose dix séries de nombres construites autour d’un écart régulier. Ton objectif est de reconnaître cet écart et calculer le terme suivant.",
        "rules": ["Une partie contient dix suites.", "Quatre nombres sont affichés à chaque question.", "Entre le nombre qui vient logiquement ensuite.", "Chaque réponse est validée côté serveur."],
        "scoring": "Chaque bonne réponse rapporte 100 points. Un bonus est accordé pour un sans-faute.",
        "tips": ["Calcule la différence entre deux termes consécutifs.", "Vérifie que la même différence fonctionne sur toute la série.", "Prends quelques secondes pour éviter une erreur de calcul simple."],
        "skills": "Raisonnement numérique, observation et calcul mental.",
    },
    "mot5": {
        "headline": "Un mot de cinq lettres à retrouver en six essais.",
        "objective": "Mot Mystère te donne des indices après chaque proposition : une lettre verte est bien placée, une lettre jaune est présente ailleurs et une lettre grise n’est pas retenue à cette position dans le mot cible.",
        "rules": ["Le mot cible contient cinq lettres.", "Chaque proposition doit contenir exactement cinq lettres.", "Vert signifie bien placé, jaune signifie présent mais mal placé.", "Tu disposes de six essais."],
        "scoring": "Plus le mot est trouvé tôt, plus le score est élevé. Une partie perdue ne rapporte pas de point.",
        "tips": ["Commence avec un mot contenant plusieurs voyelles et consonnes fréquentes.", "Réutilise les lettres vertes à la même position.", "Déplace les lettres jaunes pour tester de nouvelles positions."],
        "skills": "Vocabulaire, déduction et reconnaissance de motifs.",
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
    return {"game": "calcul", "questions": questions, "index": 0, "correct": 0, "started_at": time.time(), "finished": False, "saved": False, "message": "À toi de calculer !"}


def _scramble(word):
    letters = list(word)
    for _ in range(10):
        shuffled = "".join(sample(letters, len(letters)))
        if shuffled.lower() != word.lower():
            return shuffled
    return "".join(reversed(letters))


def _eligible_words(load_words, length=None):
    words = [word.strip().lower() for word in load_words() if word.strip().isalpha()]
    if length is not None:
        words = [word for word in words if len(word) == length]
    return words


def _new_melange_state(load_words):
    eligible = [word for word in _eligible_words(load_words) if 5 <= len(word) <= 10]
    word = choice(eligible or _eligible_words(load_words)).lower()
    return {"game": "melange", "word": word, "scrambled": _scramble(word).upper(), "attempts": 0, "finished": False, "won": False, "saved": False, "message": "Remets les lettres dans le bon ordre."}


def _new_code_state():
    secret = "".join(str(number) for number in sample(range(10), 4))
    return {"game": "code", "secret": secret, "attempts": 0, "history": [], "finished": False, "won": False, "saved": False, "message": "Trouve le code à quatre chiffres."}


def _code_feedback(secret, guess):
    exact = sum(a == b for a, b in zip(secret, guess))
    common = sum((Counter(secret) & Counter(guess)).values())
    return exact, common - exact


def _new_suite_state():
    questions = []
    for _ in range(10):
        start = randint(1, 40)
        step = choice([2, 3, 4, 5, 6, 7, 8, 9, 10, 12])
        values = [start + step * index for index in range(4)]
        questions.append({"label": " · ".join(str(value) for value in values) + " · ?", "answer": values[-1] + step})
    return {"game": "suite", "questions": questions, "index": 0, "correct": 0, "finished": False, "saved": False, "message": "Quel nombre vient ensuite ?"}


def _new_mot5_state(load_words):
    words = _eligible_words(load_words, 5)
    if not words:
        words = ["table", "livre", "route", "porte", "monde", "plage"]
    word = choice(words)
    return {"game": "mot5", "word": word, "attempts": 0, "history": [], "finished": False, "won": False, "saved": False, "message": "Trouve le mot de cinq lettres."}


def _word_feedback(secret, guess):
    result = ["absent"] * len(secret)
    remaining = Counter()
    for index, (target, proposed) in enumerate(zip(secret, guess)):
        if target == proposed:
            result[index] = "correct"
        else:
            remaining[target] += 1
    for index, proposed in enumerate(guess):
        if result[index] == "correct":
            continue
        if remaining[proposed] > 0:
            result[index] = "present"
            remaining[proposed] -= 1
    return result


def register_extra_games(app, games, current_pseudo, save_score, load_words):
    original_start = app.view_functions["start_game"]
    original_play = app.view_functions["play_game"]
    original_restart = app.view_functions["restart_game"]
    route_for = {"calcul": "extra_calcul", "melange": "extra_melange", "code": "extra_code", "suite": "extra_suite", "mot5": "extra_mot5"}

    def start_dispatch(game):
        if game in route_for:
            if not current_pseudo():
                return redirect(url_for("home", need_pseudo=1) + "#player")
            if game == "calcul": session["extra_calcul"] = _new_calcul_state()
            elif game == "melange": session["extra_melange"] = _new_melange_state(load_words)
            elif game == "code": session["extra_code"] = _new_code_state()
            elif game == "suite": session["extra_suite"] = _new_suite_state()
            elif game == "mot5": session["extra_mot5"] = _new_mot5_state(load_words)
            return redirect(url_for(route_for[game]))
        return original_start(game)

    def play_dispatch(game):
        if game in route_for:
            return redirect(url_for(route_for[game]))
        return original_play(game)

    def restart_dispatch(game):
        if game in route_for:
            return start_dispatch(game)
        return original_restart(game)

    app.view_functions["start_game"] = start_dispatch
    app.view_functions["play_game"] = play_dispatch
    app.view_functions["restart_game"] = restart_dispatch

    @app.route("/arcade/calcul", methods=["GET", "POST"])
    def extra_calcul():
        if not current_pseudo(): return redirect(url_for("home", need_pseudo=1) + "#player")
        state = session.get("extra_calcul") or _new_calcul_state()
        if request.method == "POST" and not state["finished"]:
            try: answer = int(request.form.get("answer", ""))
            except ValueError: state["message"] = "Entre un nombre valide."
            else:
                current = state["questions"][state["index"]]
                if answer == current["answer"]: state["correct"] += 1; state["message"] = "Bonne réponse !"
                else: state["message"] = f"La bonne réponse était {current['answer']}."
                state["index"] += 1
                if state["index"] >= len(state["questions"]):
                    state["finished"] = True
                    elapsed = max(1, int(time.time() - float(state["started_at"])))
                    state["elapsed"] = elapsed
                    state["points"] = state["correct"] * 100 + max(0, 500 - elapsed * 3)
                    if not state["saved"]: save_score("calcul", state["points"]); state["saved"] = True
                    state["message"] = f"Terminé : {state['correct']}/10 en {elapsed}s."
        session["extra_calcul"] = state
        current_question = None if state["finished"] else state["questions"][state["index"]]
        return render_template("extra_game.html", game="calcul", meta=games["calcul"], state=state, current_question=current_question, pseudo=current_pseudo())

    @app.route("/arcade/mot-melange", methods=["GET", "POST"])
    def extra_melange():
        if not current_pseudo(): return redirect(url_for("home", need_pseudo=1) + "#player")
        state = session.get("extra_melange") or _new_melange_state(load_words)
        if request.method == "POST" and not state["finished"]:
            guess = (request.form.get("guess") or "").strip().lower()
            state["attempts"] += 1
            if guess == state["word"]:
                state["finished"], state["won"] = True, True
                state["points"] = max(200, 1300 - state["attempts"] * 140)
                state["message"] = f"Bravo ! Le mot était « {state['word']} »."
            elif state["attempts"] >= 5:
                state["finished"], state["won"], state["points"] = True, False, 0
                state["message"] = f"Perdu. Le mot était « {state['word']} »."
            else: state["message"] = f"Ce n’est pas le bon mot. Il te reste {5 - state['attempts']} essai(s)."
            if state["finished"] and not state["saved"]: save_score("melange", state["points"]); state["saved"] = True
        session["extra_melange"] = state
        return render_template("extra_game.html", game="melange", meta=games["melange"], state=state, current_question=None, pseudo=current_pseudo())

    @app.route("/arcade/code-secret", methods=["GET", "POST"])
    def extra_code():
        if not current_pseudo(): return redirect(url_for("home", need_pseudo=1) + "#player")
        state = session.get("extra_code") or _new_code_state()
        if request.method == "POST" and not state["finished"]:
            guess = (request.form.get("guess") or "").strip()
            if len(guess) != 4 or not guess.isdigit():
                state["message"] = "Entre exactement quatre chiffres."
            else:
                state["attempts"] += 1
                exact, misplaced = _code_feedback(state["secret"], guess)
                state["history"].append({"guess": guess, "exact": exact, "misplaced": misplaced})
                if exact == 4:
                    state["finished"], state["won"] = True, True
                    state["points"] = max(250, 1700 - state["attempts"] * 130)
                    state["message"] = "Code trouvé !"
                elif state["attempts"] >= 10:
                    state["finished"], state["won"], state["points"] = True, False, 0
                    state["message"] = f"Perdu. Le code était {state['secret']}."
                else: state["message"] = f"{exact} bien placé(s), {misplaced} mal placé(s)."
                if state["finished"] and not state["saved"]: save_score("code", state["points"]); state["saved"] = True
        session["extra_code"] = state
        return render_template("extra_game.html", game="code", meta=games["code"], state=state, current_question=None, pseudo=current_pseudo())

    @app.route("/arcade/suites-logiques", methods=["GET", "POST"])
    def extra_suite():
        if not current_pseudo(): return redirect(url_for("home", need_pseudo=1) + "#player")
        state = session.get("extra_suite") or _new_suite_state()
        if request.method == "POST" and not state["finished"]:
            try: answer = int(request.form.get("answer", ""))
            except ValueError: state["message"] = "Entre un nombre valide."
            else:
                current = state["questions"][state["index"]]
                if answer == current["answer"]: state["correct"] += 1; state["message"] = "Bonne réponse !"
                else: state["message"] = f"La réponse était {current['answer']}."
                state["index"] += 1
                if state["index"] >= len(state["questions"]):
                    state["finished"] = True
                    state["points"] = state["correct"] * 100 + (200 if state["correct"] == 10 else 0)
                    if not state["saved"]: save_score("suite", state["points"]); state["saved"] = True
                    state["message"] = f"Terminé : {state['correct']}/10."
        session["extra_suite"] = state
        current_question = None if state["finished"] else state["questions"][state["index"]]
        return render_template("extra_game.html", game="suite", meta=games["suite"], state=state, current_question=current_question, pseudo=current_pseudo())

    @app.route("/arcade/mot-mystere", methods=["GET", "POST"])
    def extra_mot5():
        if not current_pseudo(): return redirect(url_for("home", need_pseudo=1) + "#player")
        state = session.get("extra_mot5") or _new_mot5_state(load_words)
        if request.method == "POST" and not state["finished"]:
            guess = (request.form.get("guess") or "").strip().lower()
            if len(guess) != 5 or not guess.isalpha():
                state["message"] = "Entre exactement cinq lettres."
            else:
                state["attempts"] += 1
                feedback = _word_feedback(state["word"], guess)
                state["history"].append({"guess": guess.upper(), "feedback": feedback})
                if guess == state["word"]:
                    state["finished"], state["won"] = True, True
                    state["points"] = max(250, 1600 - state["attempts"] * 160)
                    state["message"] = f"Bravo ! Le mot était {state['word'].upper()}."
                elif state["attempts"] >= 6:
                    state["finished"], state["won"], state["points"] = True, False, 0
                    state["message"] = f"Perdu. Le mot était {state['word'].upper()}."
                else: state["message"] = f"Essai {state['attempts']}/6. Continue !"
                if state["finished"] and not state["saved"]: save_score("mot5", state["points"]); state["saved"] = True
        session["extra_mot5"] = state
        return render_template("extra_game.html", game="mot5", meta=games["mot5"], state=state, current_question=None, pseudo=current_pseudo())
