from flask import render_template


def register_catalog_routes(app, games, current_pseudo):
    @app.route('/jeux')
    def games_catalog():
        return render_template(
            'games.html',
            games=games,
            pseudo=current_pseudo(),
        )
