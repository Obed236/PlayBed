(() => {
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

    const privacyButton = document.getElementById("privacyCookieSettings");

    // N'initialise le helper Funding Choices que sur les pages où le lien de
    // révocation est réellement présent. La politique de confidentialité reste
    // ainsi totalement dépourvue de balise ou helper de consentement Google.
    if (privacyButton) {
        window.googlefc = window.googlefc || {};
        window.googlefc.callbackQueue = window.googlefc.callbackQueue || [];
        window.googlefc.callbackQueue.push({
            CONSENT_API_READY: () => {
                privacyButton.hidden = false;
            },
        });

        privacyButton.addEventListener("click", () => {
            if (typeof window.googlefc.showRevocationMessage === "function") {
                window.googlefc.showRevocationMessage();
            }
        });
    }
})();
