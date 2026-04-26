// CACHE_NAME is rewritten by the /sw.js route in main.py to `crewlog-v<hash>`,
// where <hash> is derived from the bundled stylesheet AND JavaScript contents
// (see asset_version.py). A CSS- or JS-only deploy therefore rotates the cache
// name and the `?v=` query string on the templates' <link>/<script> tags in
// lockstep.
const CACHE_NAME = '__CREWLOG_CACHE_NAME__';

// CSS and JS files are intentionally excluded from precaching: the page
// templates request them with a `?v=<asset_version>` cache-buster, so the
// unversioned URLs we used to precache here were never actually served to
// the page. The runtime handlers below populate the cache with the
// versioned URLs the templates actually request, and CACHE_NAME rotates
// in lockstep with `asset_version()` so a CSS- or JS-only deploy wipes
// stale entries automatically.
const STATIC_ASSETS = [
  '/static/manifest.json',
  '/static/logo-crewlog.svg',
  '/static/logo-crewlog-192.png',
  '/static/logo-crewlog-512.png',
  '/offline'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== 'GET') {
    return;
  }

  if (url.pathname.startsWith('/static/')) {
    // CSS uses network-first so theme changes propagate on a single
    // reload — old cached red-on-blue CSS stuck around for too long
    // before. Other assets (images, JS, fonts) keep cache-first.
    if (url.pathname.endsWith('.css')) {
      event.respondWith(networkFirstStatic(request));
    } else {
      event.respondWith(cacheFirst(request));
    }
    return;
  }

  if (request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(networkFirstHTML(request));
    return;
  }

  event.respondWith(fetch(request));
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('', { status: 503 });
  }
}

async function networkFirstHTML(request) {
  try {
    const response = await fetch(request);
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return caches.match('/offline');
  }
}

async function networkFirstStatic(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response('', { status: 503 });
  }
}
