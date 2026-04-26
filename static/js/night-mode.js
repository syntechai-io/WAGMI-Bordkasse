(function () {
  'use strict';

  var STORAGE_KEY = 'crewlog-theme';
  var THEMES = { AUTO: 'auto', LIGHT: 'light', NIGHT: 'night' };
  var VALID = { auto: 1, light: 1, night: 1 };

  var mql = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)')) || null;

  function getPref() {
    try {
      var v = localStorage.getItem(STORAGE_KEY);
      if (v && VALID[v]) return v;
    } catch (e) {}
    if (window.__crewlogThemePref && VALID[window.__crewlogThemePref]) {
      return window.__crewlogThemePref;
    }
    return THEMES.AUTO;
  }

  function resolve(pref) {
    if (pref === THEMES.AUTO) {
      return (mql && mql.matches) ? THEMES.NIGHT : THEMES.LIGHT;
    }
    return pref === THEMES.NIGHT ? THEMES.NIGHT : THEMES.LIGHT;
  }

  function apply(pref) {
    var resolved = resolve(pref);
    if (resolved === THEMES.NIGHT) {
      document.documentElement.setAttribute('data-theme', 'night');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', resolved === THEMES.NIGHT ? '#000000' : '#1a2f4a');
    try {
      window.dispatchEvent(new CustomEvent('crewlog:theme-changed', {
        detail: { pref: pref, resolved: resolved }
      }));
    } catch (e) {}
  }

  function getCsrfToken() {
    try {
      var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
      return m ? decodeURIComponent(m[1]) : '';
    } catch (e) { return ''; }
  }

  function persistRemote(pref) {
    try {
      fetch('/api/preferences/theme', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'x-csrftoken': getCsrfToken()
        },
        body: JSON.stringify({ theme: pref })
      }).catch(function () { /* offline ok */ });
    } catch (e) {}
  }

  function setPref(pref) {
    if (!VALID[pref]) pref = THEMES.AUTO;
    try { localStorage.setItem(STORAGE_KEY, pref); } catch (e) {}
    window.__crewlogThemePref = pref;
    apply(pref);
    refreshSwitches();
    persistRemote(pref);
  }

  function buildSwitch(idPrefix) {
    var labels = (window.__crewlogThemeLabels) || { auto: 'Auto', day: 'Day', night: 'Night', label: 'Theme' };
    var wrap = document.createElement('div');
    wrap.className = 'theme-switch';
    wrap.setAttribute('role', 'group');
    wrap.setAttribute('aria-label', labels.label || 'Theme');

    var modes = [
      { key: THEMES.AUTO,  label: '◐', titleKey: 'theme.auto'  },
      { key: THEMES.LIGHT, label: '☀', titleKey: 'theme.day'   },
      { key: THEMES.NIGHT, label: '☾', titleKey: 'theme.night' }
    ];

    modes.forEach(function (m) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'theme-switch__btn';
      b.setAttribute('data-theme-pref', m.key);
      b.setAttribute('id', idPrefix + '-' + m.key);
      b.setAttribute('title', labels[m.key === 'light' ? 'day' : m.key] || m.key);
      b.setAttribute('aria-label', labels[m.key === 'light' ? 'day' : m.key] || m.key);
      b.innerHTML = '<span aria-hidden="true">' + m.label + '</span>' +
                    '<span class="theme-switch__lbl">' + (labels[m.key === 'light' ? 'day' : m.key] || '') + '</span>';
      b.addEventListener('click', function () { setPref(m.key); });
      wrap.appendChild(b);
    });
    return wrap;
  }

  function refreshSwitches() {
    var current = getPref();
    document.querySelectorAll('.theme-switch__btn').forEach(function (btn) {
      var on = btn.getAttribute('data-theme-pref') === current;
      btn.setAttribute('aria-pressed', String(on));
      btn.classList.toggle('is-active', on);
    });
  }

  function ensureTopbarSwitch() {
    if (document.getElementById('theme-switch-topbar-wrap')) return;
    var langPill = document.querySelector('nav.topbar .desktop-nav .lang-pill');
    if (!langPill || !langPill.parentNode) return;
    var sw = buildSwitch('theme-switch-topbar');
    sw.id = 'theme-switch-topbar-wrap';
    langPill.parentNode.insertBefore(sw, langPill);
  }

  // Mounts the 3-segment switch into the mobile/iPad topbar slot so it is
  // visible at <1280px viewports where `.desktop-nav` is hidden. The slot
  // markup lives in templates/layout.html (.topbar-mobile-actions).
  function ensureMobileTopbarSwitch() {
    if (document.getElementById('theme-switch-topbar-mobile-wrap')) return;
    var slot = document.getElementById('topbar-mobile-theme-slot');
    if (!slot) return;
    var sw = buildSwitch('theme-switch-topbar-mobile');
    sw.id = 'theme-switch-topbar-mobile-wrap';
    sw.classList.add('theme-switch--topbar-mobile');
    slot.appendChild(sw);
  }

  function ensureDrawerSwitch() {
    var drawerBody = document.querySelector('#nav-drawer .drawer-body');
    if (!drawerBody || document.getElementById('theme-switch-drawer-wrap')) return;
    var holder = document.createElement('div');
    holder.id = 'theme-switch-drawer-wrap';
    holder.style.cssText = 'padding: 0.5rem 1.15rem;';
    var sw = buildSwitch('theme-switch-drawer');
    sw.classList.add('theme-switch--drawer');
    holder.appendChild(sw);
    var langPillContainer = drawerBody.querySelector('.lang-pill');
    if (langPillContainer && langPillContainer.parentNode && langPillContainer.parentNode.parentNode === drawerBody) {
      drawerBody.insertBefore(holder, langPillContainer.parentNode);
    } else {
      drawerBody.appendChild(holder);
    }
  }

  // Re-resolve on system color scheme change while in Auto mode.
  if (mql && mql.addEventListener) {
    mql.addEventListener('change', function () {
      if (getPref() === THEMES.AUTO) apply(THEMES.AUTO);
    });
  } else if (mql && mql.addListener) {
    mql.addListener(function () { if (getPref() === THEMES.AUTO) apply(THEMES.AUTO); });
  }

  // Apply on script eval (no-flash backup; head script already did this for night).
  apply(getPref());

  // Account chip in the mobile topbar opens the navigation drawer (where
  // the user info + Logout button live). Avoids adding a new route while
  // giving users a visible account affordance at <1280px.
  function wireMobileAccountChip() {
    var chip = document.getElementById('topbar-account-chip');
    if (!chip || chip.__crewlogWired) return;
    chip.__crewlogWired = true;
    chip.addEventListener('click', function (e) {
      e.preventDefault();
      var hamburger = document.getElementById('drawer-open');
      if (hamburger && typeof hamburger.click === 'function') {
        hamburger.click();
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    ensureTopbarSwitch();
    ensureMobileTopbarSwitch();
    ensureDrawerSwitch();
    wireMobileAccountChip();
    refreshSwitches();
  });

  window.CrewlogNightMode = {
    get: getPref,
    set: setPref,
    THEMES: THEMES
  };
})();
