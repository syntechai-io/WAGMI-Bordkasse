(function() {
  'use strict';

  var drawer, overlay, openBtn, closeBtn, body;
  var focusableSelector = 'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])';
  var isOpen = false;

  function init() {
    drawer = document.getElementById('nav-drawer');
    overlay = document.getElementById('nav-overlay');
    openBtn = document.getElementById('drawer-open');
    closeBtn = document.getElementById('drawer-close');
    body = document.body;

    if (!drawer || !openBtn) return;

    openBtn.addEventListener('click', open);
    if (closeBtn) closeBtn.addEventListener('click', close);
    if (overlay) overlay.addEventListener('click', close);

    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && isOpen) {
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
        close();
      });
    });

    var formButtons = drawer.querySelectorAll('form button[type="submit"]');
    formButtons.forEach(function(btn) {
      btn.addEventListener('click', function() {
        close();
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
    isOpen = false;
    drawer.classList.remove('drawer-open');
    if (overlay) overlay.classList.remove('overlay-visible');
    body.classList.remove('drawer-scroll-lock');
    openBtn.setAttribute('aria-expanded', 'false');
    drawer.setAttribute('aria-hidden', 'true');
    openBtn.focus();
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
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
