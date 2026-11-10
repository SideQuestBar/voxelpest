// The installed app's service worker: the page and its bundles, so the app opens at once and its shell works offline.
// The map itself (data/: 120 MB of tiles) is never cached here; the browser's own cache keeps what it has seen.
const CACHE = 'voxelpest-shell-v1';
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(
  caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener('fetch', (e) => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin || url.pathname.includes('/data/')) return;
  const keep = (res) => { if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); } return res; };
  // hashed bundles never change: the cache first; the page and the rest: the network first, the cache when offline
  if (url.pathname.includes('/assets/')) e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then(keep)));
  else e.respondWith(fetch(req).then(keep).catch(() => caches.match(req, { ignoreSearch: req.mode === 'navigate' })));
});
