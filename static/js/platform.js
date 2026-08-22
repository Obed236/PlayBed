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

    if (privacyButton) {
        window.googlefc = window.googlefc || {};
        window.googlefc.callbackQueue = window.googlefc.callbackQueue || [];

        // Google recommande de n'afficher le point d'entrée qu'une fois l'API
        // de consentement réellement chargée et appelable.
        window.googlefc.callbackQueue.push({
            CONSENT_API_READY: () => {
                privacyButton.hidden = false;
            },
        });

        privacyButton.addEventListener("click", (event) => {
            event.preventDefault();
            window.googlefc.callbackQueue.push({
                CONSENT_API_READY: () => {
                    if (typeof window.googlefc.showRevocationMessage === "function") {
                        window.googlefc.showRevocationMessage();
                    }
                },
            });
        });
    }
})();
