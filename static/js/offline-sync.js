(function () {
  'use strict';

  if (!window.CrewlogQueue) return;
  var Q = window.CrewlogQueue;

  var T = (window.CrewlogI18n) || {
    saved_offline: 'Saved offline — will sync when online',
    queue_pending_one: '1 pending sync',
    queue_pending_many: '{n} pending syncs',
    queue_failed_one: '1 needs attention',
    queue_failed_many: '{n} need attention'
  };

  function tr(key, n) {
    var s = T[key] || key;
    return s.replace('{n}', String(n));
  }

  function ensureBadge() {
    var badge = document.getElementById('crewlog-sync-badge');
    if (badge) return badge;
    var topbar = document.querySelector('nav.topbar .container > div');
    if (!topbar) return null;
    badge = document.createElement('a');
    badge.id = 'crewlog-sync-badge';
    badge.href = '/sync-status';
    badge.style.cssText = 'display:none;align-items:center;gap:0.35rem;padding:0.25rem 0.6rem;border-radius:9999px;font-size:0.72rem;font-weight:600;background:rgba(255,255,255,0.12);color:#fff;text-decoration:none;margin-right:0.5rem;';
    badge.setAttribute('aria-live', 'polite');
    badge.innerHTML = '<span id="crewlog-sync-badge-icon">📡</span><span id="crewlog-sync-badge-text"></span>';
    var rightSide = topbar.querySelector('.desktop-nav') || topbar.lastElementChild;
    if (rightSide) rightSide.parentNode.insertBefore(badge, rightSide);
    else topbar.appendChild(badge);
    return badge;
  }

  function refreshBadge() {
    Q.counts().then(function (c) {
      var badge = ensureBadge();
      if (!badge) return;
      var icon = badge.querySelector('#crewlog-sync-badge-icon');
      var text = badge.querySelector('#crewlog-sync-badge-text');
      if (c.failed > 0) {
        badge.style.display = 'inline-flex';
        badge.style.background = '#dc2626';
        if (icon) icon.textContent = '⚠️';
        if (text) text.textContent = c.failed === 1 ? tr('queue_failed_one', 1) : tr('queue_failed_many', c.failed);
      } else if (c.pending > 0 || c.syncing > 0) {
        var n = c.pending + c.syncing;
        badge.style.display = 'inline-flex';
        badge.style.background = 'rgba(245,158,11,0.85)';
        if (icon) icon.textContent = c.syncing > 0 ? '🔄' : '📡';
        if (text) text.textContent = n === 1 ? tr('queue_pending_one', 1) : tr('queue_pending_many', n);
      } else {
        badge.style.display = 'none';
      }
    }).catch(function () { /* noop */ });
  }

  function flashSavedOffline() {
    try {
      var div = document.createElement('div');
      div.style.cssText = 'position:fixed;top:1rem;left:50%;transform:translateX(-50%);background:#1a2f4a;color:#fff;padding:0.75rem 1.25rem;border-radius:0.75rem;z-index:99998;font-weight:600;box-shadow:0 8px 24px rgba(0,0,0,0.25);font-family:Inter,system-ui,sans-serif;';
      div.textContent = '📡 ' + (T.saved_offline || 'Saved offline');
      document.body.appendChild(div);
      setTimeout(function () { div.remove(); }, 3500);
    } catch (e) { /* noop */ }
  }

  function shouldQueueOnFailure(method) {
    return (method || 'POST').toUpperCase() === 'POST';
  }

  function buildLabel(form) {
    try {
      var fd = new FormData(form);
      var date = fd.get('entry_date');
      var time = fd.get('entry_time');
      var notes = fd.get('notes');
      var bits = [];
      if (date) bits.push(String(date));
      if (time) bits.push(String(time));
      var head = bits.join(' ');
      if (notes) head = (head ? head + ' — ' : '') + String(notes).slice(0, 60);
      return head || 'Logbook entry';
    } catch (e) { return 'Logbook entry'; }
  }

  function attachLogbookForm(form) {
    if (!form || form.dataset.offlineWired === '1') return;
    form.dataset.offlineWired = '1';

    // Inject hidden client_temp_id if not present
    var existing = form.querySelector('input[name="clientTempId"]');
    if (!existing) {
      var inp = document.createElement('input');
      inp.type = 'hidden';
      inp.name = 'clientTempId';
      inp.value = Q.uuidv4();
      form.appendChild(inp);
    }

    form.addEventListener('submit', function (ev) {
      var ctid = form.querySelector('input[name="clientTempId"]').value;
      var method = (form.method || 'post').toUpperCase();
      var action = form.action || window.location.href;

      // If browser believes we are offline, intercept up-front.
      if (typeof navigator !== 'undefined' && navigator.onLine === false && shouldQueueOnFailure(method)) {
        ev.preventDefault();
        var ser = Q.serializeFormData(form);
        Q.enqueue({
          client_temp_id: ctid,
          kind: 'logbook',
          url: action,
          method: method,
          fields: ser.fields,
          label: buildLabel(form)
        }).then(function () {
          flashSavedOffline();
          setTimeout(function () { window.location.href = '/logbook'; }, 600);
        });
      }
      // Online: let it submit normally; clientTempId guarantees server-side dedup.
    });
  }

  function wireForms() {
    document.querySelectorAll('form[data-offline-queue="logbook"]').forEach(attachLogbookForm);
  }

  function trySyncSoon() {
    if (typeof navigator !== 'undefined' && navigator.onLine === false) return;
    Q.syncAll().then(function () { refreshBadge(); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    wireForms();
    refreshBadge();
    trySyncSoon();
  });

  window.addEventListener('online', trySyncSoon);
  window.addEventListener('crewlog:queue-changed', refreshBadge);

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', function (event) {
      if (event && event.data && event.data.type === 'CREWLOG_SYNC') {
        trySyncSoon();
      }
    });
  }
})();
