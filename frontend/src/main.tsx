import "@fontsource-variable/plus-jakarta-sans";
import "@fontsource-variable/fraunces";
import "./styles.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { AppProvider } from "./lib/store";

// Kilau kaca: satu pendengar untuk seluruh halaman, posisi jari/kursor ditulis ke variabel CSS kartu
// yang sedang disentuh. Dimatikan bila pengguna memilih kurangi gerakan.
if (!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
  let terakhir: HTMLElement | null = null;
  document.addEventListener(
    "pointermove",
    (e) => {
      const el = (e.target as HTMLElement | null)?.closest?.(".kaca") as HTMLElement | null;
      if (terakhir && terakhir !== el) terakhir.classList.remove("berkilau");
      terakhir = el;
      if (!el) return;
      const r = el.getBoundingClientRect();
      el.style.setProperty("--mx", `${e.clientX - r.left}px`);
      el.style.setProperty("--my", `${e.clientY - r.top}px`);
      el.classList.add("berkilau");
    },
    { passive: true },
  );
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* tanpa service worker aplikasi tetap jalan, hanya tidak bisa dipasang/menerima bagikan */
    });
  });
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppProvider>
      <App />
    </AppProvider>
  </StrictMode>,
);
