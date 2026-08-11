from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from pathlib import Path
from random import choice, randint, sample
import sqlite3
import os
import re
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "playbed.db"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "playbed-v2-dev-secret-change-me")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

GAMES = {
    "pendu": {
        "name": "Pendu",
        "emoji": "🪢",
        "description": "Trouve le mot avant de perdre toutes tes vies.",
        "tag": "Lettres",
    },
    "pom": {
        "name": "Plus ou Moins",
        "emoji": "🔢",
        "description": "Devine le nombre secret entre 0 et 100.",
        "tag": "Logique",
    },
    "vof": {
        "name": "Vrai ou Faux",
        "emoji": "🧠",
        "description": "Réponds à 10 affirmations et vise le sans-faute.",
        "tag": "Culture",
    },
    "quiz": {
        "name": "Quiz Express",
        "emoji": "⚡",
        "description": "10 questions à choix multiples pour tester ta culture.",
        "tag": "Quiz",
    },
    "memory": {
        "name": "Memory",
        "emoji": "🃏",
        "description": "Retrouve toutes les paires avec le moins de coups possible.",
        "tag": "Mémoire",
    },
}


def db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pseudo TEXT NOT NULL,
                game TEXT NOT NULL,
                points INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


def load_words():
    path = DATA_DIR / "mots.txt"
    with path.open(encoding="utf-8") as file:
        return [line.strip().lower() for line in file if line.strip()]


def load_vof_questions():
    with (DATA_DIR / "vof.json").open(encoding="utf-8") as file:
        return json_load(file)


def load_quiz_questions():
    with (DATA_DIR / "quiz.json").open(encoding="utf-8") as file:
        return json_load(file)


def json_load(file):
    import json
    return json.load(file)


def clean_pseudo(value):
    value = (value or "").strip()
    if not 2 <= len(value) <= 20:
        return None
    if not re.fullmatch(r"[A-Za-zÀ-ÿ0-9 _-]+", value):
        return None
    return value


def current_pseudo():
    return session.get("pseudo")


def save_score(game, points):
    pseudo = current_pseudo()
    if not pseudo or game not in GAMES:
        return
    points = max(0, min(int(points), 10000))
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO scores (pseudo, game, points, created_at) VALUES (?, ?, ?, ?)",
            (pseudo, game, points, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def new_game(game):
    if game == "pom":
        return {
            "game": game,
            "secret": randint(0, 100),
            "attempts": 0,
            "finished": False,
            "saved": False,
            "message": "Trouve le nombre entre 0 et 100.",
        }

    if game == "pendu":
        word = choice(load_words())
        return {
            "game": game,
            "word": word,
            "guessed": [],
            "lives": 10,
            "finished": False,
            "won": False,
            "saved": False,
            "message": "À toi de jouer !",
        }

    if game == "vof":
        questions = sample(load_vof_questions(), k=min(10, len(load_vof_questions())))
        return {
            "game": game,
            "questions": questions,
            "index": 0,
            "score": 0,
            "finished": False,
            "saved": False,
            "message": "Vrai ou faux ?",
        }

    if game == "quiz":
        questions = sample(load_quiz_questions(), k=min(10, len(load_quiz_questions())))
        return {
            "game": game,
            "questions": questions,
            "index": 0,
            "score": 0,
            "finished": False,
            "saved": False,
            "message": "Choisis la bonne réponse.",
        }

    if game == "memory":
        return {
            "game": game,
            "finished": False,
            "saved": False,
            "message": "Retrouve les 8 paires.",
        }

    return None


@app.before_request
def ensure_database():
    init_db()


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.route("/")
def home():
    with db_connection() as conn:
        total_scores = conn.execute("SELECT COUNT(*) AS n FROM scores").fetchone()["n"]
    return render_template(
        "index.html",
        games=GAMES,
        pseudo=current_pseudo(),
        total_scores=total_scores,
    )


@app.route("/pseudo", methods=["POST"])
def set_pseudo():
    pseudo = clean_pseudo(request.form.get("pseudo"))
    if pseudo:
        session["pseudo"] = pseudo
        return redirect(request.referrer or url_for("home"))
    return redirect(url_for("home", pseudo_error=1))


@app.route("/logout")
def clear_pseudo():
    session.pop("pseudo", None)
    session.pop("current_game", None)
    return redirect(url_for("home"))


@app.route("/start/<game>")
def start_game(game):
    if game not in GAMES:
        return redirect(url_for("home"))
    if not current_pseudo():
        return redirect(url_for("home", need_pseudo=1) + "#player")
    session["current_game"] = new_game(game)
    return redirect(url_for("play_game", game=game))


@app.route("/play/<game>", methods=["GET", "POST"])
def play_game(game):
    if game not in GAMES:
        return redirect(url_for("home"))
    if not current_pseudo():
        return redirect(url_for("home", need_pseudo=1) + "#player")

    state = session.get("current_game")
    if not state or state.get("game") != game:
        state = new_game(game)

    if request.method == "POST" and not state.get("finished"):
        if game == "pom":
            handle_pom(state)
        elif game == "pendu":
            handle_pendu(state)
        elif game == "vof":
            handle_vof(state)
        elif game == "quiz":
            handle_quiz(state)

    if state.get("finished") and not state.get("saved") and game != "memory":
        points = calculate_points(game, state)
        save_score(game, points)
        state["saved"] = True
        state["points"] = points

    session["current_game"] = state

    visible_word = None
    current_question = None

    if game == "pendu":
        visible_word = " ".join(
            c if (not c.isalpha() or c in state["guessed"]) else "_"
            for c in state["word"]
        )
    elif game in {"vof", "quiz"} and not state["finished"]:
        current_question = state["questions"][state["index"]]

    return render_template(
        "game.html",
        game=game,
        meta=GAMES[game],
        state=state,
        visible_word=visible_word,
        current_question=current_question,
        pseudo=current_pseudo(),
    )


def handle_pom(state):
    try:
        guess = int(request.form.get("guess", ""))
    except ValueError:
        state["message"] = "Entre un nombre valide."
        return

    if not 0 <= guess <= 100:
        state["message"] = "Le nombre doit être compris entre 0 et 100."
        return

    state["attempts"] += 1
    if guess < state["secret"]:
        state["message"] = "C'est plus !"
    elif guess > state["secret"]:
        state["message"] = "C'est moins !"
    else:
        state["finished"] = True
        state["message"] = f"Bravo ! Trouvé en {state['attempts']} essai(s)."


def handle_pendu(state):
    letter = request.form.get("letter", "").strip().lower()
    if len(letter) != 1 or not letter.isalpha():
        state["message"] = "Entre une seule lettre."
        return
    if letter in state["guessed"]:
        state["message"] = "Tu as déjà essayé cette lettre."
        return

    state["guessed"].append(letter)
    if letter not in state["word"]:
        state["lives"] -= 1
        state["message"] = "Raté !"
    else:
        state["message"] = "Bien joué !"

    hidden_left = any(
        c.isalpha() and c not in state["guessed"]
        for c in state["word"]
    )
    if not hidden_left:
        state["finished"] = True
        state["won"] = True
        state["message"] = "Bravo, tu as trouvé le mot !"
    elif state["lives"] <= 0:
        state["finished"] = True
        state["won"] = False
        state["message"] = f"Perdu. Le mot était : {state['word']}."


def handle_vof(state):
    answer = request.form.get("answer", "").lower()
    if answer not in {"vrai", "faux"}:
        return

    current = state["questions"][state["index"]]
    if answer == current["answer"]:
        state["score"] += 1
        state["message"] = "Bonne réponse !"
    else:
        state["message"] = f"Raté : la bonne réponse était {current['answer']}."

    state["index"] += 1
    if state["index"] >= len(state["questions"]):
        state["finished"] = True
        state["message"] += f" Score final : {state['score']}/{len(state['questions'])}."


def handle_quiz(state):
    answer = request.form.get("answer", "")
    current = state["questions"][state["index"]]
    if answer == current["answer"]:
        state["score"] += 1
        state["message"] = "Bonne réponse !"
    else:
        state["message"] = f"Raté : la bonne réponse était « {current['answer']} »."

    state["index"] += 1
    if state["index"] >= len(state["questions"]):
        state["finished"] = True
        state["message"] += f" Score final : {state['score']}/{len(state['questions'])}."


def calculate_points(game, state):
    if game == "pom":
        return max(100, 1200 - state["attempts"] * 70)
    if game == "pendu":
        return 0 if not state.get("won") else 500 + state["lives"] * 70
    if game in {"vof", "quiz"}:
        return state["score"] * 100
    return 0


@app.route("/api/memory-score", methods=["POST"])
def memory_score():
    if not current_pseudo():
        return jsonify({"ok": False, "error": "pseudo_required"}), 401

    data = request.get_json(silent=True) or {}
    try:
        moves = int(data.get("moves", 0))
        seconds = int(data.get("seconds", 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False}), 400

    if moves < 8 or seconds < 0:
        return jsonify({"ok": False}), 400

    points = max(100, 1800 - moves * 45 - seconds * 4)
    save_score("memory", points)
    return jsonify({"ok": True, "points": points})


@app.route("/restart/<game>")
def restart_game(game):
    if game in GAMES:
        session["current_game"] = new_game(game)
        return redirect(url_for("play_game", game=game))
    return redirect(url_for("home"))


@app.route("/classement")
def leaderboard():
    with db_connection() as conn:
        overall = conn.execute("""
            SELECT pseudo, SUM(points) AS total_points, COUNT(*) AS games_played
            FROM scores
            GROUP BY pseudo
            ORDER BY total_points DESC, games_played ASC
            LIMIT 50
        """).fetchall()

        best_by_game = {}
        for slug in GAMES:
            best_by_game[slug] = conn.execute("""
                SELECT pseudo, MAX(points) AS points
                FROM scores
                WHERE game = ?
                GROUP BY pseudo
                ORDER BY points DESC
                LIMIT 5
            """, (slug,)).fetchall()

    return render_template(
        "leaderboard.html",
        overall=overall,
        best_by_game=best_by_game,
        games=GAMES,
        pseudo=current_pseudo(),
    )


@app.route("/ads.txt")
def ads_txt():
    return send_from_directory(BASE_DIR, "ads.txt", mimetype="text/plain")


@app.route("/robots.txt")
def robots_txt():
    return send_from_directory(BASE_DIR, "robots.txt", mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    return send_from_directory(BASE_DIR, "sitemap.xml", mimetype="application/xml")


@app.route("/health")
def health():
    return {"status": "ok", "version": "2"}


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=True)
