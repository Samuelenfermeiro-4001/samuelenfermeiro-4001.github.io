// PWA do Samuel 4001.
// Suba a versão do cache sempre que publicar uma alteração nos arquivos.
const CACHE = 'samuel4001-v7';

const PRECACHE = [
  './',
  './index.html',
  './styles.css',
  './app.js',
  './config.js',
  './manifest.webmanifest',
  './assets/samuel-4001.jpg',
  './assets/icon-192.png',
  './assets/icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;

  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Supabase, CDN e qualquer outro domínio passam direto pela rede.
  if (url.origin !== self.location.origin) return;

  // Painel administrativo nunca é servido do cache.
  if (url.pathname.includes('admin')) return;

  // HTML e config.js: rede primeiro, cache como reserva (offline).
  const networkFirst = request.mode === 'navigate' || url.pathname.endsWith('config.js');

  if (networkFirst) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request).then((cached) => cached || caches.match('./index.html')))
    );
    return;
  }

  // Arte, CSS, JS e ícones: cache primeiro (abertura instantânea pelo WhatsApp).
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(request, copy));
        return response;
      });
    })
  );
});
