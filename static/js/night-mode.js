(function () {
  'use strict';

  var STORAGE_KEY = 'crewlog-theme';
  var THEMES = { LIGHT: 'light', NIGHT: 'night' };

  function getTheme() {
    try { return localStorage.getItem(STORAGE_KEY) || THEMES.LIGHT; }
    catch (e) { return THEMES.LIGHT; }
  }

  function setTheme(theme) {
    if (theme !== THEMES.LIGHT && theme !== THEMES.NIGHT) theme = THEMES.LIGHT;
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem(STORAGE_KEY, theme); } catch (e) { /* noop */ }
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', theme === THEMES.NIGHT ? '#000000' : '#1a2f4a');
    refreshButtons();
    try { window.dispatchEvent(new CustomEvent('crewlog:theme-changed', { detail: { theme: theme } })); }
    catch (e) { /* noop */ }
  }

  function toggle() {
    setTheme(getTheme() === THEMES.NIGHT ? THEMES.LIGHT : THEMES.NIGHT);
  }

  function refreshButtons() {
    var current = getTheme();
    var label = current === THEMES.NIGHT ? '☀️' : '🌙';
    var aria = current === THEMES.NIGHT ? 'Switch to day mode' : 'Switch to night mode';
    document.querySelectorAll('[data-night-toggle]').forEach(function (btn) {
      var icon = btn.querySelector('.night-toggle-icon');
      if (icon) icon.textContent = label;
      else btn.textContent = label;
      btn.setAttribute('aria-pressed', String(current === THEMES.NIGHT));
      btn.setAttribute('title', aria);
      btn.setAttribute('aria-label', aria);
    });
  }

  function ensureTopbarToggle() {
    if (document.getElementById('night-toggle-topbar')) return;
    var langPill = document.querySelector('nav.topbar .desktop-nav .lang-pill');
    if (!langPill || !langPill.parentNode) return;
    var btn = document.createElement('button');
    btn.id = 'night-toggle-topbar';
    btn.type = 'button';
    btn.className = 'night-toggle';
    btn.setAttribute('data-night-toggle', '1');
    btn.innerHTML = '<span class="night-toggle-icon">🌙</span>';
    langPill.parentNode.insertBefore(btn, langPill);
    btn.addEventListener('click', toggle);
  }

  function ensureDrawerToggle() {
    var drawerBody = document.querySelector('#nav-drawer .drawer-body');
    if (!drawerBody || document.getElementById('night-toggle-drawer')) return;
    var wrap = document.createElement('div');
    wrap.style.cssText = 'padding: 0.5rem 1.15rem;';
    var btn = document.createElement('button');
    btn.id = 'night-toggle-drawer';
    btn.type = 'button';
    btn.className = 'night-toggle';
    btn.setAttribute('data-night-toggle', '1');
    btn.innerHTML = '<span class="night-toggle-icon">🌙</span><span style="margin-left:0.4rem;">Night</span>';
    btn.addEventListener('click', toggle);
    wrap.appendChild(btn);
    var langPillContainer = drawerBody.querySelector('.lang-pill');
    if (langPillContainer && langPillContainer.parentNode && langPillContainer.parentNode.parentNode === drawerBody) {
      drawerBody.insertBefore(wrap, langPillContainer.parentNode);
    } else {
      drawerBody.appendChild(wrap);
    }
  }

  // Apply early to avoid flash
  setTheme(getTheme());

  document.addEventListener('DOMContentLoaded', function () {
    ensureTopbarToggle();
    ensureDrawerToggle();
    refreshButtons();
  });

  window.CrewlogNightMode = {
    get: getTheme,
    set: setTheme,
    toggle: toggle,
    THEMES: THEMES
  };
})();
