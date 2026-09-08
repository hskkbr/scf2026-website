(() => {
    const nav = document.querySelector('nav');
    const toggle = nav.querySelector('.nav-toggle');
    const label = toggle.querySelector('.nav-toggle-label');
    const icon = toggle.querySelector('.nav-toggle-icon');
    const mobile = window.matchMedia('(max-width: 768px)');

    const setOpen = (open) => {
        toggle.setAttribute('aria-expanded', String(open));
        label.textContent = open ? '閉じる' : 'メニュー';
        icon.textContent = open ? '×' : '☰';
    };

    toggle.addEventListener('click', () => {
        setOpen(toggle.getAttribute('aria-expanded') !== 'true');
    });

    nav.querySelectorAll('a').forEach((link) => {
        link.addEventListener('click', () => {
            if (!mobile.matches) return;
            setOpen(false);

            // Move keyboard focus out of the collapsed list before navigation.
            const href = link.getAttribute('href');
            const target = href.startsWith('#')
                ? document.getElementById(href.slice(1))
                : null;
            if (target) {
                target.setAttribute('tabindex', '-1');
                target.focus({ preventScroll: true });
            } else {
                toggle.focus({ preventScroll: true });
            }
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && mobile.matches &&
            toggle.getAttribute('aria-expanded') === 'true') {
            setOpen(false);
            toggle.focus({ preventScroll: true });
        }
    });

    document.addEventListener('click', (event) => {
        if (mobile.matches && !nav.contains(event.target)) {
            setOpen(false);
        }
    });

    nav.addEventListener('focusout', (event) => {
        if (mobile.matches && !nav.contains(event.relatedTarget)) {
            setOpen(false);
        }
    });

    mobile.addEventListener('change', () => {
        const focusWasInNav = nav.contains(document.activeElement);
        setOpen(false);
        if (focusWasInNav) {
            const target = mobile.matches ? toggle : nav.querySelector('a');
            target.focus({ preventScroll: true });
        }
    });

    nav.classList.add('is-collapsible');
})();
