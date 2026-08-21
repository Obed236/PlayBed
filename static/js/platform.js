(() => {
    const CONSENT_KEY = "playbed-consent-v1";
    const FAVORITES_KEY = "playbed-favorites-v1";
    const ADSENSE_ID = "ca-pub-8115913863262508";

    function track(event, data = {}) {
        window.dataLayer = window.dataLayer || [];
        window.dataLayer.push({ event, ...data });
    }

    const menuToggle = document.getElementById("mobileMenuToggle");
    const navigation = document.getElementById("mainNavigation");
    if (menuToggle && navigation) {
        menuToggle.addEventListener("click", () => {
            const open = navigation.classList.toggle("open");
            menuToggle.setAttribute("aria-expanded", String(open));
            menuToggle.textContent = open ? "✕" : "☰";
        });
        navigation.addEventListener("click", (event) => {
            if (event.target.closest("a") && navigation.classList.contains("open")) {
                navigation.classList.remove("open");
                menuToggle.setAttribute("aria-expanded", "false");
                menuToggle.textContent = "☰";
            }
        });
    }

    function readFavorites() {
        try {
            const value = JSON.parse(localStorage.getItem(FAVORITES_KEY));
            return Array.isArray(value) ? value.filter((item) => typeof item === "string") : [];
        } catch {
            return [];
        }
    }

    function writeFavorites(values) {
        const unique = [...new Set(values)];
        localStorage.setItem(FAVORITES_KEY, JSON.stringify(unique));
        return unique;
    }

    let favorites = readFavorites();
    const favoriteButtons = [...document.querySelectorAll("[data-favorite-game]")];
    function refreshFavoriteButtons() {
        favoriteButtons.forEach((button) => {
            const slug = button.dataset.favoriteGame;
            const active = favorites.includes(slug);
            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", String(active));
            button.textContent = active ? "★" : "☆";
            button.setAttribute("aria-label", active ? `Retirer ${slug} des favoris` : `Ajouter ${slug} aux favoris`);
        });
    }
    favoriteButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const slug = button.dataset.favoriteGame;
            const active = favorites.includes(slug);
            favorites = active ? favorites.filter((item) => item !== slug) : writeFavorites([...favorites, slug]);
            if (active) writeFavorites(favorites);
            refreshFavoriteButtons();
            track("favorite_toggle", { game: slug, favorite: !active });
            document.dispatchEvent(new CustomEvent("playbed:favorites-changed"));
        });
    });
    refreshFavoriteButtons();

    const searchInput = document.querySelector("[data-game-search]");
    const filterButtons = [...document.querySelectorAll("[data-game-filter]")];
    const gameCards = [...document.querySelectorAll("[data-game-card]")];
    const emptyState = document.querySelector("[data-discovery-empty]");
    let activeFilter = "all";

    function applyDiscoveryFilter() {
        const query = (searchInput?.value || "").trim().toLowerCase();
        let visible = 0;
        gameCards.forEach((card) => {
            const slug = card.dataset.gameSlug || "";
            const name = card.dataset.gameName || card.textContent.toLowerCase();
            const category = card.dataset.gameCategory || "";
            const categoryMatch = activeFilter === "all" || category === activeFilter || (activeFilter === "favorites" && favorites.includes(slug));
            const queryMatch = !query || name.includes(query);
            const show = categoryMatch && queryMatch;
            card.hidden = !show;
            if (show) visible += 1;
        });
        if (emptyState) emptyState.hidden = visible !== 0;
    }

    searchInput?.addEventListener("input", () => {
        applyDiscoveryFilter();
        track("game_search", { query_length: searchInput.value.trim().length });
    });
    filterButtons.forEach((button) => {
        button.addEventListener("click", () => {
            activeFilter = button.dataset.gameFilter || "all";
            filterButtons.forEach((item) => item.classList.toggle("active", item === button));
            applyDiscoveryFilter();
            track("game_filter", { filter: activeFilter });
        });
    });
    document.addEventListener("playbed:favorites-changed", applyDiscoveryFilter);
    applyDiscoveryFilter();

    document.querySelectorAll("[data-game-start]").forEach((link) => {
        link.addEventListener("click", () => track("game_start", { game: link.dataset.gameStart }));
    });
    document.querySelectorAll("[data-challenge-create]").forEach((link) => {
        link.addEventListener("click", () => track("challenge_created", { game: link.dataset.challengeCreate }));
    });

    document.querySelectorAll("[data-share-current]").forEach((button) => {
        button.addEventListener("click", async () => {
            const title = button.dataset.shareTitle || document.title;
            const text = button.dataset.shareText || "Découvre ce défi PlayBed.";
            const url = window.location.href;
            try {
                if (navigator.share) {
                    await navigator.share({ title, text, url });
                    track("challenge_share", { method: "native" });
                } else if (navigator.clipboard) {
                    await navigator.clipboard.writeText(url);
                    const previous = button.textContent;
                    button.textContent = "Lien copié ✓";
                    setTimeout(() => { button.textContent = previous; }, 1800);
                    track("challenge_share", { method: "clipboard" });
                }
            } catch {
                // L'utilisateur peut fermer la feuille de partage sans action.
            }
        });
    });

    const panel = document.getElementById("consentPanel");
    const adsCheckbox = document.getElementById("adsConsent");
    const acceptAll = document.getElementById("acceptAllConsent");
    const rejectAll = document.getElementById("rejectAllConsent");
    const saveConsent = document.getElementById("saveConsent");
    const openPreferences = document.getElementById("openPrivacyPreferences");
    let lastFocused = null;

    function readConsent() {
        try {
            const value = JSON.parse(localStorage.getItem(CONSENT_KEY));
            if (!value || typeof value.ads !== "boolean") return null;
            return value;
        } catch {
            return null;
        }
    }
    function updateGoogleConsent(adsAllowed) {
        if (typeof window.gtag !== "function") return;
        window.gtag("consent", "update", {
            ad_storage: adsAllowed ? "granted" : "denied",
            ad_user_data: adsAllowed ? "granted" : "denied",
            ad_personalization: adsAllowed ? "granted" : "denied",
            analytics_storage: "denied"
        });
    }
    function loadAdsense() {
        if (document.querySelector('script[data-playbed-adsense="true"]')) return;
        const script = document.createElement("script");
        script.async = true;
        script.crossOrigin = "anonymous";
        script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${ADSENSE_ID}`;
        script.dataset.playbedAdsense = "true";
        document.head.appendChild(script);
    }
    function applyConsent(consent) {
        updateGoogleConsent(consent.ads);
        if (consent.ads && document.body?.dataset.adsPage === "true") loadAdsense();
    }
    function storeConsent(ads) {
        const consent = { ads: Boolean(ads), version: 1, updatedAt: new Date().toISOString() };
        localStorage.setItem(CONSENT_KEY, JSON.stringify(consent));
        applyConsent(consent);
        closePanel();
    }
    function openPanel() {
        if (!panel) return;
        lastFocused = document.activeElement;
        const current = readConsent();
        if (adsCheckbox) adsCheckbox.checked = Boolean(current?.ads);
        panel.hidden = false;
        document.body.style.overflow = "hidden";
        window.setTimeout(() => {
            const target = panel.querySelector("button, input, a");
            if (target) target.focus();
        }, 0);
    }
    function closePanel() {
        if (!panel) return;
        panel.hidden = true;
        document.body.style.overflow = "";
        if (lastFocused && typeof lastFocused.focus === "function") lastFocused.focus();
    }
    const existingConsent = readConsent();
    if (existingConsent) applyConsent(existingConsent);
    else window.setTimeout(openPanel, 250);

    acceptAll?.addEventListener("click", () => storeConsent(true));
    rejectAll?.addEventListener("click", () => storeConsent(false));
    saveConsent?.addEventListener("click", () => storeConsent(Boolean(adsCheckbox?.checked)));
    openPreferences?.addEventListener("click", openPanel);
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && panel && !panel.hidden && readConsent()) closePanel();
    });
})();
