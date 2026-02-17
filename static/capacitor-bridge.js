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
})();
