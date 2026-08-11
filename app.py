from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from pathlib import Path
from random import choice, randint
import os
import secrets

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

GAMES = {
    "pendu": {"name": "Pendu", "emoji": "🪢", "description": "Trouve le mot avant de perdre toutes tes vies."},
    "pom": {"name": "Plus ou Moins", "emoji": "🔢", "description": "Devine le nombre secret entre 0 et 100."},
    "vof": {"name": "Vrai ou Faux", "emoji": "🧠", "description": "Teste tes connaissances avec une série de questions."},
}


def load_words():
    path = BASE_DIR / "mots.txt"
    with path.open(encoding="utf-8") as file:
        return [line.strip().lower() for line in file if line.strip()]


def load_questions():
    path = BASE_DIR / "questions.txt"
    questions = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            if "|" not in line:
                continue
            question, answer = line.strip().rsplit("|", 1)
            questions.append((question, answer.lower()))
    return questions


def new_game(game):
    if game == "pom":
        return {"game": game, "secret": randint(0, 100), "attempts": 0, "finished": False, "message": "Trouve le nombre entre 0 et 100."}

    if game == "pendu":
        word = choice(load_words())
        return {"game": game, "word": word, "guessed": [], "lives": 10, "finished": False, "won": False, "message": "À toi de jouer !"}

    if game == "vof":
        question, answer = choice(load_questions())
        return {"game": game, "question": question, "answer": answer, "score": 0, "round": 1, "finished": False, "message": "Vrai ou faux ?"}

    return None


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.route("/")
def home():
    return render_template("index.html", games=GAMES)


@app.route("/start/<game>")
def start_game(game):
    if game not in GAMES:
        return redirect(url_for("home"))
    session["current_game"] = new_game(game)
    return redirect(url_for("play_game", game=game))


@app.route("/play/<game>", methods=["GET", "POST"])
def play_game(game):
    if game not in GAMES:
        return redirect(url_for("home"))

    state = session.get("current_game")
    if not state or state.get("game") != game:
        state = new_game(game)

    if request.method == "POST" and not state.get("finished"):
        if game == "pom":
            try:
                guess = int(request.form.get("guess", ""))
            except ValueError:
                state["message"] = "Entre un nombre valide."
            else:
                if not 0 <= guess <= 100:
                    state["message"] = "Le nombre doit être compris entre 0 et 100."
                else:
                    state["attempts"] += 1
                    if guess < state["secret"]:
                        state["message"] = "C'est plus !"
                    elif guess > state["secret"]:
                        state["message"] = "C'est moins !"
                    else:
                        state["finished"] = True
                        state["message"] = f"Bravo ! Trouvé en {state['attempts']} essai(s)."

        elif game == "pendu":
            letter = request.form.get("letter", "").strip().lower()
            if len(letter) != 1 or not letter.isalpha():
                state["message"] = "Entre une seule lettre."
            elif letter in state["guessed"]:
                state["message"] = "Tu as déjà essayé cette lettre."
            else:
                state["guessed"].append(letter)
                if letter not in state["word"]:
                    state["lives"] -= 1
                    state["message"] = "Raté !"
                else:
                    state["message"] = "Bien joué !"

                visible = [c if c in state["guessed"] else "_" for c in state["word"]]
                if "_" not in visible:
                    state["finished"] = True
                    state["won"] = True
                    state["message"] = "Bravo, tu as trouvé le mot !"
                elif state["lives"] <= 0:
                    state["finished"] = True
                    state["message"] = f"Perdu. Le mot était : {state['word']}."

        elif game == "vof":
            answer = request.form.get("answer", "").lower()
            if answer in {"vrai", "faux"}:
                if answer == state["answer"]:
                    state["score"] += 1
                    state["message"] = "Bonne réponse !"
                else:
                    state["message"] = f"Raté : la bonne réponse était {state['answer']}."

                if state["round"] >= 10:
                    state["finished"] = True
                    state["message"] += f" Score final : {state['score']}/10."
                else:
                    state["round"] += 1
                    question, correct = choice(load_questions())
                    state["question"] = question
                    state["answer"] = correct

    session["current_game"] = state

    visible_word = None
    if game == "pendu":
        visible_word = " ".join(c if c in state["guessed"] else "_" for c in state["word"])

    return render_template("game.html", game=game, meta=GAMES[game], state=state, visible_word=visible_word)


@app.route("/restart/<game>")
def restart_game(game):
    if game in GAMES:
        session["current_game"] = new_game(game)
        return redirect(url_for("play_game", game=game))
    return redirect(url_for("home"))


@app.route("/ads.txt")
def ads_txt():
    return send_from_directory(BASE_DIR, "ads.txt", mimetype="text/plain")


@app.route("/robots.txt")
def robots_txt():
    return send_from_directory(BASE_DIR, "robots.txt", mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    return send_from_directory(BASE_DIR, "sitemap.xml", mimetype="application/xml")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=False)
