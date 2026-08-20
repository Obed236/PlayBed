from flask import render_template


def register_sitemap_route(app, games, current_pseudo):
    @app.route("/plan-du-site")
    def site_map_page():
        return render_template(
            "site_map.html",
            games=games,
            pseudo=current_pseudo(),
        )
