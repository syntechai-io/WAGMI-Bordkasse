const CACHE_VERSION = 'v2';
const STATIC_CACHE = `crew-wallet-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `crew-wallet-dynamic-${CACHE_VERSION}`;
const API_CACHE = `crew-wallet-api-${CACHE_VERSION}`;
const DB_NAME = 'CrewWalletDB';
const DB_VERSION = 3;
const SYNC_TAG = 'sync-crew-wallet';

const STATIC_ASSETS = [
  '/',
  '/static/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/static/logo.jpeg',
  'https://cdn.tailwindcss.com',
  'https://unpkg.com/htmx.org@1.9.10',
  'https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600;700&display=swap'
];

const PAGES_TO_CACHE = [
  '/offline',
  '/login',
  '/trips',
  '/crew',
  '/deposits',
  '/expenses',
  '/balances',
  '/settlement',
  '/help'
];

let db;

function openDB() {
  return new Promise((resolve, reject) => {
    if (db) {
      resolve(db);
      return;
    }

    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      db = request.result;
      resolve(db);
    };

    request.onupgradeneeded = (event) => {
      const database = event.target.result;
      const oldVersion = event.oldVersion;

      if (!database.objectStoreNames.contains('pendingRequests')) {
        const store = database.createObjectStore('pendingRequests', { 
          keyPath: 'id', 
          autoIncrement: true 
        });
        store.createIndex('timestamp', 'timestamp', { unique: false });
        store.createIndex('synced', 'synced', { unique: false });
      }

      if (!database.objectStoreNames.contains('offlineData')) {
        const dataStore = database.createObjectStore('offlineData', { 
          keyPath: 'key' 
        });
      }

      if (oldVersion < 2) {
        if (!database.objectStoreNames.contains('logbookEntries')) {
          const logbookStore = database.createObjectStore('logbookEntries', { 
            keyPath: 'id' 
          });
          logbookStore.createIndex('tripId', 'tripId', { unique: false });
          logbookStore.createIndex('syncStatus', 'syncStatus', { unique: false });
          logbookStore.createIndex('clientTempId', 'clientTempId', { unique: false });
        }

        if (!database.objectStoreNames.contains('expenses')) {
          const expensesStore = database.createObjectStore('expenses', { 
            keyPath: 'id' 
          });
          expensesStore.createIndex('tripId', 'tripId', { unique: false });
          expensesStore.createIndex('syncStatus', 'syncStatus', { unique: false });
          expensesStore.createIndex('clientTempId', 'clientTempId', { unique: false });
        }

        if (!database.objectStoreNames.contains('deposits')) {
          const depositsStore = database.createObjectStore('deposits', { 
            keyPath: 'id' 
          });
          depositsStore.createIndex('tripId', 'tripId', { unique: false });
          depositsStore.createIndex('syncStatus', 'syncStatus', { unique: false });
          depositsStore.createIndex('clientTempId', 'clientTempId', { unique: false });
        }

        if (!database.objectStoreNames.contains('crewMembers')) {
          const crewStore = database.createObjectStore('crewMembers', { 
            keyPath: 'id' 
          });
          crewStore.createIndex('tripId', 'tripId', { unique: false });
        }

        if (!database.objectStoreNames.contains('pendingPhotos')) {
          const photosStore = database.createObjectStore('pendingPhotos', { 
            keyPath: 'id', 
            autoIncrement: true 
          });
          photosStore.createIndex('entryId', 'entryId', { unique: false });
          photosStore.createIndex('entityType', 'entityType', { unique: false });
          photosStore.createIndex('synced', 'synced', { unique: false });
        }
      }

      if (oldVersion < 3) {
        if (database.objectStoreNames.contains('logbookEntries')) {
          database.deleteObjectStore('logbookEntries');
        }
        if (database.objectStoreNames.contains('expenses')) {
          database.deleteObjectStore('expenses');
        }
        if (database.objectStoreNames.contains('deposits')) {
          database.deleteObjectStore('deposits');
        }

        const logbookStore = database.createObjectStore('logbookEntries', { 
          keyPath: 'id' 
        });
        logbookStore.createIndex('tripId', 'tripId', { unique: false });
        logbookStore.createIndex('syncStatus', 'syncStatus', { unique: false });
        logbookStore.createIndex('clientTempId', 'clientTempId', { unique: false });

        const expensesStore = database.createObjectStore('expenses', { 
          keyPath: 'id' 
        });
        expensesStore.createIndex('tripId', 'tripId', { unique: false });
        expensesStore.createIndex('syncStatus', 'syncStatus', { unique: false });
        expensesStore.createIndex('clientTempId', 'clientTempId', { unique: false });

        const depositsStore = database.createObjectStore('deposits', { 
          keyPath: 'id' 
        });
        depositsStore.createIndex('tripId', 'tripId', { unique: false });
        depositsStore.createIndex('syncStatus', 'syncStatus', { unique: false });
        depositsStore.createIndex('clientTempId', 'clientTempId', { unique: false });
      }
    };
  });
}

async function queueRequest(request, body = null) {
  const database = await openDB();
  const tx = database.transaction(['pendingRequests'], 'readwrite');
  const store = tx.objectStore('pendingRequests');

  const requestData = {
    url: request.url,
    method: request.method,
    headers: [...request.headers.entries()],
    body: body,
    timestamp: Date.now(),
    synced: false
  };

  await store.add(requestData);
  
  if ('sync' in self.registration) {
    await self.registration.sync.register(SYNC_TAG);
  }
}

async function getPendingRequests() {
  const database = await openDB();
  const tx = database.transaction(['pendingRequests'], 'readonly');
  const store = tx.objectStore('pendingRequests');
  const index = store.index('synced');
  
  return new Promise((resolve, reject) => {
    const request = index.getAll(false);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function markRequestSynced(id) {
  const database = await openDB();
  const tx = database.transaction(['pendingRequests'], 'readwrite');
  const store = tx.objectStore('pendingRequests');
  
  const request = await store.get(id);
  if (request) {
    request.synced = true;
    await store.put(request);
  }
}

async function deleteSyncedRequests() {
  const database = await openDB();
  const tx = database.transaction(['pendingRequests'], 'readwrite');
  const store = tx.objectStore('pendingRequests');
  const index = store.index('synced');
  
  const syncedRequests = await new Promise((resolve, reject) => {
    const request = index.getAll(true);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });

  for (const req of syncedRequests) {
    await store.delete(req.id);
  }
}

async function saveToCache(storeName, data) {
  const database = await openDB();
  const tx = database.transaction([storeName], 'readwrite');
  const store = tx.objectStore(storeName);
  
  if (Array.isArray(data)) {
    for (const item of data) {
      await store.put(item);
    }
  } else {
    await store.put(data);
  }
  
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function getFromCache(storeName, key = null) {
  const database = await openDB();
  const tx = database.transaction([storeName], 'readonly');
  const store = tx.objectStore(storeName);
  
  return new Promise((resolve, reject) => {
    const request = key ? store.get(key) : store.getAll();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function getCachedByIndex(storeName, indexName, value) {
  const database = await openDB();
  const tx = database.transaction([storeName], 'readonly');
  const store = tx.objectStore(storeName);
  const index = store.index(indexName);
  
  return new Promise((resolve, reject) => {
    const request = index.getAll(value);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function deleteFromCache(storeName, key) {
  const database = await openDB();
  const tx = database.transaction([storeName], 'readwrite');
  const store = tx.objectStore(storeName);
  
  return new Promise((resolve, reject) => {
    const request = store.delete(key);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

async function clearCache(storeName) {
  const database = await openDB();
  const tx = database.transaction([storeName], 'readwrite');
  const store = tx.objectStore(storeName);
  
  return new Promise((resolve, reject) => {
    const request = store.clear();
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    Promise.all([
      caches.open(STATIC_CACHE).then((cache) => {
        return cache.addAll(STATIC_ASSETS.concat(PAGES_TO_CACHE)).catch(err => {
          console.warn('Some assets failed to cache during install:', err);
        });
      }),
      openDB()
    ]).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    Promise.all([
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName.startsWith('crew-wallet-') && 
                cacheName !== STATIC_CACHE && 
                cacheName !== DYNAMIC_CACHE && 
                cacheName !== API_CACHE) {
              console.log('Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      }),
      deleteSyncedRequests(),
      self.clients.claim()
    ])
  );
});

function isStaticAsset(url) {
  return url.includes('/static/') || 
         url.includes('tailwindcss.com') || 
         url.includes('unpkg.com') ||
         url.includes('googleapis.com') ||
         url.includes('gstatic.com') ||
         url.match(/\.(png|jpg|jpeg|svg|gif|woff|woff2|ttf|eot|css|js)$/);
}

function isAPIRequest(url) {
  return url.includes('/api/') || 
         (url.includes('/crew') || 
          url.includes('/deposits') || 
          url.includes('/expenses') || 
          url.includes('/trips')) && 
         !url.includes('.html');
}

function isNavigationRequest(request) {
  return request.mode === 'navigate' || 
         (request.method === 'GET' && request.headers.get('accept')?.includes('text/html'));
}

async function cacheFirstStrategy(request) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    if (networkResponse && networkResponse.status === 200) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.error('Cache-first strategy failed:', error);
    throw error;
  }
}

async function networkFirstStrategy(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse && networkResponse.status === 200) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    if (isNavigationRequest(request)) {
      const offlineResponse = await caches.match('/offline');
      if (offlineResponse) {
        return offlineResponse;
      }
    }
    
    throw error;
  }
}

async function handleAPIRequest(request) {
  if (request.method === 'GET') {
    try {
      const networkResponse = await fetch(request);
      if (networkResponse && networkResponse.status === 200) {
        const cache = await caches.open(API_CACHE);
        cache.put(request, networkResponse.clone());
      }
      return networkResponse;
    } catch (error) {
      const cachedResponse = await caches.match(request);
      if (cachedResponse) {
        return cachedResponse;
      }
      return new Response(JSON.stringify({ error: 'Offline - data may be outdated' }), {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }

  if (request.method === 'POST' || request.method === 'PUT' || request.method === 'DELETE') {
    try {
      const response = await fetch(request);
      broadcastOnlineStatus(true);
      return response;
    } catch (error) {
      const clonedRequest = request.clone();
      const body = await clonedRequest.text();
      
      await queueRequest(request, body);
      broadcastOnlineStatus(false);
      
      return new Response(JSON.stringify({ 
        queued: true, 
        message: 'Request queued for sync when online' 
      }), {
        status: 202,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }

  return fetch(request);
}

function broadcastOnlineStatus(isOnline) {
  self.clients.matchAll().then(clients => {
    clients.forEach(client => {
      client.postMessage({
        type: 'ONLINE_STATUS',
        isOnline: isOnline,
        timestamp: Date.now()
      });
    });
  });
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (url.origin !== location.origin && !isStaticAsset(url.href)) {
    return;
  }

  if (isStaticAsset(url.href)) {
    event.respondWith(cacheFirstStrategy(request));
  } else if (isAPIRequest(url.href)) {
    event.respondWith(handleAPIRequest(request));
  } else {
    event.respondWith(networkFirstStrategy(request));
  }
});

// Helper: Convert base64 to Blob
function base64ToBlob(base64, mimeType) {
  const byteCharacters = atob(base64.split(',')[1]);
  const byteArrays = [];

  for (let offset = 0; offset < byteCharacters.length; offset += 512) {
    const slice = byteCharacters.slice(offset, offset + 512);
    const byteNumbers = new Array(slice.length);
    for (let i = 0; i < slice.length; i++) {
      byteNumbers[i] = slice.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    byteArrays.push(byteArray);
  }

  return new Blob(byteArrays, { type: mimeType });
}

async function syncPendingRequests() {
  const pendingRequests = await getPendingRequests();
  const results = [];

  for (const reqData of pendingRequests) {
    try {
      const headers = new Headers();
      reqData.headers.forEach(([key, value]) => {
        headers.append(key, value);
      });

      let requestBody = reqData.body;
      
      // Check if this is an expense with a receipt attachment
      if (reqData.url.includes('/expenses/new') && reqData.body) {
        try {
          const bodyData = JSON.parse(reqData.body);
          
          // If receipt base64 data exists, convert to FormData
          if (bodyData.receipt && bodyData.receipt.base64) {
            const formData = new FormData();
            
            // Add all expense fields
            formData.append('payer_id', bodyData.payer_id);
            formData.append('expense_date', bodyData.date);
            formData.append('category', bodyData.category);
            formData.append('description', bodyData.description);
            formData.append('amount', bodyData.amount);
            formData.append('currency', bodyData.currency);
            formData.append('paid_from', bodyData.paid_from);
            formData.append('split_mode', bodyData.split_mode);
            
            if (bodyData.participant_ids) {
              bodyData.participant_ids.forEach(id => {
                formData.append('participant_ids', id);
              });
            }
            
            if (bodyData.participant_percentages) {
              bodyData.participant_percentages.forEach(p => {
                formData.append('participant_percentages', p);
              });
            }
            
            if (bodyData.clientTempId) {
              formData.append('clientTempId', bodyData.clientTempId);
            }
            
            // Convert base64 to Blob and add as file
            const blob = base64ToBlob(bodyData.receipt.base64, bodyData.receipt.type);
            formData.append('receipt', blob, bodyData.receipt.name);
            
            requestBody = formData;
            
            // Remove Content-Type header to let browser set it with boundary for multipart
            headers.delete('Content-Type');
          }
        } catch (e) {
          console.warn('Failed to parse expense body for receipt:', e);
        }
      }

      const response = await fetch(reqData.url, {
        method: reqData.method,
        headers: headers,
        body: requestBody
      });

      if (response.ok) {
        await markRequestSynced(reqData.id);
        results.push({ success: true, url: reqData.url });
      } else {
        results.push({ success: false, url: reqData.url, status: response.status });
      }
    } catch (error) {
      console.error('Sync failed for request:', reqData.url, error);
      results.push({ success: false, url: reqData.url, error: error.message });
    }
  }

  await deleteSyncedRequests();
  
  return results;
}

self.addEventListener('sync', (event) => {
  if (event.tag === SYNC_TAG) {
    event.waitUntil(
      syncPendingRequests()
        .then((results) => {
          const successCount = results.filter(r => r.success).length;
          const failCount = results.filter(r => !r.success).length;
          
          broadcastOnlineStatus(true);
          
          self.clients.matchAll().then(clients => {
            clients.forEach(client => {
              client.postMessage({
                type: 'SYNC_COMPLETE',
                success: successCount,
                failed: failCount,
                timestamp: Date.now()
              });
            });
          });

          if ('Notification' in self && successCount > 0) {
            self.registration.showNotification('Crew Wallet', {
              body: `${successCount} Aktionen erfolgreich synchronisiert`,
              icon: '/static/icon-192.png',
              badge: '/static/icon-192.png'
            });
          }
        })
        .catch((error) => {
          console.error('Background sync failed:', error);
        })
    );
  }
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CHECK_ONLINE_STATUS') {
    fetch('/').then(() => {
      broadcastOnlineStatus(true);
    }).catch(() => {
      broadcastOnlineStatus(false);
    });
  }

  if (event.data && event.data.type === 'CACHE_DATA') {
    const { storeName, data, timestamp } = event.data;
    
    if (Array.isArray(data)) {
      const enrichedData = data.map(item => ({
        ...item,
        syncStatus: 'synced',
        cachedAt: timestamp || Date.now()
      }));
      saveToCache(storeName, enrichedData).catch(err => {
        console.error(`Failed to cache ${storeName}:`, err);
      });
    } else if (data) {
      const enrichedData = {
        ...data,
        syncStatus: 'synced',
        cachedAt: timestamp || Date.now()
      };
      saveToCache(storeName, enrichedData).catch(err => {
        console.error(`Failed to cache ${storeName}:`, err);
      });
    }
    
    event.ports[0]?.postMessage({ success: true });
  }

  if (event.data && event.data.type === 'GET_CACHED_DATA') {
    const { storeName, key } = event.data;
    
    getFromCache(storeName, key)
      .then(data => {
        event.ports[0]?.postMessage({ success: true, data });
      })
      .catch(err => {
        event.ports[0]?.postMessage({ success: false, error: err.message });
      });
  }

  if (event.data && event.data.type === 'CREATE_OFFLINE_ENTRY') {
    const { storeName, entry } = event.data;
    
    // Generate temp ID for offline entry
    const clientTempId = `offline_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const offlineEntry = {
      ...entry,
      id: clientTempId,  // Set id = clientTempId for IndexedDB keyPath
      clientTempId,
      syncStatus: 'pending',
      createdAt: Date.now(),
      cachedAt: Date.now()
    };
    
    // Save to IndexedDB
    saveToCache(storeName, offlineEntry)
      .then(() => {
        // Create a mock request for queueRequest
        const mockRequest = new Request(entry.endpoint || `/${storeName}/new`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        
        // Add to pending requests for sync using queueRequest
        return queueRequest(mockRequest, JSON.stringify(offlineEntry));
      })
      .then(() => {
        event.ports[0]?.postMessage({ 
          success: true, 
          entry: offlineEntry,
          clientTempId 
        });
      })
      .catch(err => {
        console.error('Failed to create offline entry:', err);
        event.ports[0]?.postMessage({ 
          success: false, 
          error: err.message 
        });
      });
  }

  if (event.data && event.data.type === 'GET_PENDING_COUNT') {
    getPendingRequests()
      .then(requests => {
        event.ports[0]?.postMessage({ 
          success: true, 
          count: requests.length 
        });
      })
      .catch(err => {
        event.ports[0]?.postMessage({ 
          success: false, 
          error: err.message 
        });
      });
  }
});

self.addEventListener('online', () => {
  broadcastOnlineStatus(true);
  if ('sync' in self.registration) {
    self.registration.sync.register(SYNC_TAG).catch(err => {
      console.error('Failed to register sync:', err);
    });
  }
});

self.addEventListener('offline', () => {
  broadcastOnlineStatus(false);
});
