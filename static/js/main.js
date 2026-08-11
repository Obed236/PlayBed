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

    const icons = ["🚀","🎮","⚽","💻","🔥","🎵","🧠","🍕"];
    const cards = [...icons, ...icons].sort(() => Math.random() - 0.5);
    const movesEl = document.getElementById("memoryMoves");
    const timeEl = document.getElementById("memoryTime");
    const resultEl = document.getElementById("memoryResult");

    let first = null;
    let second = null;
    let locked = false;
    let matched = 0;
    let moves = 0;
    let seconds = 0;
    let started = false;
    let timer = null;

    function startTimer() {
        if (started) return;
        started = true;
        timer = setInterval(() => {
            seconds += 1;
            timeEl.textContent = seconds;
        }, 1000);
    }

    cards.forEach((icon, index) => {
        const button = document.createElement("button");
        button.className = "memory-card";
        button.type = "button";
        button.dataset.value = icon;
        button.dataset.index = index;
        button.innerHTML = `<span class="face">${icon}</span>`;
        board.appendChild(button);
    });

    board.addEventListener("click", async (event) => {
        const card = event.target.closest(".memory-card");
        if (!card || locked || card.classList.contains("matched") || card === first) return;

        startTimer();
        card.classList.add("revealed");

        if (!first) {
            first = card;
            return;
        }

        second = card;
        moves += 1;
        movesEl.textContent = moves;

        if (first.dataset.value === second.dataset.value) {
            first.classList.add("matched");
            second.classList.add("matched");
            first.classList.remove("revealed");
            second.classList.remove("revealed");
            matched += 2;
            first = null;
            second = null;

            if (matched === cards.length) {
                clearInterval(timer);
                resultEl.hidden = false;
                resultEl.textContent = "Partie terminée…";
                try {
                    const response = await fetch(board.dataset.scoreUrl, {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({moves, seconds})
                    });
                    const data = await response.json();
                    if (data.ok) {
                        resultEl.textContent = `Bravo ! ${moves} coups, ${seconds}s — +${data.points} points 🏆`;
                    } else {
                        resultEl.textContent = `Bravo ! ${moves} coups en ${seconds}s.`;
                    }
                } catch {
                    resultEl.textContent = `Bravo ! ${moves} coups en ${seconds}s.`;
                }
            }
        } else {
            locked = true;
            setTimeout(() => {
                first.classList.remove("revealed");
                second.classList.remove("revealed");
                first = null;
                second = null;
                locked = false;
            }, 750);
        }
    });
})();
