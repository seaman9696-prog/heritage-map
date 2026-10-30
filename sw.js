// 世界遺産マップの Service Worker
// アプリ本体と地図データは最初に保存し、写真のファイルとフォントは一度開いたものを保存する。
// 中身を更新したら VERSION を上げる(古い保存分は消える)。
const VERSION = 'v1';
const CORE = [
  './', 'index.html', 'manifest.webmanifest', 'heritage_map.json', 'world-50m.json', 'photos/index.json',
  'vendor/leaflet.js', 'vendor/leaflet.markercluster.js', 'vendor/topojson-client.min.js',
  'icons/icon.svg', 'icons/icon-192.png', 'icons/apple-touch-icon.png',
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  const sameOrigin = url.origin === location.origin;
  const font = url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com';
  if (!sameOrigin && !font) return;
  // ページとデータはネットを優先(更新をすぐ反映)、つながらなければ保存分。写真・フォントは保存分を優先
  const cacheFirst = font || url.pathname.includes('/photos/p') || url.pathname.includes('/vendor/');
  e.respondWith(cacheFirst ? fromCache(e.request) : fromNetwork(e.request));
});

async function fromCache(req) {
  const hit = await caches.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok || res.type === 'opaque') (await caches.open(VERSION)).put(req, res.clone());
  return res;
}

async function fromNetwork(req) {
  try {
    const res = await fetch(req);
    if (res.ok) (await caches.open(VERSION)).put(req, res.clone());
    return res;
  } catch (err) {
    const hit = await caches.match(req, { ignoreSearch: true });
    if (hit) return hit;
    throw err;
  }
}
