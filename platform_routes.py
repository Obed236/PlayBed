from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import redirect, url_for, render_template
import os

PARIS_TZ = ZoneInfo("Europe/Paris")

GAME_CONTENT = {
    "pendu": {
        "headline": "Retrouve le mot avant de manquer de vies.",
        "objective": "Le Pendu te demande de retrouver un mot caché en proposant une lettre à la fois. Chaque erreur fait perdre une vie et une partie gagnée avec beaucoup de vies restantes rapporte davantage de points.",
        "rules": [
            "Un mot est choisi aléatoirement au début de la partie.",
            "Propose une seule lettre à chaque tour.",
            "Une bonne lettre est révélée partout où elle apparaît dans le mot.",
            "Une mauvaise lettre fait perdre une vie.",
            "La partie se termine lorsque le mot est entièrement découvert ou lorsque les 10 vies sont épuisées.",
        ],
        "scoring": "Une victoire rapporte une base de 500 points, complétée par un bonus lié au nombre de vies restantes. Une défaite ne rapporte pas de point.",
        "tips": [
            "Commence par les voyelles et les consonnes fréquentes en français.",
            "Observe la longueur du mot et la position des lettres déjà révélées.",
            "Évite de rejouer une lettre déjà proposée : PlayBed te le signalera.",
        ],
        "skills": "Vocabulaire, déduction et observation.",
    },
    "pom": {
        "headline": "Trouve le nombre secret avec le moins d’essais possible.",
        "objective": "Plus ou Moins est un jeu de logique rapide. Un nombre secret compris entre 0 et 100 est choisi et chaque tentative te donne un indice pour réduire progressivement la zone de recherche.",
        "rules": [
            "Le nombre secret est compris entre 0 et 100 inclus.",
            "Entre une proposition puis valide-la.",
            "PlayBed indique « plus » si le nombre secret est supérieur et « moins » s’il est inférieur.",
            "Continue jusqu’à trouver exactement le nombre secret.",
        ],
        "scoring": "Le score commence haut puis diminue avec le nombre d’essais. Une recherche structurée permet donc d’obtenir de meilleurs scores.",
        "tips": [
            "Commence autour de 50 pour couper l’intervalle en deux.",
            "Après chaque indice, choisis le milieu du nouvel intervalle possible.",
            "Cette méthode de dichotomie permet de trouver le résultat très rapidement.",
        ],
        "skills": "Logique, estimation et raisonnement par intervalles.",
    },
    "vof": {
        "headline": "Dix affirmations pour tester ta culture générale.",
        "objective": "Vrai ou Faux propose une série de dix affirmations sélectionnées aléatoirement. À toi de décider si chacune est exacte ou non.",
        "rules": [
            "Une partie contient jusqu’à 10 affirmations.",
            "Choisis « Vrai » ou « Faux » pour chaque affirmation.",
            "La réponse correcte est indiquée après ton choix.",
            "La partie se termine après la dernière affirmation.",
        ],
        "scoring": "Chaque bonne réponse rapporte 100 points. Un sans-faute permet donc d’atteindre 1 000 points.",
        "tips": [
            "Lis l’affirmation en entier avant de répondre.",
            "Méfie-toi des formulations absolues comme « toujours » ou « jamais ».",
            "Utilise tes parties pour apprendre : les réponses te donnent immédiatement un retour.",
        ],
        "skills": "Culture générale, attention et esprit critique.",
    },
    "quiz": {
        "headline": "Un quiz express de dix questions à choix multiples.",
        "objective": "Quiz Express mélange plusieurs thèmes de culture générale. Les questions sont sélectionnées aléatoirement pour renouveler les parties.",
        "rules": [
            "Une partie contient jusqu’à 10 questions.",
            "Plusieurs propositions sont affichées pour chaque question.",
            "Sélectionne la réponse que tu penses correcte.",
            "Ton score final correspond au nombre de bonnes réponses.",
        ],
        "scoring": "Chaque bonne réponse vaut 100 points, soit un maximum de 1 000 points pour une partie parfaite.",
        "tips": [
            "Élimine d’abord les réponses manifestement fausses.",
            "Ne change pas une réponse sans raison précise.",
            "Rejoue régulièrement : les questions étant tirées aléatoirement, tu peux rencontrer de nouveaux défis.",
        ],
        "skills": "Culture générale, mémoire et prise de décision.",
    },
    "memory": {
        "headline": "Mémorise les cartes et retrouve les huit paires.",
        "objective": "Memory met à l’épreuve ta mémoire visuelle. Seize cartes sont mélangées face cachée et ton objectif est de retrouver les huit paires le plus efficacement possible.",
        "rules": [
            "Retourne deux cartes à chaque coup.",
            "Si les symboles correspondent, la paire reste révélée.",
            "Sinon, les cartes se retournent après un court instant.",
            "La partie se termine lorsque les huit paires sont retrouvées.",
        ],
        "scoring": "Le nombre de coups et le temps de résolution influencent le score. Une partie rapide avec peu d’erreurs rapporte davantage.",
        "tips": [
            "Essaie de mémoriser la position des cartes dès leur première apparition.",
            "Lorsque tu vois une carte déjà rencontrée, cherche immédiatement sa paire connue.",
            "Privilégie la précision : retourner au hasard augmente rapidement le nombre de coups.",
        ],
        "skills": "Mémoire visuelle, concentration et rapidité.",
    },
}

GUIDES = {
    "mieux-jouer-au-pendu": {
        "title": "Comment progresser au Pendu",
        "description": "Une méthode simple pour choisir de meilleures lettres et réduire le nombre d’erreurs.",
        "read_time": "4 min",
        "game": "pendu",
        "sections": [
            ("Commencer par les lettres les plus utiles", [
                "Toutes les lettres n’ont pas la même fréquence en français. Commencer par des voyelles courantes comme E, A, I ou O permet souvent de révéler rapidement la structure du mot.",
                "Ensuite, les consonnes fréquentes comme S, R, N, T ou L peuvent aider à confirmer une terminaison ou une famille de mots."
            ]),
            ("Utiliser la forme du mot", [
                "La longueur du mot, les lettres répétées et leur position donnent des indices. Une lettre révélée en fin de mot peut par exemple suggérer une terminaison connue.",
                "Au lieu de proposer des lettres au hasard, essaie de construire mentalement quelques mots compatibles avec le motif visible."
            ]),
            ("Éviter les paris trop tôt", [
                "Les lettres rares comme W, K ou X peuvent être utiles, mais seulement lorsque le motif du mot les rend plausibles. Les jouer trop tôt augmente le risque de perdre des vies sans obtenir d’information."
            ]),
        ],
    },
    "dichotomie-plus-ou-moins": {
        "title": "Plus ou Moins : la stratégie de la dichotomie",
        "description": "Pourquoi couper l’intervalle en deux est la manière la plus efficace de trouver le nombre secret.",
        "read_time": "4 min",
        "game": "pom",
        "sections": [
            ("Réduire l’espace de recherche", [
                "Au départ, 101 valeurs sont possibles entre 0 et 100. En choisissant une valeur proche du milieu, tu élimines environ la moitié des possibilités à chaque réponse.",
                "Si tu proposes 50 et que PlayBed répond « plus », tu sais immédiatement que toutes les valeurs de 0 à 50 peuvent être écartées."
            ]),
            ("Recalculer le milieu", [
                "Supposons que la réponse soit « plus » après 50. Le nouvel intervalle est 51–100 : son milieu se situe autour de 75. Tu répètes ensuite la même logique.",
                "Cette méthode s’appelle la recherche dichotomique. Elle est également très importante en algorithmique."
            ]),
            ("Transformer le jeu en exercice d’algorithme", [
                "Essaie de te fixer un objectif d’essais maximum et compare tes parties. Tu verras qu’une méthode régulière bat presque toujours une suite de propositions intuitives."
            ]),
        ],
    },
    "reussir-memory": {
        "title": "5 techniques pour améliorer sa mémoire au Memory",
        "description": "Des habitudes simples pour retenir plus de cartes et terminer avec moins de coups.",
        "read_time": "5 min",
        "game": "memory",
        "sections": [
            ("Balayer la grille méthodiquement", [
                "Évite de choisir les cartes uniquement au hasard. Parcourir progressivement une zone de la grille facilite la création de repères spatiaux."
            ]),
            ("Associer symbole et position", [
                "Lorsque tu découvres un symbole, mémorise à la fois son apparence et sa position : coin supérieur gauche, milieu de la deuxième ligne, etc.",
                "Créer une petite association mentale rend la position plus facile à retrouver quelques secondes plus tard."
            ]),
            ("Exploiter immédiatement une paire connue", [
                "Si la première carte retournée correspond à un symbole déjà mémorisé, utilise ton deuxième choix pour chercher sa paire. Cela évite de gaspiller une information fraîche."
            ]),
            ("Privilégier la précision à la vitesse", [
                "Le score prend en compte les coups et le temps. Aller très vite mais retourner beaucoup de mauvaises cartes n’est donc pas forcément avantageux."
            ]),
        ],
    },
    "progresser-en-culture-generale": {
        "title": "Progresser en culture générale avec les quiz",
        "description": "Comment utiliser Vrai ou Faux et Quiz Express pour apprendre au lieu de simplement deviner.",
        "read_time": "5 min",
        "game": "quiz",
        "sections": [
            ("Transformer une erreur en information", [
                "Une mauvaise réponse est utile si tu retiens la correction. Après une partie, essaie de te rappeler les deux ou trois questions qui t’ont posé problème."
            ]),
            ("Raisonner avant de répondre", [
                "Dans un QCM, commence par éliminer ce qui paraît impossible. Même sans connaître immédiatement la réponse, réduire le nombre de possibilités améliore ton raisonnement."
            ]),
            ("Jouer régulièrement plutôt que longtemps", [
                "Des sessions courtes et répétées favorisent souvent mieux la mémorisation qu’une seule longue session. Revenir plusieurs fois sur PlayBed permet également de rencontrer différentes questions."
            ]),
        ],
    },
    "comprendre-les-scores-playbed": {
        "title": "Comprendre les scores et le classement PlayBed",
        "description": "Comment les points sont calculés et comment améliorer son classement sans jouer au hasard.",
        "read_time": "4 min",
        "game": None,
        "sections": [
            ("Des règles différentes selon le jeu", [
                "Chaque mini-jeu récompense une compétence différente. Les quiz récompensent le nombre de bonnes réponses, le Pendu tient compte des vies restantes, Plus ou Moins du nombre d’essais et Memory combine efficacité et rapidité."
            ]),
            ("Le classement général", [
                "Les points obtenus à la fin des parties sont additionnés par pseudo. Le classement général valorise donc autant la régularité que les meilleures performances."
            ]),
            ("Se fixer des objectifs", [
                "Au lieu de chercher seulement la première place, vise des paliers personnels : réussir un sans-faute, dépasser 1 000 points sur un jeu ou améliorer ton meilleur score."
            ]),
        ],
    },
}

ACHIEVEMENTS = [
    ("premiere-partie", "🎮", "Première partie", "Terminer au moins une partie", lambda s: s["games_played"] >= 1),
    ("habitude", "🔥", "Habitué", "Terminer au moins 10 parties", lambda s: s["games_played"] >= 10),
    ("explorateur", "🧭", "Explorateur", "Jouer aux 5 jeux différents", lambda s: s["distinct_games"] >= 5),
    ("5000", "⭐", "5 000 points", "Atteindre 5 000 points cumulés", lambda s: s["total_points"] >= 5000),
    ("10000", "🏆", "10 000 points", "Atteindre 10 000 points cumulés", lambda s: s["total_points"] >= 10000),
    ("expert", "💎", "Performance expert", "Dépasser 1 000 points sur une partie", lambda s: s["best_score"] >= 1000),
]


def register_platform_routes(app, games, db_connection, current_pseudo):
    contact_email = os.environ.get("CONTACT_EMAIL", "").strip()

    def challenge_for(pseudo=None):
        today = datetime.now(PARIS_TZ).date()
        slugs = list(games.keys())
        slug = slugs[today.toordinal() % len(slugs)]
        targets = {"pendu": 900, "pom": 800, "vof": 700, "quiz": 700, "memory": 900}
        challenge = {"date": today.strftime("%d/%m/%Y"), "game": slug, "name": games[slug]["name"], "emoji": games[slug]["emoji"], "target": targets[slug], "completed": False}
        if pseudo:
            with db_connection() as conn:
                rows = conn.execute("SELECT points, created_at FROM scores WHERE pseudo = ? AND game = ? ORDER BY created_at DESC LIMIT 100", (pseudo, slug)).fetchall()
            for row in rows:
                try:
                    stamp = datetime.fromisoformat(row["created_at"])
                    if stamp.tzinfo is None:
                        stamp = stamp.replace(tzinfo=timezone.utc)
                    local_day = stamp.astimezone(PARIS_TZ).date()
                except (TypeError, ValueError):
                    continue
                if local_day == today and int(row["points"]) >= targets[slug]:
                    challenge["completed"] = True
                    break
        return challenge

    @app.route("/jeux/<game>")
    def platform_game_detail(game):
        if game not in games:
            return render_template("404.html", pseudo=current_pseudo()), 404
        return render_template("game_detail.html", game=game, meta=games[game], content=GAME_CONTENT[game], pseudo=current_pseudo())

    @app.route("/guides")
    def platform_guides():
        return render_template("guides.html", guides=GUIDES, games=games, pseudo=current_pseudo())

    @app.route("/guides/<slug>")
    def platform_guide_detail(slug):
        guide = GUIDES.get(slug)
        if not guide:
            return render_template("404.html", pseudo=current_pseudo()), 404
        return render_template("guide_detail.html", guide=guide, games=games, pseudo=current_pseudo())

    @app.route("/nouveautes")
    def platform_news():
        return render_template("news.html", pseudo=current_pseudo())

    @app.route("/contact")
    def platform_contact():
        return render_template("contact.html", pseudo=current_pseudo(), contact_email=contact_email)

    @app.route("/mentions-legales")
    def platform_legal():
        return render_template("legal.html", pseudo=current_pseudo(), contact_email=contact_email)

    @app.route("/defi-du-jour")
    def platform_daily_challenge():
        pseudo = current_pseudo()
        return render_template("daily_challenge.html", pseudo=pseudo, challenge=challenge_for(pseudo))

    @app.route("/profil")
    def platform_profile():
        pseudo = current_pseudo()
        if not pseudo:
            return redirect(url_for("home", need_pseudo=1) + "#player")
        with db_connection() as conn:
            stats_row = conn.execute("""
                SELECT COUNT(*) AS games_played, COALESCE(SUM(points), 0) AS total_points,
                       COALESCE(MAX(points), 0) AS best_score, COUNT(DISTINCT game) AS distinct_games
                FROM scores WHERE pseudo = ?
            """, (pseudo,)).fetchone()
            by_game_rows = conn.execute("""
                SELECT game, COUNT(*) AS games_played, MAX(points) AS best_points, SUM(points) AS total_points
                FROM scores WHERE pseudo = ? GROUP BY game ORDER BY total_points DESC
            """, (pseudo,)).fetchall()
            recent_rows = conn.execute("""
                SELECT game, points, created_at FROM scores WHERE pseudo = ? ORDER BY created_at DESC LIMIT 12
            """, (pseudo,)).fetchall()
            ranking_rows = conn.execute("""
                SELECT pseudo, SUM(points) AS total_points FROM scores GROUP BY pseudo ORDER BY total_points DESC
            """).fetchall()
        stats = {"games_played": int(stats_row["games_played"] or 0), "total_points": int(stats_row["total_points"] or 0), "best_score": int(stats_row["best_score"] or 0), "distinct_games": int(stats_row["distinct_games"] or 0)}
        by_game = {row["game"]: dict(row) for row in by_game_rows}
        recent = [dict(row) for row in recent_rows]
        rank = next((index + 1 for index, row in enumerate(ranking_rows) if row["pseudo"] == pseudo), None)
        achievements = [{"slug": slug, "emoji": emoji, "name": name, "description": description, "unlocked": bool(check(stats))} for slug, emoji, name, description, check in ACHIEVEMENTS]
        return render_template("profile.html", pseudo=pseudo, games=games, stats=stats, by_game=by_game, recent=recent, rank=rank, achievements=achievements, challenge=challenge_for(pseudo))

    @app.errorhandler(404)
    def platform_not_found(error):
        return render_template("404.html", pseudo=current_pseudo()), 404

    @app.errorhandler(500)
    def platform_server_error(error):
        return render_template("500.html", pseudo=current_pseudo()), 500
