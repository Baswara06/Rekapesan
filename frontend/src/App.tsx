import { useEffect, useState } from "react";
import { cekKesehatan } from "./lib/api";

export default function App() {
  const [status, setStatus] = useState<"memeriksa" | "ok" | "gagal">("memeriksa");

  useEffect(() => {
    cekKesehatan()
      .then(() => setStatus("ok"))
      .catch(() => setStatus("gagal"));
  }, []);

  return (
    <main style={{ maxWidth: 480, margin: "0 auto", padding: 16, fontFamily: "system-ui, sans-serif" }}>
      <h1>Rekapesan</h1>
      <p>Dari chat grup jadi rekap pesanan, tanpa salin ulang.</p>
      <p role="status">
        Backend: {status === "ok" ? "tersambung" : status === "gagal" ? "tidak tersambung" : "memeriksa..."}
      </p>
    </main>
  );
}
