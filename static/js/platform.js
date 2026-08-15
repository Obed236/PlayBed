(() => {
    const CONSENT_KEY = "playbed-consent-v1";
    const ADSENSE_ID = "ca-pub-8115913863262508";
    const menuToggle = document.getElementById("mobileMenuToggle");
    const navigation = document.getElementById("mainNavigation");
    if (menuToggle && navigation) {
        menuToggle.addEventListener("click", () => { const open = navigation.classList.toggle("open"); menuToggle.setAttribute("aria-expanded", String(open)); menuToggle.textContent = open ? "✕" : "☰"; });
        navigation.addEventListener("click", (event) => { if (event.target.closest("a") && navigation.classList.contains("open")) { navigation.classList.remove("open"); menuToggle.setAttribute("aria-expanded", "false"); menuToggle.textContent = "☰"; } });
    }
    const panel = document.getElementById("consentPanel");
    const adsCheckbox = document.getElementById("adsConsent");
    const acceptAll = document.getElementById("acceptAllConsent");
    const rejectAll = document.getElementById("rejectAllConsent");
    const saveConsent = document.getElementById("saveConsent");
    const openPreferences = document.getElementById("openPrivacyPreferences");
    let lastFocused = null;
    function readConsent() { try { const value = JSON.parse(localStorage.getItem(CONSENT_KEY)); if (!value || typeof value.ads !== "boolean") return null; return value; } catch { return null; } }
    function updateGoogleConsent(adsAllowed) { if (typeof window.gtag !== "function") return; window.gtag("consent", "update", {ad_storage: adsAllowed ? "granted" : "denied", ad_user_data: adsAllowed ? "granted" : "denied", ad_personalization: adsAllowed ? "granted" : "denied", analytics_storage: "denied"}); }
    function loadAdsense() { if (document.querySelector('script[data-playbed-adsense="true"]')) return; const script = document.createElement("script"); script.async = true; script.crossOrigin = "anonymous"; script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${ADSENSE_ID}`; script.dataset.playbedAdsense = "true"; document.head.appendChild(script); }
    function applyConsent(consent) { updateGoogleConsent(consent.ads); if (consent.ads && document.body?.dataset.adsPage === "true") loadAdsense(); }
    function storeConsent(ads) { const consent = {ads: Boolean(ads), version: 1, updatedAt: new Date().toISOString()}; localStorage.setItem(CONSENT_KEY, JSON.stringify(consent)); applyConsent(consent); closePanel(); }
    function openPanel() { if (!panel) return; lastFocused = document.activeElement; const current = readConsent(); if (adsCheckbox) adsCheckbox.checked = Boolean(current?.ads); panel.hidden = false; document.body.style.overflow = "hidden"; window.setTimeout(() => { const target = panel.querySelector("button, input, a"); if (target) target.focus(); }, 0); }
    function closePanel() { if (!panel) return; panel.hidden = true; document.body.style.overflow = ""; if (lastFocused && typeof lastFocused.focus === "function") lastFocused.focus(); }
    const existingConsent = readConsent(); if (existingConsent) applyConsent(existingConsent); else window.setTimeout(openPanel, 250);
    acceptAll?.addEventListener("click", () => storeConsent(true)); rejectAll?.addEventListener("click", () => storeConsent(false)); saveConsent?.addEventListener("click", () => storeConsent(Boolean(adsCheckbox?.checked))); openPreferences?.addEventListener("click", openPanel);
    document.addEventListener("keydown", (event) => { if (event.key === "Escape" && panel && !panel.hidden && readConsent()) closePanel(); });
})();
