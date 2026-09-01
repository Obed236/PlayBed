(() => {
    const body = document.body;
    if (!body || body.classList.contains('pb-immersive-page')) return;

    const nav = document.querySelector('.pb-mobile-nav');
    if (!nav) return;

    const links = Array.from(nav.querySelectorAll('[data-swipe-tab]'));
    if (links.length < 2) return;

    const coarsePointer = window.matchMedia('(pointer: coarse)').matches;
    const mobileViewport = window.matchMedia('(max-width: 820px)').matches;
    if (!coarsePointer || !mobileViewport) return;

    let startX = 0;
    let startY = 0;
    let tracking = false;
    let blocked = false;

    const isInteractiveTarget = (target) => Boolean(target.closest(
        'input, textarea, select, button, a, [contenteditable="true"], [data-no-swipe]'
    ));

    const activeIndex = () => {
        const marked = links.findIndex((link) => link.classList.contains('is-active'));
        if (marked >= 0) return marked;

        const section = body.dataset.navSection;
        const bySection = links.findIndex((link) => link.dataset.swipeTab === section);
        return bySection >= 0 ? bySection : 0;
    };

    document.addEventListener('touchstart', (event) => {
        if (event.touches.length !== 1) return;
        const target = event.target;
        blocked = isInteractiveTarget(target);
        if (blocked) return;

        const touch = event.touches[0];
        startX = touch.clientX;
        startY = touch.clientY;
        tracking = true;
    }, { passive: true });

    document.addEventListener('touchend', (event) => {
        if (!tracking || blocked || event.changedTouches.length !== 1) {
            tracking = false;
            blocked = false;
            return;
        }

        const touch = event.changedTouches[0];
        const dx = touch.clientX - startX;
        const dy = touch.clientY - startY;
        tracking = false;
        blocked = false;

        const horizontalEnough = Math.abs(dx) >= 70 && Math.abs(dx) > Math.abs(dy) * 1.35;
        if (!horizontalEnough) return;

        const current = activeIndex();
        const next = dx < 0 ? current + 1 : current - 1;
        if (next < 0 || next >= links.length) return;

        const destination = links[next].href;
        if (!destination) return;

        body.classList.add(dx < 0 ? 'pb-swipe-left' : 'pb-swipe-right');
        window.setTimeout(() => {
            window.location.href = destination;
        }, 90);
    }, { passive: true });
})();
