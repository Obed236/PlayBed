from flask import render_template

LANGUAGES = {
    "en": {
        "html_lang": "en",
        "name": "English",
        "title": "PlayBed — Free browser mini-games",
        "description": "Discover PlayBed, a free browser gaming platform with ten mini-games, levels, missions, rankings and player challenges.",
        "eyebrow": "PLAYBED INTERNATIONAL · ENGLISH BETA",
        "heading": "Play. Progress. Challenge your friends.",
        "intro": "PlayBed is a free browser gaming platform built around short sessions, progression, missions, public player profiles and rankings. No download is required.",
        "catalog_title": "10 games available",
        "catalog_intro": "The platform currently includes ten games covering words, logic, memory, speed and general knowledge. Gameplay is still primarily in French while international versions are being prepared.",
        "play": "Play",
        "rules": "Rules",
        "features_title": "More than a list of games",
        "features": [
            ("⭐ Levels & XP", "Every recorded game contributes to a global progression level."),
            ("🎯 Daily missions", "Short objectives encourage players to come back and explore the catalog."),
            ("⚔️ Quiz Duel", "Two players answer the same ten questions and PlayBed compares the results server-side."),
        ],
        "cta": "Open the French platform",
        "language_note": "Full English gameplay and editorial content are being rolled out progressively.",
    },
    "es": {
        "html_lang": "es",
        "name": "Español",
        "title": "PlayBed — Minijuegos gratis en el navegador",
        "description": "Descubre PlayBed, una plataforma gratuita con diez minijuegos, niveles, misiones, clasificaciones y desafíos entre jugadores.",
        "eyebrow": "PLAYBED INTERNACIONAL · BETA EN ESPAÑOL",
        "heading": "Juega. Progresa. Desafía a tus amigos.",
        "intro": "PlayBed es una plataforma gratuita de juegos en el navegador basada en partidas rápidas, progresión, misiones, perfiles públicos y clasificaciones. No necesitas descargar nada.",
        "catalog_title": "10 juegos disponibles",
        "catalog_intro": "La plataforma incluye actualmente diez juegos de palabras, lógica, memoria, rapidez y cultura general. El juego sigue estando principalmente en francés mientras se preparan las versiones internacionales.",
        "play": "Jugar",
        "rules": "Reglas",
        "features_title": "Más que una lista de juegos",
        "features": [
            ("⭐ Niveles y XP", "Cada partida registrada contribuye a una progresión global."),
            ("🎯 Misiones diarias", "Objetivos breves animan a volver y explorar diferentes juegos."),
            ("⚔️ Quiz Duel", "Dos jugadores responden a las mismas diez preguntas y PlayBed compara los resultados en el servidor."),
        ],
        "cta": "Abrir la plataforma en francés",
        "language_note": "La experiencia completa en español se desplegará progresivamente.",
    },
}

GAME_TRANSLATIONS = {
    "en": {
        "pendu": ("Hangman", "Find the hidden word letter by letter before running out of lives."),
        "pom": ("Higher or Lower", "Find the secret number between 0 and 100 using higher/lower clues."),
        "vof": ("True or False", "Answer ten general-knowledge statements."),
        "quiz": ("Quick Quiz", "Ten multiple-choice general-knowledge questions."),
        "memory": ("Memory", "Match eight pairs while minimizing moves and time."),
        "calcul": ("Mental Math", "Solve ten calculations accurately and quickly."),
        "melange": ("Scrambled Word", "Put shuffled letters back in the right order."),
        "code": ("Secret Code", "Deduce a four-digit code using position clues."),
        "suite": ("Number Sequences", "Find the next number in ten logical sequences."),
        "mot5": ("Mystery Word", "Find a five-letter French word in six attempts."),
    },
    "es": {
        "pendu": ("Ahorcado", "Encuentra la palabra oculta letra por letra antes de quedarte sin vidas."),
        "pom": ("Más o Menos", "Encuentra el número secreto entre 0 y 100 con pistas de más o menos."),
        "vof": ("Verdadero o Falso", "Responde a diez afirmaciones de cultura general."),
        "quiz": ("Quiz Exprés", "Diez preguntas de cultura general con varias opciones."),
        "memory": ("Memory", "Encuentra ocho parejas usando el menor número de movimientos posible."),
        "calcul": ("Cálculo Mental", "Resuelve diez operaciones con precisión y rapidez."),
        "melange": ("Palabra Mezclada", "Vuelve a colocar las letras en el orden correcto."),
        "code": ("Código Secreto", "Deduce un código de cuatro cifras gracias a las pistas."),
        "suite": ("Series Lógicas", "Encuentra el número siguiente en diez series."),
        "mot5": ("Palabra Misteriosa", "Encuentra una palabra francesa de cinco letras en seis intentos."),
    },
}


def register_international(app, games, current_pseudo):
    def render_language(lang):
        copy = LANGUAGES[lang]
        localized_games = []
        translations = GAME_TRANSLATIONS[lang]
        for slug, game in games.items():
            name, description = translations.get(slug, (game["name"], game["description"]))
            localized_games.append({"slug": slug, "name": name, "description": description, "emoji": game["emoji"], "tag": game["tag"]})
        return render_template("international_home.html", lang=lang, copy=copy, localized_games=localized_games, pseudo=current_pseudo())

    @app.route("/en")
    def international_en():
        return render_language("en")

    @app.route("/es")
    def international_es():
        return render_language("es")
