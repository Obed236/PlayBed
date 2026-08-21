(() => {
  const FAVORITES_KEY = "playbed-favorites-v1";
  const RECENT_KEY = "playbed-recent-v1";
  const PLAYERS_KEY = "playbed-followed-players-v1";
  const push = (event, data = {}) => {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ event, ...data });
  };

  const readList = (key) => {
    try {
      const value = JSON.parse(localStorage.getItem(key));
      return Array.isArray(value) ? value : [];
    } catch {
      return [];
    }
  };
  const writeList = (key, value) => localStorage.setItem(key, JSON.stringify(value));

  const gameCards = [...document.querySelectorAll("[data-game-card]")];
  const search = document.getElementById("gameSearch");
  const category = document.getElementById("gameCategory");
  const favoritesOnly = document.getElementById("favoritesOnly");
  const emptyState = document.getElementById("gameFilterEmpty");

  const applyFilters = () => {
    const query = (search?.value || "").trim().toLowerCase();
    const selectedCategory = category?.value || "all";
    const favorites = new Set(readList(FAVORITES_KEY));
    let visible = 0;
    gameCards.forEach((card) => {
      const haystack = `${card.dataset.gameName || ""} ${card.dataset.gameTag || ""}`.toLowerCase();
      const matchesSearch = !query || haystack.includes(query);
      const matchesCategory = selectedCategory === "all" || card.dataset.gameTag === selectedCategory;
      const matchesFavorite = !favoritesOnly?.checked || favorites.has(card.dataset.gameSlug);
      const show = matchesSearch && matchesCategory && matchesFavorite;
      card.hidden = !show;
      if (show) visible += 1;
    });
    if (emptyState) emptyState.hidden = visible !== 0;
  };

  search?.addEventListener("input", () => {
    applyFilters();
    push("game_search", { query_length: search.value.trim().length });
  });
  category?.addEventListener("change", () => {
    applyFilters();
    push("game_category_filter", { category: category.value });
  });
  favoritesOnly?.addEventListener("change", () => {
    applyFilters();
    push("favorites_filter", { enabled: favoritesOnly.checked });
  });

  const syncFavoriteButtons = () => {
    const favorites = new Set(readList(FAVORITES_KEY));
    document.querySelectorAll("[data-favorite-game]").forEach((button) => {
      const active = favorites.has(button.dataset.favoriteGame);
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
      button.title = active ? "Retirer des favoris" : "Ajouter aux favoris";
      button.textContent = active ? "★" : "☆";
    });
  };

  const syncFollowButtons = () => {
    const followed = new Set(readList(PLAYERS_KEY));
    document.querySelectorAll("[data-follow-player]").forEach((button) => {
      const pseudo = button.dataset.followPlayer;
      const active = followed.has(pseudo);
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
      button.textContent = active ? "★ Joueur suivi" : "☆ Suivre ce joueur";
    });
  };

  document.addEventListener("click", (event) => {
    const favoriteButton = event.target.closest("[data-favorite-game]");
    if (favoriteButton) {
      event.preventDefault();
      const slug = favoriteButton.dataset.favoriteGame;
      const favorites = readList(FAVORITES_KEY);
      const exists = favorites.includes(slug);
      const next = exists ? favorites.filter((item) => item !== slug) : [slug, ...favorites].slice(0, 20);
      writeList(FAVORITES_KEY, next);
      syncFavoriteButtons();
      applyFilters();
      renderQuickLists();
      push("favorite_toggle", { game: slug, favorite: !exists });
      return;
    }

    const followButton = event.target.closest("[data-follow-player]");
    if (followButton) {
      event.preventDefault();
      const pseudo = followButton.dataset.followPlayer;
      const followed = readList(PLAYERS_KEY);
      const exists = followed.includes(pseudo);
      const next = exists ? followed.filter((item) => item !== pseudo) : [pseudo, ...followed].slice(0, 20);
      writeList(PLAYERS_KEY, next);
      syncFollowButtons();
      renderQuickLists();
      push("player_follow_toggle", { followed: !exists });
      return;
    }

    const startLink = event.target.closest("[data-game-start]");
    if (startLink) {
      const slug = startLink.dataset.gameStart;
      const recent = readList(RECENT_KEY).filter((item) => item !== slug);
      recent.unshift(slug);
      writeList(RECENT_KEY, recent.slice(0, 6));
      push("game_start", { game: slug, source: startLink.dataset.source || "unknown" });
    }

    const shareButton = event.target.closest("[data-share-url]");
    if (shareButton) {
      event.preventDefault();
      const url = shareButton.dataset.shareUrl;
      const title = shareButton.dataset.shareTitle || "PlayBed";
      if (navigator.share) {
        navigator.share({ title, url }).then(() => push("share", { method: "native" })).catch(() => {});
      } else if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(() => {
          const previous = shareButton.textContent;
          shareButton.textContent = "Lien copié ✓";
          push("share", { method: "clipboard" });
          setTimeout(() => { shareButton.textContent = previous || "Partager"; }, 1800);
        });
      }
    }
  });

  const gameMeta = new Map(gameCards.map((card) => [card.dataset.gameSlug, {
    name: card.dataset.gameName,
    emoji: card.dataset.gameEmoji,
    url: card.dataset.gameStartUrl,
  }]));

  const renderGameList = (container, slugs, emptyText) => {
    if (!container) return;
    const items = slugs.map((slug) => ({ slug, ...gameMeta.get(slug) })).filter((item) => item.name && item.url);
    if (!items.length) {
      container.innerHTML = `<p class="growth-empty">${emptyText}</p>`;
      return;
    }
    container.innerHTML = items.map((item) => `
      <a class="quick-game-link" href="${item.url}" data-game-start="${item.slug}" data-source="quick-list">
        <span>${item.emoji || "🎮"}</span><strong>${item.name}</strong><small>Jouer →</small>
      </a>`).join("");
  };

  const renderPlayers = () => {
    const container = document.getElementById("followedPlayers");
    if (!container) return;
    const players = readList(PLAYERS_KEY);
    if (!players.length) {
      container.innerHTML = '<p class="growth-empty">Les profils que tu suis apparaîtront ici.</p>';
      return;
    }
    container.innerHTML = players.map((pseudo) => `
      <a class="quick-game-link" href="/joueur/${encodeURIComponent(pseudo)}">
        <span>👤</span><strong>${escapeHtml(pseudo)}</strong><small>Profil →</small>
      </a>`).join("");
  };

  const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  })[char]);

  const renderQuickLists = () => {
    renderGameList(document.getElementById("recentGames"), readList(RECENT_KEY), "Tes jeux récents apparaîtront ici.");
    renderGameList(document.getElementById("favoriteGames"), readList(FAVORITES_KEY), "Ajoute un jeu en favori avec ☆.");
    renderPlayers();
  };

  syncFavoriteButtons();
  syncFollowButtons();
  applyFilters();
  renderQuickLists();

  const points = document.querySelector(".points-earned");
  if (points) {
    const shell = document.querySelector("[data-current-game]");
    push("game_complete", { game: shell?.dataset.currentGame || "unknown" });
  }

  const memoryResult = document.getElementById("memoryResult");
  if (memoryResult && window.MutationObserver) {
    let fired = false;
    new MutationObserver(() => {
      if (!fired && !memoryResult.hidden && /points|Bravo/i.test(memoryResult.textContent || "")) {
        fired = true;
        push("game_complete", { game: "memory" });
      }
    }).observe(memoryResult, { childList: true, characterData: true, subtree: true, attributes: true });
  }

  document.querySelectorAll("[data-mission-complete='true']").forEach((mission) => {
    push("mission_completed_view", { mission: mission.dataset.missionName || "unknown" });
  });

  if ("PerformanceObserver" in window) {
    let clsValue = 0;
    let lcpValue = 0;
    let inpValue = 0;
    try {
      new PerformanceObserver((list) => {
        const entries = list.getEntries();
        if (entries.length) lcpValue = entries[entries.length - 1].startTime;
      }).observe({ type: "largest-contentful-paint", buffered: true });
    } catch {}
    try {
      new PerformanceObserver((list) => {
        list.getEntries().forEach((entry) => { if (!entry.hadRecentInput) clsValue += entry.value; });
      }).observe({ type: "layout-shift", buffered: true });
    } catch {}
    try {
      new PerformanceObserver((list) => {
        list.getEntries().forEach((entry) => { inpValue = Math.max(inpValue, entry.duration || 0); });
      }).observe({ type: "event", durationThreshold: 40, buffered: true });
    } catch {}
    window.addEventListener("pagehide", () => {
      if (lcpValue) push("web_vital", { metric: "LCP", value: Math.round(lcpValue) });
      if (clsValue) push("web_vital", { metric: "CLS", value: Math.round(clsValue * 1000) / 1000 });
      if (inpValue) push("web_vital", { metric: "INP", value: Math.round(inpValue) });
    }, { once: true });
  }
})();
