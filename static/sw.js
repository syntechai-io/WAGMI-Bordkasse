const CACHE_NAME = 'crewlog-v10';

const STATIC_ASSETS = [
  '/static/ui_v1.css',
  '/static/ui_desktop_skin.css',
  '/static/ui_navy_contrast_fix.css',
  '/static/ui_nav.js',
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
    event.respondWith(cacheFirst(request));
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
