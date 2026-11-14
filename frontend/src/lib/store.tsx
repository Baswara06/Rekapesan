import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ambilToken, api, ApiError, aturSaatTidakTerautentikasi, simpanToken, type Akun, type Batch, type Product } from "./api";

export type Tema = "otomatis" | "terang" | "gelap";
export type UkuranTeks = "normal" | "besar" | "sangat_besar";

interface Toast {
  id: number;
  teks: string;
  jenis: "sukses" | "galat" | "info";
}

interface AppState {
  masuk: boolean;
  login: (u: string, p: string) => Promise<void>;
  daftar: (u: string, p: string, namaToko: string) => Promise<void>;
  keluar: () => void;

  /** Akun dari GET /auth/me. null bila belum dimuat atau server belum mendukung endpoint itu. */
  akun: Akun | null;
  setAkun: (a: Akun) => void;

  batches: Batch[];
  batchAktif: Batch | null;
  pilihBatch: (id: string) => void;
  muatBatch: () => Promise<void>;
  batchSiap: boolean;

  katalog: Product[];
  /** true setelah katalog pertama kali dimuat (berhasil atau gagal). */
  katalogSiap: boolean;
  katalogMap: Map<string, Product>;
  muatKatalog: () => Promise<void>;

  /** Naik setiap kali data pesanan berubah, supaya layar lain memuat ulang. */
  versiData: number;
  dataBerubah: () => void;

  toast: (teks: string, jenis?: Toast["jenis"]) => void;
  toasts: Toast[];
  tutupToast: (id: number) => void;

  tema: Tema;
  setTema: (t: Tema) => void;
  ukuranTeks: UkuranTeks;
  setUkuranTeks: (u: UkuranTeks) => void;
}

const Ctx = createContext<AppState | null>(null);

function baca<T extends string>(kunci: string, bawaan: T): T {
  try {
    return (localStorage.getItem(kunci) as T | null) ?? bawaan;
  } catch {
    return bawaan;
  }
}

function tulis(kunci: string, nilai: string | null): void {
  try {
    if (nilai === null) localStorage.removeItem(kunci);
    else localStorage.setItem(kunci, nilai);
  } catch {
    /* penyimpanan diblokir: preferensi hanya berlaku di sesi ini */
  }
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [masuk, setMasuk] = useState(() => !!ambilToken());
  const [batches, setBatches] = useState<Batch[]>([]);
  const [batchSiap, setBatchSiap] = useState(false);
  const [idAktif, setIdAktif] = useState<string | null>(() => baca<string>("rekapesan.batch", "") || null);
  const [katalog, setKatalog] = useState<Product[]>([]);
  const [akun, setAkun] = useState<Akun | null>(null);
  const [katalogSiap, setKatalogSiap] = useState(false);
  const [versiData, setVersiData] = useState(0);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [tema, setTemaState] = useState<Tema>(() => baca("rekapesan.tampilan", "terang"));
  const [ukuranTeks, setUkuranTeks] = useState<UkuranTeks>(() => baca("rekapesan.ukuran", "normal"));
  const nomorToast = useRef(0);

  const tutupToast = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), []);
  const toast = useCallback(
    (teks: string, jenis: Toast["jenis"] = "sukses") => {
      const id = ++nomorToast.current;
      setToasts((t) => [...t.slice(-2), { id, teks, jenis }]);
      window.setTimeout(() => tutupToast(id), jenis === "galat" ? 7000 : 4000);
    },
    [tutupToast],
  );

  const keluar = useCallback(() => {
    simpanToken(null);
    setMasuk(false);
    setBatches([]);
    setKatalog([]);
    setAkun(null);
    setBatchSiap(false);
    setKatalogSiap(false);
  }, []);

  useEffect(() => {
    aturSaatTidakTerautentikasi(() => {
      keluar(); // bersihkan data akun sebelumnya, supaya tidak tampil ke akun lain yang masuk di perangkat ini
      toast("Sesi berakhir. Silakan masuk lagi.", "info");
    });
  }, [toast, keluar]);


  const login = useCallback(async (u: string, p: string) => {
    const { token } = await api.login(u, p);
    simpanToken(token);
    setMasuk(true);
  }, []);

  const daftar = useCallback(async (u: string, p: string, namaToko: string) => {
    const { token } = await api.daftar(u, p, namaToko);
    simpanToken(token);
    setMasuk(true);
  }, []);

  const muatBatch = useCallback(async () => {
    try {
      const daftar = await api.daftarBatch();
      setBatches(daftar);
      setIdAktif((lama) => (lama && daftar.some((b) => b.id === lama) ? lama : (daftar[0]?.id ?? null)));
    } catch (e) {
      if (e instanceof ApiError && e.status !== 401) toast(e.message, "galat");
    } finally {
      setBatchSiap(true);
    }
  }, [toast]);

  const muatKatalog = useCallback(async () => {
    try {
      setKatalog(await api.daftarMenu());
    } catch (e) {
      if (e instanceof ApiError && e.status !== 401) toast(e.message, "galat");
    } finally {
      setKatalogSiap(true);
    }
  }, [toast]);

  useEffect(() => {
    if (!masuk) return;
    void muatBatch();
    void muatKatalog();
    // Nama toko hanya pelengkap tampilan: kalau gagal (mis. server lama tanpa /auth/me), aplikasi tetap jalan.
    api
      .akunSaya()
      .then(setAkun)
      .catch(() => setAkun(null));
  }, [masuk, muatBatch, muatKatalog]);

  useEffect(() => tulis("rekapesan.batch", idAktif), [idAktif]);

  // Ukuran huruf: seluruh antarmuka diperbesar lewat CSS (lihat [data-ukuran] di styles.css).
  useEffect(() => {
    tulis("rekapesan.ukuran", ukuranTeks);
    document.documentElement.dataset.ukuran = ukuranTeks;
  }, [ukuranTeks]);

  useEffect(() => {
    tulis("rekapesan.tampilan", tema);
    const root = document.documentElement;
    if (tema !== "otomatis") {
      root.dataset.theme = tema === "gelap" ? "dark" : "light";
      return;
    }
    const mq = window.matchMedia?.("(prefers-color-scheme: dark)");
    const terapkan = () => {
      root.dataset.theme = mq?.matches ? "dark" : "light";
    };
    terapkan();
    mq?.addEventListener?.("change", terapkan);
    return () => mq?.removeEventListener?.("change", terapkan);
  }, [tema]);

  const nilai = useMemo<AppState>(
    () => ({
      masuk,
      login,
      daftar,
      keluar,
      akun,
      setAkun,
      batches,
      batchAktif: batches.find((b) => b.id === idAktif) ?? null,
      pilihBatch: setIdAktif,
      muatBatch,
      batchSiap,
      katalog,
      katalogSiap,
      katalogMap: new Map(katalog.map((p) => [p.id, p])),
      muatKatalog,
      versiData,
      dataBerubah: () => setVersiData((v) => v + 1),
      toast,
      toasts,
      tutupToast,
      tema,
      setTema: setTemaState,
      ukuranTeks,
      setUkuranTeks,
    }),
    [masuk, login, daftar, keluar, akun,
 batches, idAktif, muatBatch, batchSiap, katalog, katalogSiap, muatKatalog, versiData, toast, toasts, tutupToast, tema, ukuranTeks],
  );

  return <Ctx.Provider value={nilai}>{children}</Ctx.Provider>;
}

export function useApp(): AppState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useApp dipakai di luar AppProvider");
  return v;
}

/** Memuat data async dengan status loading/galat dan fungsi muat ulang. */
export function useMuat<T>(fn: (() => Promise<T>) | null, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [galat, setGalat] = useState<ApiError | null>(null);
  const [memuat, setMemuat] = useState(!!fn);
  const [putaran, setPutaran] = useState(0);

  useEffect(() => {
    if (!fn) {
      setMemuat(false);
      return;
    }
    let batal = false;
    setMemuat(true);
    setGalat(null);
    fn()
      .then((d) => !batal && setData(d))
      .catch((e) => !batal && setGalat(e instanceof ApiError ? e : new ApiError(0, "galat", String(e))))
      .finally(() => !batal && setMemuat(false));
    return () => {
      batal = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, putaran]);

  return { data, setData, galat, memuat, muatUlang: () => setPutaran((p) => p + 1) };
}
