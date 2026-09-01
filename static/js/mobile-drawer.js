(() => {
    const drawer = document.getElementById('pbMobileDrawer');
    const backdrop = document.getElementById('pbMobileDrawerBackdrop');
    const openButton = document.getElementById('pbMobileMenuButton');
    const closeButton = document.getElementById('pbMobileDrawerClose');

    if (!drawer || !backdrop || !openButton || !closeButton) return;

    const openDrawer = () => {
        drawer.classList.add('is-open');
        backdrop.classList.add('is-open');
        drawer.setAttribute('aria-hidden', 'false');
        openButton.setAttribute('aria-expanded', 'true');
        document.body.classList.add('pb-drawer-open');
        closeButton.focus({ preventScroll: true });
    };

    const closeDrawer = () => {
        drawer.classList.remove('is-open');
        backdrop.classList.remove('is-open');
        drawer.setAttribute('aria-hidden', 'true');
        openButton.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('pb-drawer-open');
        openButton.focus({ preventScroll: true });
    };

    openButton.addEventListener('click', openDrawer);
    closeButton.addEventListener('click', closeDrawer);
    backdrop.addEventListener('click', closeDrawer);

    drawer.addEventListener('click', (event) => {
        if (event.target.closest('a')) closeDrawer();
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && drawer.classList.contains('is-open')) {
            closeDrawer();
        }
    });
})();
