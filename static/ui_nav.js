(function() {
  'use strict';

  var drawer, overlay, openBtn, closeBtn, body;
  var focusableSelector = 'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])';
  var isOpen = false;

  // ── Desktop-sidebar threshold (single source of truth) ─────────────────
  // Read the canonical breakpoint from `--cl-desktop-min-px`, declared in
  // static/ui_breakpoints.css. The hardcoded `1280` below is ONLY a
  // defensive fallback for the (extremely unlikely) case that the CSS
  // variable was not parsed yet — the regression test
  // tests/test_desktop_sidebar_breakpoint_single_source.py asserts the
  // fallback equals the canonical value, so the two cannot drift.
  var DESKTOP_MIN = (function() {
    try {
      var raw = getComputedStyle(document.documentElement)
        .getPropertyValue('--cl-desktop-min-px');
      var n = parseInt(raw, 10);
      if (n > 0) return n;
    } catch (e) { /* ignore — fall through to default */ }
    return 1280;
  })();

  function init() {
    drawer = document.getElementById('nav-drawer');
    overlay = document.getElementById('nav-overlay');
    openBtn = document.getElementById('drawer-open');
    closeBtn = document.getElementById('drawer-close');
    body = document.body;

    if (!drawer) return;

    // ── Desktop sidebar bootstrap ───────────────────────────────────────
    // At >=DESKTOP_MIN px the drawer must always be visible as a
    // permanent left sidebar (display + aria + .drawer-open class).
    // Below the threshold it returns to mobile drawer behaviour and is
    // closed by default unless the user has explicitly opened it via the
    // hamburger. The threshold (currently 1280px) ensures iPad Pro at
    // 1024px landscape gets the mobile drawer pattern, which works
    // reliably on both Safari and Chrome. See static/ui_breakpoints.css
    // for the canonical declaration.
    function applyLayout() {
      if (window.innerWidth >= DESKTOP_MIN) {
        drawer.style.removeProperty('display');
        drawer.setAttribute('aria-hidden', 'false');
        drawer.classList.add('drawer-open');
        body.classList.remove('drawer-scroll-lock');
        if (overlay) overlay.classList.remove('overlay-visible');
        isOpen = false;
      } else if (!isOpen) {
        drawer.setAttribute('aria-hidden', 'true');
        drawer.classList.remove('drawer-open');
      }
    }
    applyLayout();

    var resizeTimer;
    window.addEventListener('resize', function() {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(applyLayout, 100);
    });

    if (!openBtn) { highlightActive(); return; }

    openBtn.addEventListener('click', open);
    if (closeBtn) closeBtn.addEventListener('click', function() {
      if (window.innerWidth < DESKTOP_MIN) close();
    });
    if (overlay) overlay.addEventListener('click', function() {
      if (window.innerWidth < DESKTOP_MIN) close();
    });

    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && isOpen && window.innerWidth < DESKTOP_MIN) {
        close();
        return;
      }
      if (e.key === 'Tab' && isOpen) {
        trapFocus(e);
      }
    });

    var links = drawer.querySelectorAll('a[href]');
    links.forEach(function(link) {
      link.addEventListener('click', function() {
        if (window.innerWidth < DESKTOP_MIN) close();
      });
    });

    var formButtons = drawer.querySelectorAll('form button[type="submit"]');
    formButtons.forEach(function(btn) {
      btn.addEventListener('click', function() {
        if (window.innerWidth < DESKTOP_MIN) close();
      });
    });

    var sections = drawer.querySelectorAll('.drawer-section-toggle');
    sections.forEach(function(toggle) {
      toggle.addEventListener('click', function() {
        var content = this.nextElementSibling;
        var arrow = this.querySelector('.drawer-arrow');
        if (!content) return;
        var hidden = content.classList.contains('hidden');
        content.classList.toggle('hidden');
        if (arrow) {
          arrow.style.transform = hidden ? 'rotate(180deg)' : '';
        }
        this.setAttribute('aria-expanded', hidden ? 'true' : 'false');
      });
    });

    highlightActive();
  }

  function open() {
    isOpen = true;
    drawer.classList.add('drawer-open');
    if (overlay) overlay.classList.add('overlay-visible');
    body.classList.add('drawer-scroll-lock');
    openBtn.setAttribute('aria-expanded', 'true');
    drawer.setAttribute('aria-hidden', 'false');

    var first = drawer.querySelector(focusableSelector);
    if (first) first.focus();
  }

  function close() {
    // On desktop the sidebar is permanently open — never tear it down
    if (window.innerWidth >= DESKTOP_MIN) return;
    isOpen = false;
    drawer.classList.remove('drawer-open');
    if (overlay) overlay.classList.remove('overlay-visible');
    body.classList.remove('drawer-scroll-lock');
    if (openBtn) {
      openBtn.setAttribute('aria-expanded', 'false');
      openBtn.focus();
    }
    drawer.setAttribute('aria-hidden', 'true');
  }

  function trapFocus(e) {
    var focusable = drawer.querySelectorAll(focusableSelector);
    if (focusable.length === 0) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];

    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }

  function highlightActive() {
    var path = window.location.pathname;
    var links = drawer.querySelectorAll('.drawer-link');
    links.forEach(function(link) {
      var href = link.getAttribute('href');
      if (!href) return;
      var match = false;
      if (href === '/') {
        match = path === '/';
      } else {
        match = path === href || path.startsWith(href + '/');
      }
      if (match) {
        link.classList.add('drawer-link-active');
      }
    });
    var desktopNav = document.querySelector('.desktop-nav');
    if (desktopNav) {
      var dLinks = desktopNav.querySelectorAll('.nav-item');
      dLinks.forEach(function(link) {
        var href = link.getAttribute('href');
        if (!href) return;
        var m = false;
        if (href === '/') {
          m = path === '/';
        } else {
          m = path === href || path.startsWith(href + '/');
        }
        if (m) {
          link.classList.add('nav-active');
        }
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
