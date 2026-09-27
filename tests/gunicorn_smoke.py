"""Exercise the production WSGI entry point in an isolated local database."""
import json
import http.client
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen


def main(entrypoint):
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="playbed-smoke-") as directory:
        target = Path(directory)
        for source in root.glob("*.py"):
            shutil.copy2(source, target / source.name)
        for name in ("templates", "static", "data", "imposteur"):
            shutil.copytree(root / name, target / name)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        env = os.environ.copy()
        for key in ("DATABASE_URL", "GUNICORN_CMD_ARGS", "WEB_CONCURRENCY"):
            env.pop(key, None)
        env.update(
            PORT=str(port), SECRET_KEY="isolated-gunicorn-smoke-test", RENDER="true",
            SESSION_COOKIE_SECURE="1",
            PLAYBED_TRUSTED_HOSTS="127.0.0.1,playbed.example",
        )
        subprocess.run(
            [sys.executable, "-c", "import app; app.init_db()"],
            cwd=target, env=env, check=True, timeout=30,
        )
        base = f"http://127.0.0.1:{port}"
        # Match render.yaml: Gunicorn must pick up PORT without an explicit bind.
        with tempfile.TemporaryFile(mode="w+") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", "gunicorn", entrypoint],
                cwd=target, env=env, stdout=log, stderr=subprocess.STDOUT,
            )
            try:
                deadline = time.monotonic() + 30
                while True:
                    if process.poll() is not None:
                        raise AssertionError("Gunicorn exited before becoming ready")
                    try:
                        with urlopen(base + "/health", timeout=2) as response:
                            assert response.status == 200
                            assert json.load(response)["status"] == "ok"
                        break
                    except URLError:
                        if time.monotonic() >= deadline:
                            raise AssertionError("Gunicorn did not become ready within 30 seconds")
                        time.sleep(0.2)
                with urlopen(base + "/", timeout=10) as response:
                    assert response.status == 200
                    assert b"PlayBed" in response.read()
                    assert "nonce-" in response.headers["Content-Security-Policy"]
                    assert response.headers["X-Content-Type-Options"] == "nosniff"
                with urlopen(base + "/static/js/csp-events.js", timeout=5) as response:
                    assert response.status == 200
                    assert b"migrateLegacyHandlers" in response.read()
                # Simulate Render's TLS-terminating proxy and preserve the session.
                headers = {
                    "X-Forwarded-Proto": "https",
                    "X-Forwarded-Host": "playbed.example",
                    "Origin": "https://playbed.example",
                    "Content-Type": "application/x-www-form-urlencoded",
                }
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
                try:
                    connection.request("POST", "/pseudo", "pseudo=GunicornSmoke", headers)
                    response = connection.getresponse()
                    assert response.status == 302
                    assert response.getheader("Location") in ("/", "https://playbed.example/")
                    cookie = response.getheader("Set-Cookie")
                    assert cookie and "Secure" in cookie and "HttpOnly" in cookie
                    response.read()
                    headers["Cookie"] = cookie.split(";", 1)[0]
                    connection.request("GET", "/", headers=headers)
                    response = connection.getresponse()
                    assert response.status == 200
                    assert b"GunicornSmoke" in response.read()
                finally:
                    connection.close()
                process.terminate()
                assert process.wait(timeout=15) == 0, "Gunicorn failed to shut down cleanly"
                print(f"Gunicorn {entrypoint}: HTTP, proxy, session and SIGTERM OK")
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                log.seek(0)
                print(log.read())


if __name__ == "__main__":
    for entrypoint in ("app:app", "wsgi:app"):
        main(entrypoint)
