(function() {
  'use strict';

  if (!window.Capacitor || !window.Capacitor.isNativePlatform()) return;

  window.IS_NATIVE_IOS = true;

  var Browser = null;
  try {
    Browser = window.Capacitor.Plugins.Browser;
  } catch(e) {}

  var STRIPE_PATTERNS = [
    'checkout.stripe.com',
    'billing.stripe.com'
  ];

  function isStripeUrl(url) {
    if (!url) return false;
    for (var i = 0; i < STRIPE_PATTERNS.length; i++) {
      if (url.indexOf(STRIPE_PATTERNS[i]) !== -1) return true;
    }
    return false;
  }

  function openExternal(url) {
    if (Browser) {
      Browser.open({ url: url, presentationStyle: 'fullscreen' });
    } else {
      window.open(url, '_system');
    }
  }

  window._crewlogOpenExternal = openExternal;

  function hideNativePaymentUI() {
    var selectors = [
      '[data-ios-hide]',
      '[data-stripe-external]'
    ];
    selectors.forEach(function(sel) {
      var els = document.querySelectorAll(sel);
      els.forEach(function(el) { el.style.display = 'none'; });
    });

    var iosOnly = document.querySelectorAll('[data-ios-only]');
    iosOnly.forEach(function(el) { el.style.display = ''; });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', hideNativePaymentUI);
  } else {
    hideNativePaymentUI();
  }
  document.body.addEventListener('htmx:afterSwap', hideNativePaymentUI);
  document.body.addEventListener('htmx:afterSettle', hideNativePaymentUI);

  var _origAssign = Object.getOwnPropertyDescriptor(window.location.__proto__, 'href');
  if (_origAssign && _origAssign.set) {
    Object.defineProperty(window.location.__proto__, 'href', {
      set: function(url) {
        if (isStripeUrl(url)) {
          openExternal(url);
          return;
        }
        _origAssign.set.call(this, url);
      },
      get: _origAssign.get,
      configurable: true,
      enumerable: true
    });
  }

  document.addEventListener('click', function(e) {
    var anchor = e.target.closest('a[data-stripe-external]');
    if (!anchor) return;
    var href = anchor.href || anchor.getAttribute('href');
    if (href) {
      e.preventDefault();
      e.stopPropagation();
      openExternal(href);
    }
  }, true);

  document.addEventListener('click', function(e) {
    var anchor = e.target.closest('a[data-footer-legal]');
    if (!anchor) return;
    var href = anchor.href || anchor.getAttribute('href');
    if (href) {
      e.preventDefault();
      e.stopPropagation();
      openExternal(href);
    }
  }, true);

  var origXHROpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function() {
    this._crewlogUrl = arguments[1];
    return origXHROpen.apply(this, arguments);
  };

  var origFetch = window.fetch;
  window.fetch = function() {
    var url = arguments[0];
    if (typeof url === 'string' && (url.indexOf('/billing/checkout') !== -1 || url.indexOf('/billing/portal') !== -1)) {
      return origFetch.apply(this, arguments).then(function(response) {
        var clone = response.clone();
        clone.json().then(function(data) {
          var stripeUrl = data.checkout_url || data.portal_url;
          if (stripeUrl && isStripeUrl(stripeUrl)) {
            openExternal(stripeUrl);
          }
        }).catch(function() {});
        return response;
      });
    }
    return origFetch.apply(this, arguments);
  };

  document.body.addEventListener('htmx:beforeRedirect', function(e) {
    var url = e.detail && e.detail.redirectUrl;
    if (url && isStripeUrl(url)) {
      e.preventDefault();
      openExternal(url);
    }
  });

  if (typeof window.htmx !== 'undefined') {
    document.body.addEventListener('htmx:beforeSwap', function(e) {
      var xhr = e.detail && e.detail.xhr;
      if (xhr) {
        var redirect = xhr.getResponseHeader('HX-Redirect');
        if (redirect && isStripeUrl(redirect)) {
          e.preventDefault();
          openExternal(redirect);
        }
      }
    });
  }

  function checkSession() {
    fetch('/api/whoami', { credentials: 'same-origin' })
      .then(function(res) {
        if (!res.ok) {
          window.location.href = '/login';
          return;
        }
        return res.json();
      })
      .then(function(data) {
        if (data && data.mode === 'none') {
          window.location.href = '/login';
        }
      })
      .catch(function() {});
  }

  try {
    var AppPlugin = window.Capacitor.Plugins.App;
    if (AppPlugin && AppPlugin.addListener) {
      AppPlugin.addListener('appStateChange', function(state) {
        if (state.isActive) {
          checkSession();
        }
      });
    }
  } catch(e) {}

  var offlineOverlay = null;
  function showOfflineScreen() {
    if (offlineOverlay) return;
    offlineOverlay = document.createElement('div');
    offlineOverlay.id = 'crewlog-offline';
    offlineOverlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:linear-gradient(135deg,#1a2f4a 0%,#2c4a6e 100%);color:white;display:flex;align-items:center;justify-content:center;z-index:99999;font-family:-apple-system,BlinkMacSystemFont,Inter,sans-serif;';
    offlineOverlay.innerHTML = '<div style="text-align:center;padding:2rem;"><div style="font-size:4rem;margin-bottom:1rem;">⚓</div><h1 style="font-size:1.5rem;font-weight:700;margin-bottom:0.5rem;">No Connection</h1><p style="font-size:0.95rem;opacity:0.8;margin-bottom:2rem;">Please check your internet connection and try again.</p><button id="crewlog-retry" style="background:white;color:#1a2f4a;padding:0.9rem 2.5rem;border-radius:12px;font-size:1.1rem;font-weight:700;border:none;cursor:pointer;">Retry</button></div>';
    document.body.appendChild(offlineOverlay);
    document.getElementById('crewlog-retry').addEventListener('click', function() {
      hideOfflineScreen();
      window.location.reload();
    });
  }

  function hideOfflineScreen() {
    if (offlineOverlay) {
      offlineOverlay.remove();
      offlineOverlay = null;
    }
  }

  window.addEventListener('offline', showOfflineScreen);
  window.addEventListener('online', hideOfflineScreen);
  if (!navigator.onLine) showOfflineScreen();

  // ---------------------------------------------------------------------------
  // Biometric (Face ID / Touch ID) login helpers
  // ---------------------------------------------------------------------------
  // Uses @aparajita/capacitor-biometric-auth (LocalAuthentication) and
  // @aparajita/capacitor-secure-storage (iOS Keychain). Credentials saved here
  // are only retrievable after a successful biometric prompt.
  var BIO_KEY_EMAIL = 'crewlog.bio.email';
  var BIO_KEY_PASSWORD = 'crewlog.bio.password';

  function _bioPlugin() {
    try { return window.Capacitor.Plugins.BiometricAuth || null; } catch (e) { return null; }
  }
  function _securePlugin() {
    try { return window.Capacitor.Plugins.SecureStorage || null; } catch (e) { return null; }
  }

  async function bioIsAvailable() {
    var p = _bioPlugin();
    if (!p) return { available: false, reason: 'plugin_missing' };
    try {
      var info = await p.checkBiometry();
      return {
        available: !!info.isAvailable,
        biometryType: info.biometryType,
        reason: info.reason || null
      };
    } catch (e) {
      return { available: false, reason: 'check_failed' };
    }
  }

  async function bioHasSavedCredentials() {
    var s = _securePlugin();
    if (!s) return false;
    try {
      var v = await s.get({ key: BIO_KEY_EMAIL });
      return !!(v && v.value);
    } catch (e) {
      return false;
    }
  }

  async function bioAuthenticateAndLoad(reason) {
    var p = _bioPlugin();
    var s = _securePlugin();
    if (!p || !s) throw new Error('plugin_missing');
    // Check Keychain BEFORE prompting for biometrics — if creds were wiped
    // between init and the click, don't subject the user to a Face ID prompt
    // that can only end in a 'no_credentials' error.
    var emailRes, pwRes;
    try {
      emailRes = await s.get({ key: BIO_KEY_EMAIL });
      pwRes = await s.get({ key: BIO_KEY_PASSWORD });
    } catch (e) {
      throw new Error('no_credentials');
    }
    if (!emailRes || !emailRes.value || !pwRes || !pwRes.value) {
      throw new Error('no_credentials');
    }
    await p.authenticate({
      reason: reason || 'Sign in to CrewLog',
      cancelTitle: 'Cancel',
      allowDeviceCredential: false,
      iosFallbackTitle: ''
    });
    return { email: emailRes.value, password: pwRes.value };
  }

  async function bioSaveCredentials(email, password) {
    var s = _securePlugin();
    if (!s) throw new Error('plugin_missing');
    await s.set({ key: BIO_KEY_EMAIL, value: String(email || '') });
    await s.set({ key: BIO_KEY_PASSWORD, value: String(password || '') });
  }

  async function bioClearCredentials() {
    var s = _securePlugin();
    if (!s) return;
    try { await s.remove({ key: BIO_KEY_EMAIL }); } catch (e) {}
    try { await s.remove({ key: BIO_KEY_PASSWORD }); } catch (e) {}
  }

  window.CrewlogBiometric = {
    isAvailable: bioIsAvailable,
    hasSaved: bioHasSavedCredentials,
    authenticateAndLoad: bioAuthenticateAndLoad,
    save: bioSaveCredentials,
    clear: bioClearCredentials
  };

  // ---------------------------------------------------------------------------
  // iOS Home/Lock Screen Widget — Keychain bridge
  // ---------------------------------------------------------------------------
  // The web /about page issues a long-lived bearer token via POST /api/widget/token.
  // We persist that token to the iOS Keychain so the WidgetKit extension can read
  // it (the extension uses an App Group keychain access group declared in its
  // entitlements; see ios_app/README_IOS.md). The bridge also writes the API
  // base URL so the widget knows where to fetch /api/widget/snapshot.
  var WIDGET_KEY_TOKEN = 'crewlog.widget.token';
  var WIDGET_KEY_BASE_URL = 'crewlog.widget.baseUrl';

  async function widgetSaveToken(token) {
    var s = _securePlugin();
    if (!s) return false;
    try {
      await s.set({ key: WIDGET_KEY_TOKEN, value: String(token || '') });
      await s.set({ key: WIDGET_KEY_BASE_URL, value: String(window.location.origin || '') });
      return true;
    } catch (e) { return false; }
  }
  async function widgetClearToken() {
    var s = _securePlugin();
    if (!s) return;
    try { await s.remove({ key: WIDGET_KEY_TOKEN }); } catch (e) {}
    try { await s.remove({ key: WIDGET_KEY_BASE_URL }); } catch (e) {}
  }

  window.addEventListener('crewlog:widget-token-issued', function(ev) {
    var tok = ev && ev.detail && ev.detail.token;
    if (tok) widgetSaveToken(tok);
  });
  window.addEventListener('crewlog:widget-token-revoked', function() {
    widgetClearToken();
  });

  window.CrewlogWidget = {
    saveToken: widgetSaveToken,
    clearToken: widgetClearToken
  };
})();
