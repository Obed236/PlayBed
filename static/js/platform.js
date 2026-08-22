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
})();
