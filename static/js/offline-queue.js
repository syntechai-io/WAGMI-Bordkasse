(function (global) {
  'use strict';

  var DB_NAME = 'crewlog-offline-v1';
  var STORE = 'queue';
  var DB_VERSION = 1;

  var STATUS = {
    PENDING: 'pending',
    SYNCING: 'syncing',
    FAILED: 'failed',
    SYNCED: 'synced'
  };

  var MAX_AUTO_ATTEMPTS = 5;

  function openDB() {
    return new Promise(function (resolve, reject) {
      var req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = function (e) {
        var db = e.target.result;
        if (!db.objectStoreNames.contains(STORE)) {
          var os = db.createObjectStore(STORE, { keyPath: 'client_temp_id' });
          os.createIndex('status', 'status', { unique: false });
          os.createIndex('created_at', 'created_at', { unique: false });
        }
      };
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error); };
    });
  }

  function tx(db, mode) {
    return db.transaction(STORE, mode).objectStore(STORE);
  }

  function put(rec) {
    return openDB().then(function (db) {
      return new Promise(function (resolve, reject) {
        var r = tx(db, 'readwrite').put(rec);
        r.onsuccess = function () { resolve(rec); };
        r.onerror = function () { reject(r.error); };
      });
    });
  }

  function get(id) {
    return openDB().then(function (db) {
      return new Promise(function (resolve, reject) {
        var r = tx(db, 'readonly').get(id);
        r.onsuccess = function () { resolve(r.result || null); };
        r.onerror = function () { reject(r.error); };
      });
    });
  }

  function del(id) {
    return openDB().then(function (db) {
      return new Promise(function (resolve, reject) {
        var r = tx(db, 'readwrite').delete(id);
        r.onsuccess = function () { resolve(true); };
        r.onerror = function () { reject(r.error); };
      });
    });
  }

  function listAll() {
    return openDB().then(function (db) {
      return new Promise(function (resolve, reject) {
        var out = [];
        var idx = tx(db, 'readonly').index('created_at');
        var cur = idx.openCursor();
        cur.onsuccess = function (e) {
          var c = e.target.result;
          if (c) { out.push(c.value); c.continue(); } else { resolve(out); }
        };
        cur.onerror = function () { reject(cur.error); };
      });
    });
  }

  function listByStatus(status) {
    return listAll().then(function (rows) {
      return rows.filter(function (r) { return r.status === status; });
    });
  }

  function counts() {
    return listAll().then(function (rows) {
      var c = { pending: 0, failed: 0, syncing: 0, total: rows.length };
      rows.forEach(function (r) {
        if (r.status === STATUS.PENDING) c.pending++;
        else if (r.status === STATUS.FAILED) c.failed++;
        else if (r.status === STATUS.SYNCING) c.syncing++;
      });
      return c;
    });
  }

  function uuidv4() {
    if (global.crypto && global.crypto.randomUUID) return global.crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = Math.random() * 16 | 0;
      var v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  function serializeFormData(form) {
    var fd = new FormData(form);
    var fields = [];
    var skippedFiles = [];
    fd.forEach(function (value, key) {
      if (value instanceof File) {
        if (value.size > 0) skippedFiles.push(value.name || key);
        return;
      }
      fields.push([key, String(value)]);
    });
    return { fields: fields, skippedFiles: skippedFiles };
  }

  function rebuildFormData(fields) {
    var fd = new FormData();
    fields.forEach(function (kv) { fd.append(kv[0], kv[1]); });
    return fd;
  }

  function getCookie(name) {
    var m = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/[$()*+.?[\\\]^{|}]/g, '\\$&') + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : null;
  }

  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    var input = document.querySelector('input[name="csrf_token"]');
    if (input && input.value) return input.value;
    return getCookie('fastapi-csrf-token');
  }

  function enqueue(record) {
    if (!record.client_temp_id) record.client_temp_id = uuidv4();
    record.created_at = record.created_at || Date.now();
    record.attempts = record.attempts || 0;
    record.status = record.status || STATUS.PENDING;
    record.last_error = record.last_error || null;
    return put(record).then(function (r) {
      notifyChange();
      return r;
    });
  }

  function postOne(rec) {
    var fd = rebuildFormData(rec.fields || []);
    var headers = {};
    var csrf = getCsrfToken();
    if (csrf) headers['x-csrf-token'] = csrf;
    return fetch(rec.url, {
      method: rec.method || 'POST',
      body: fd,
      headers: headers,
      credentials: 'same-origin',
      redirect: 'manual'
    }).then(function (resp) {
      var status = resp.status;
      if (status >= 200 && status < 400) return { ok: true, status: status };
      if (status === 0 || status === 408 || status === 429 || status >= 500) {
        return { ok: false, status: status, retriable: true };
      }
      return { ok: false, status: status, retriable: false };
    });
  }

  function syncOne(id) {
    return get(id).then(function (rec) {
      if (!rec) return { ok: false, missing: true };
      rec.status = STATUS.SYNCING;
      rec.attempts = (rec.attempts || 0) + 1;
      return put(rec).then(function () {
        notifyChange();
        return postOne(rec).then(function (res) {
          if (res.ok) {
            return del(rec.client_temp_id).then(function () {
              notifyChange();
              return { ok: true };
            });
          }
          rec.status = res.retriable && rec.attempts < MAX_AUTO_ATTEMPTS
            ? STATUS.PENDING
            : STATUS.FAILED;
          rec.last_error = 'HTTP ' + res.status;
          return put(rec).then(function () {
            notifyChange();
            return { ok: false, status: res.status, status_label: rec.status };
          });
        }).catch(function (err) {
          rec.status = rec.attempts < MAX_AUTO_ATTEMPTS ? STATUS.PENDING : STATUS.FAILED;
          rec.last_error = String(err && err.message || err);
          return put(rec).then(function () {
            notifyChange();
            return { ok: false, error: rec.last_error, status_label: rec.status };
          });
        });
      });
    });
  }

  var syncing = false;
  function syncAll() {
    if (syncing) return Promise.resolve({ ok: true, skipped: true });
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      return Promise.resolve({ ok: false, offline: true });
    }
    syncing = true;
    return listByStatus(STATUS.PENDING).then(function (pending) {
      var p = Promise.resolve();
      var results = [];
      pending.forEach(function (rec) {
        p = p.then(function () {
          return syncOne(rec.client_temp_id).then(function (r) { results.push(r); });
        });
      });
      return p.then(function () { syncing = false; return { ok: true, results: results }; });
    }).catch(function (e) { syncing = false; throw e; });
  }

  function retryFailed(id) {
    return get(id).then(function (rec) {
      if (!rec) return null;
      rec.status = STATUS.PENDING;
      rec.attempts = 0;
      rec.last_error = null;
      return put(rec).then(function () {
        notifyChange();
        return syncOne(id);
      });
    });
  }

  function discard(id) { return del(id).then(function (r) { notifyChange(); return r; }); }

  function notifyChange() {
    try {
      window.dispatchEvent(new CustomEvent('crewlog:queue-changed'));
    } catch (e) { /* noop */ }
  }

  global.CrewlogQueue = {
    STATUS: STATUS,
    enqueue: enqueue,
    serializeFormData: serializeFormData,
    listAll: listAll,
    listByStatus: listByStatus,
    counts: counts,
    syncAll: syncAll,
    syncOne: syncOne,
    retryFailed: retryFailed,
    discard: discard,
    uuidv4: uuidv4
  };
})(window);
