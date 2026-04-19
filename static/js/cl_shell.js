(function () {
    'use strict';

    const root = document.documentElement;
    const body = document.body;

    function measureBar(selector, varName, presenceFlag) {
        const el = document.querySelector(selector);
        if (!el) {
            root.style.setProperty(varName, '0px');
            if (presenceFlag) body.removeAttribute(presenceFlag);
            return;
        }
        if (presenceFlag) body.setAttribute(presenceFlag, '1');
        const apply = () => {
            const h = Math.ceil(el.getBoundingClientRect().height);
            root.style.setProperty(varName, h + 'px');
        };
        apply();
        if ('ResizeObserver' in window) {
            new ResizeObserver(apply).observe(el);
        }
        window.addEventListener('resize', apply, { passive: true });
        window.addEventListener('orientationchange', apply, { passive: true });
    }

    function init() {
        // Order matters: actionbar presence trumps tab bar (CSS hides tabbar
        // when body[data-has-actionbar="1"]).
        measureBar('.cl-actionbar', '--cl-actionbar-h', 'data-has-actionbar');
        measureBar('.cl-tabbar',    '--cl-tabbar-h',    null);

        // Highlight active tab based on current path.
        try {
            const path = window.location.pathname;
            document.querySelectorAll('.cl-tabbar__item[data-match]').forEach(function (a) {
                const patterns = (a.getAttribute('data-match') || '').split('|').map(function (s) { return s.trim(); }).filter(Boolean);
                const match = patterns.some(function (p) {
                    if (!p) return false;
                    if (p === '/') return path === '/' || path === '';
                    return path === p || path.indexOf(p + '/') === 0 || path.indexOf(p) === 0;
                });
                if (match) a.classList.add('cl-tabbar__item--active');
            });
        } catch (e) {}
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
