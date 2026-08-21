from flask import request


def register_performance(app):
    @app.after_request
    def performance_headers(response):
        path = request.path
        if path.startswith("/static/") and response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=604800"
        elif path in {"/sitemap.xml", "/robots.txt", "/ads.txt", "/manifest.webmanifest", "/service-worker.js"} and response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=3600"
        elif response.mimetype == "text/html":
            response.headers.setdefault("Cache-Control", "no-cache")
        response.headers.setdefault("Vary", "Accept-Encoding")
        return response
