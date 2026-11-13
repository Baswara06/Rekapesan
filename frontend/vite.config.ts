/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Selama pengembangan, permintaan /api diteruskan ke backend FastAPI.
// `fs.allow` membuka folder induk supaya contoh chat di `sample/` bisa dipakai tombol "Pakai contoh chat".
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true, // bisa dibuka dari HP di jaringan yang sama untuk uji mobile
    proxy: { "/api": "http://localhost:8000" },
    fs: { allow: [".."] },
  },
  preview: {
    port: 4173,
    host: true,
    proxy: { "/api": "http://localhost:8000" },
  },
  test: { environment: "jsdom" },
});
