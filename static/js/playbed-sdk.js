(() => {
  const VERSION = "0.1.0";
  const safeName = (value) => /^[a-z][a-z0-9_]{1,47}$/i.test(String(value || ""));
  const emit = (event, payload = {}) => {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ event, sdk_version: VERSION, ...payload });
    try {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({ source: "playbed-sdk", event, payload, version: VERSION }, window.location.origin);
      }
    } catch {}
  };

  window.PlayBed = Object.freeze({
    version: VERSION,
    startGame({ game } = {}) {
      if (!safeName(game)) return false;
      emit("sdk_game_start", { game: String(game) });
      return true;
    },
    track(name, payload = {}) {
      if (!safeName(name)) return false;
      const cleanPayload = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
      emit("sdk_custom_event", { sdk_event_name: String(name), sdk_payload: cleanPayload });
      return true;
    },
    gameOver({ game, score } = {}) {
      if (!safeName(game) || !Number.isFinite(Number(score))) return false;
      emit("sdk_game_over", { game: String(game), score: Math.max(0, Math.round(Number(score))) });
      return true;
    },
    submitScore() {
      console.warn("PlayBed.submitScore n'est pas public : les scores classés doivent être validés côté serveur.");
      return Promise.reject(new Error("score_submission_not_public"));
    }
  });
})();
