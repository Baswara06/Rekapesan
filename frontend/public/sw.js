// Service worker Rekapesan.
// 1. Share target: menerima ekspor chat yang dibagikan dari WhatsApp (Android), menyimpannya
//    sementara di cache, lalu membuka layar Impor. Berkas tidak dikirim ke mana pun sebelum
//    penjual memilih PO dan menekan Impor.
// 2. Cadangan offline untuk kerangka aplikasi (network-first). Permintaan /api tidak pernah di-cache,
//    supaya data pesanan selalu dari server dan tidak tertinggal di perangkat.
const CACHE_APP = "rekapesan-app-v1";
const CACHE_BAGIKAN = "rekapesan-bagikan";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_APP)
      .then((c) => c.addAll(["/", "/manifest.webmanifest", "/icons/icon.svg"]))
      .catch(() => undefined)
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((kunci) => Promise.all(kunci.filter((k) => k !== CACHE_APP && k !== CACHE_BAGIKAN).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

async function terimaBagikan(request) {
  try {
    const form = await request.formData();
    const berkas = form.get("file");
    const teks = [form.get("title"), form.get("text")].filter((x) => typeof x === "string" && x).join("\n");
    const cache = await caches.open(CACHE_BAGIKAN);
    if (berkas && typeof berkas !== "string") {
      await cache.put(
        "/bagikan/berkas",
        new Response(berkas, {
          headers: { "Content-Type": berkas.type || "application/octet-stream", "X-Nama-Berkas": encodeURIComponent(berkas.name || "chat.txt") },
        }),
      );
    } else if (teks) {
      await cache.put("/bagikan/teks", new Response(teks, { headers: { "Content-Type": "text/plain; charset=utf-8" } }));
    }
  } catch {
    /* tetap buka layar impor, pengguna bisa tempel teks manual */
  }
  return Response.redirect("/#/impor?bagikan=1", 303);
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  if (req.method === "POST" && url.pathname === "/bagikan") {
    event.respondWith(terimaBagikan(req));
    return;
  }
  if (req.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api")) return;

  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok && (req.mode === "navigate" || /\.(js|css|woff2?|svg|png|webmanifest)$/.test(url.pathname))) {
          const salinan = res.clone();
          caches.open(CACHE_APP).then((c) => c.put(req.mode === "navigate" ? "/" : req, salinan));
        }
        return res;
      })
      .catch(async () => (await caches.match(req.mode === "navigate" ? "/" : req)) ?? Response.error()),
  );
});
