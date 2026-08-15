(() => {
    if ("serviceWorker" in navigator) {
        window.addEventListener("load", () => {
            navigator.serviceWorker.register("/service-worker.js").catch(() => {});
        });
    }

    const buttons = Array.from(document.querySelectorAll("[data-pwa-install]"));
    if (!buttons.length) return;

    const isStandalone =
        window.matchMedia("(display-mode: standalone)").matches ||
        window.navigator.standalone === true;
    const isIOS = /iphone|ipad|ipod/i.test(window.navigator.userAgent);
    let deferredPrompt = null;

    const showButtons = () => buttons.forEach((button) => { button.hidden = false; });
    const hideButtons = () => buttons.forEach((button) => { button.hidden = true; });

    if (isStandalone) {
        hideButtons();
        return;
    }

    if (isIOS) showButtons();

    window.addEventListener("beforeinstallprompt", (event) => {
        event.preventDefault();
        deferredPrompt = event;
        showButtons();
    });

    buttons.forEach((button) => {
        button.addEventListener("click", async () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                await deferredPrompt.userChoice;
                deferredPrompt = null;
                hideButtons();
                return;
            }

            if (isIOS) {
                window.alert("Sur Safari : touche Partager, puis « Sur l’écran d’accueil » pour installer PlayBed.");
            }
        });
    });

    window.addEventListener("appinstalled", () => {
        deferredPrompt = null;
        hideButtons();
    });
})();
