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
})();
