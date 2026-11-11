// The website's service worker: the page and its bundles, so the app opens at once and its shell works offline, and
// the map when the visitor saved it for offline use (src/offline.ts fills MAP from offline.json; nothing else writes
// to it, so its meta.json always matches its tiles). Without a saved map, data/ goes to the network as before.
const CACHE = 'voxelpest-shell-v2';
const MAP = 'voxelpest-map';  // src/offline.ts's MAP
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(
  caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE && k !== MAP).map((k) => caches.delete(k)))).then(() => self.clients.claim())));

const fromMap = (req, opts) => caches.open(MAP).then((c) => c.match(req, opts));

function data(req, url) {
  // tiles: their URLs carry the map's hash (?v=), so a saved one is the one asked for; a tile the map doesn't have is a
  // 404 online, and offline too once a map is saved (an empty tile, mesher.worker.ts), rather than an error
  if (url.pathname.includes('/data/tiles/')) {
    return fromMap(req).then((hit) => hit || fetch(req).catch(() =>
      caches.open(MAP).then((c) => c.match('data/offline-done.json')).then((done) => {
        if (done) return new Response(null, { status: 404 });
        throw new TypeError('offline');
      })));
  }
  // meta.json, foliage.bin, the climate and phenology tables: the network first (a new map), the saved ones offline
  const saved = () => fromMap(req, { ignoreSearch: true }).then((hit) => hit || Response.error());
  if (!navigator.onLine) return saved();
  return fetch(req).catch(saved);
}

self.addEventListener('fetch', (e) => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin) return;
  if (url.pathname.includes('/data/')) { e.respondWith(data(req, url)); return; }
  const keep = (res) => { if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); } return res; };
  const anyCache = (r, opts) => caches.match(r, opts);  // the shell's, or the saved map's copy of the shell
  // hashed bundles never change: the cache first; the page and the rest: the network first, the cache when offline
  if (url.pathname.includes('/assets/')) e.respondWith(anyCache(req).then((hit) => hit || fetch(req).then(keep)));
  else e.respondWith(fetch(req).then(keep).catch(() => anyCache(req, { ignoreSearch: req.mode === 'navigate' })
    .then((hit) => hit || Response.error())));
});
