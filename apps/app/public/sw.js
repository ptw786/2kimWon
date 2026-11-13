// 안심온 앱 서비스 워커 — 배포용 빌드에서만 등록된다(src/main.tsx).
// 앱 껍데기(HTML·JS·CSS·아이콘)만 저장해 두고, /api 요청은 절대 저장하지 않는다(항상 네트워크).
const CACHE = 'ansimon-app-v2'
const SHELL = ['/', '/index.html', '/manifest.webmanifest', '/icons/icon-192.png', '/icons/icon-512.png', '/icons/apple-touch-icon.png']

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()))
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const req = event.request
  const url = new URL(req.url)
  if (req.method !== 'GET' || url.origin !== self.location.origin) return
  if (url.pathname.startsWith('/api')) return // network-only
  if (req.mode === 'navigate') {
    // 화면 주소(/, /records, /r/KY-01 …)는 새 버전을 먼저 받고, 안 되면 저장해 둔 index.html
    event.respondWith(fetch(req).catch(() => caches.match('/index.html')))
    return
  }
  // 이름에 해시가 붙은 빌드 파일·아이콘: 저장본 먼저, 없으면 받아서 저장
  event.respondWith(
    caches.match(req).then((hit) => hit || fetch(req).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)) }
      return res
    })),
  )
})
