from flask import render_template


def register_creator_routes(app, current_pseudo):
    @app.route("/createur")
    def creator_page():
        return render_template("creator.html", pseudo=current_pseudo())
