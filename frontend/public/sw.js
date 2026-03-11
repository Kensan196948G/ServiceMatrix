/**
 * ServiceMatrix Service Worker
 *
 * 戦略:
 *   - App Shell: Cache First（高速起動）
 *   - API レスポンス: Network First（最新データ優先）
 *   - Push 通知: バックグラウンド受信 → 表示
 *   - Background Sync: オフライン中の操作をキューに保持
 */

const CACHE_VERSION = "v1";
const APP_SHELL_CACHE = `servicematrix-shell-${CACHE_VERSION}`;
const API_CACHE = `servicematrix-api-${CACHE_VERSION}`;

/** App Shell としてキャッシュする静的リソース */
const APP_SHELL_URLS = [
  "/",
  "/incidents",
  "/changes",
  "/dashboard",
  "/manifest.json",
];

// ── インストール ───────────────────────────────────────────────────────────────

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(APP_SHELL_CACHE)
      .then((cache) => cache.addAll(APP_SHELL_URLS))
      .then(() => self.skipWaiting())
  );
});

// ── アクティベート ────────────────────────────────────────────────────────────

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter(
              (key) => key !== APP_SHELL_CACHE && key !== API_CACHE
            )
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

// ── フェッチ戦略 ──────────────────────────────────────────────────────────────

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API リクエスト: Network First
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(networkFirst(request, API_CACHE));
    return;
  }

  // 静的リソース: Cache First
  if (
    request.destination === "script" ||
    request.destination === "style" ||
    request.destination === "image" ||
    request.destination === "font"
  ) {
    event.respondWith(cacheFirst(request, APP_SHELL_CACHE));
    return;
  }

  // ナビゲーション: Network First with App Shell フォールバック
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match("/").then((r) => r || fetch(request))
      )
    );
    return;
  }
});

async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    return cached || new Response(JSON.stringify({ error: "offline" }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    });
  }
}

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) {
    const cache = await caches.open(cacheName);
    cache.put(request, response.clone());
  }
  return response;
}

// ── Push 通知 ─────────────────────────────────────────────────────────────────

self.addEventListener("push", (event) => {
  let data = { title: "ServiceMatrix", body: "新着通知があります" };
  if (event.data) {
    try {
      data = event.data.json();
    } catch {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body,
    icon: "/icons/icon-192x192.png",
    badge: "/icons/icon-72x72.png",
    vibrate: [200, 100, 200],
    data: { url: data.url || "/" },
    actions: [
      { action: "open", title: "開く" },
      { action: "close", title: "閉じる" },
    ],
  };

  event.waitUntil(
    self.registration.showNotification(data.title || "ServiceMatrix", options)
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  if (event.action === "close") return;

  const targetUrl = event.notification.data?.url || "/";

  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clients) => {
        const existing = clients.find((c) => c.url === targetUrl);
        if (existing) return existing.focus();
        return self.clients.openWindow(targetUrl);
      })
  );
});

// ── Background Sync ───────────────────────────────────────────────────────────

self.addEventListener("sync", (event) => {
  if (event.tag === "sync-incidents") {
    event.waitUntil(syncPendingIncidents());
  }
});

async function syncPendingIncidents() {
  // IndexedDB の保留操作をサーバーに送信する処理
  // 実装はフロントエンドの IndexedDB ヘルパーと連携
  const clients = await self.clients.matchAll();
  clients.forEach((client) => {
    client.postMessage({ type: "SYNC_COMPLETE", tag: "sync-incidents" });
  });
}
