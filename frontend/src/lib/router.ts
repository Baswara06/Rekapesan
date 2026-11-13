import { useEffect, useState } from "react";

// Router hash kecil. Cukup untuk 9 layar dan bekerja di hosting statis apa pun tanpa aturan rewrite.
export interface Rute {
  path: string; // mis. "/pesanan/abc"
  segmen: string[]; // ["pesanan", "abc"]
  query: URLSearchParams;
}

export function bacaRute(hash = window.location.hash): Rute {
  const mentah = hash.replace(/^#/, "") || "/";
  const [path, q = ""] = mentah.split("?");
  const bersih = path.startsWith("/") ? path : `/${path}`;
  return { path: bersih, segmen: bersih.split("/").filter(Boolean), query: new URLSearchParams(q) };
}

export function pergi(path: string): void {
  window.location.hash = path;
}

export function useRute(): Rute {
  const [rute, setRute] = useState(() => bacaRute());
  useEffect(() => {
    const ubah = () => {
      setRute(bacaRute());
      window.scrollTo({ top: 0 });
    };
    window.addEventListener("hashchange", ubah);
    return () => window.removeEventListener("hashchange", ubah);
  }, []);
  return rute;
}
