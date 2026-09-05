(() => {
    const root = document.documentElement;
    const toggle = document.getElementById("themeToggle");
    const savedTheme = localStorage.getItem("playbed-theme") || "dark";
    root.dataset.theme = savedTheme;

    function updateThemeIcon() {
        if (toggle) toggle.textContent = root.dataset.theme === "dark" ? "☀️" : "🌙";
    }
    updateThemeIcon();

    if (toggle) {
        toggle.addEventListener("click", () => {
            root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
            localStorage.setItem("playbed-theme", root.dataset.theme);
            updateThemeIcon();
        });
    }

    const board = document.getElementById("memoryGame");
    if (!board) return;

    const movesEl = document.getElementById("memoryMoves");
    const timeEl = document.getElementById("memoryTime");
    const resultEl = document.getElementById("memoryResult");

    let first = null;
    let locked = false;
    let started = false;
    let seconds = 0;
    let timer = null;

    function startTimer() {
        if (started) return;
        started = true;
        timer = setInterval(() => {
            seconds += 1;
            timeEl.textContent = seconds;
        }, 1000);
    }

    function stopTimer(serverSeconds) {
        if (timer) clearInterval(timer);
        timer = null;
        started = false;
        if (Number.isFinite(serverSeconds)) {
            seconds = serverSeconds;
            timeEl.textContent = serverSeconds;
        }
    }

    for (let index = 0; index < 16; index += 1) {
        const button = document.createElement("button");
        button.className = "memory-card";
        button.type = "button";
        button.dataset.index = String(index);
        button.setAttribute("aria-label", `Carte ${index + 1}`);
        button.innerHTML = '<span class="face"></span>';
        board.appendChild(button);
    }

    board.addEventListener("click", async (event) => {
        const card = event.target.closest(".memory-card");
        if (!card || locked || card.classList.contains("matched") || card === first) return;

        locked = true;
        const index = Number.parseInt(card.dataset.index, 10);

        try {
            const response = await fetch(board.dataset.flipUrl, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({index})
            });
            const data = await response.json();

            if (!response.ok || !data.ok) {
                if (response.status === 429) {
                    resultEl.hidden = false;
                    resultEl.textContent = "Trop de requêtes. Réessaie dans quelques instants.";
                }
                locked = false;
                return;
            }

            const face = card.querySelector(".face");
            face.textContent = data.icon || "";
            card.classList.add("revealed");
            startTimer();

            if (Number.isFinite(data.moves)) {
                movesEl.textContent = data.moves;
            }

            if (data.status === "first") {
                first = card;
                locked = false;
                return;
            }

            if (data.status === "match") {
                if (first) {
                    first.classList.add("matched");
                    first.classList.remove("revealed");
                }
                card.classList.add("matched");
                card.classList.remove("revealed");
                first = null;
                locked = false;
            } else if (data.status === "mismatch") {
                const previous = first;
                first = null;
                setTimeout(() => {
                    if (previous) {
                        previous.classList.remove("revealed");
                        const previousFace = previous.querySelector(".face");
                        if (previousFace) previousFace.textContent = "";
                    }
                    card.classList.remove("revealed");
                    face.textContent = "";
                    locked = false;
                }, 750);
            } else {
                locked = false;
            }

            if (data.finished) {
                stopTimer(Number(data.seconds));
                locked = true;
                resultEl.hidden = false;
                resultEl.textContent = `Bravo ! ${data.moves} coups, ${data.seconds}s — +${data.points} points 🏆`;
                board.querySelectorAll(".memory-card").forEach((button) => {
                    button.disabled = true;
                });
            }
        } catch {
            locked = false;
            resultEl.hidden = false;
            resultEl.textContent = "Impossible de valider la carte. Réessaie.";
        }
    });
})();
