import { useEffect, useRef, useState } from "react";
import { Icon, type NamaIkon } from "./components/Icon";
import { TandaLogo, TeksLogo } from "./components/Logo";
import { Toasts } from "./components/ui";
import { api } from "./lib/api";
import { useRute } from "./lib/router";
import { useApp } from "./lib/store";
import Beranda from "./pages/Beranda";
import Detail from "./pages/Detail";
import Impor from "./pages/Impor";
import Katalog from "./pages/Katalog";
import Lainnya from "./pages/Lainnya";
import Login from "./pages/Login";
import Pengaturan from "./pages/Pengaturan";
import Rekap from "./pages/Rekap";
import Review from "./pages/Review";
import Tanya from "./pages/Tanya";

const NAV: { path: string; label: string; ikon: NamaIkon; cocok: string[] }[] = [
  { path: "/", label: "Beranda", ikon: "beranda", cocok: [""] },
  { path: "/impor", label: "Impor", ikon: "impor", cocok: ["impor"] },
  { path: "/cek", label: "Cek", ikon: "cek", cocok: ["cek", "pesanan"] },
  { path: "/rekap", label: "Rekap", ikon: "rekap", cocok: ["rekap"] },
  // Tanya AI jadi tab sendiri supaya fitur AI terlihat di HP. Katalog dan Pengaturan lewat ikon gerigi di bilah atas.
  { path: "/tanya", label: "Tanya AI", ikon: "tanya", cocok: ["tanya"] },
];

/** Navigasi bilah atas di layar lebar: semua layar utama terlihat tanpa menu "Lainnya". */
const NAV_ATAS: { path: string; label: string; cocok: string[] }[] = [
  { path: "/", label: "Beranda", cocok: [""] },
  { path: "/impor", label: "Impor", cocok: ["impor"] },
  { path: "/cek", label: "Cek pesanan", cocok: ["cek", "pesanan"] },
  { path: "/rekap", label: "Rekap", cocok: ["rekap"] },
  { path: "/tanya", label: "Tanya AI", cocok: ["tanya"] },
  { path: "/katalog", label: "Katalog", cocok: ["katalog"] },
];

const JUDUL_LAYAR: Record<string, string> = {
  "": "Beranda",
  impor: "Masukkan chat",
  cek: "Cek pesanan",
  pesanan: "Detail pesanan",
  rekap: "Rekap",
  katalog: "Katalog menu",
  tanya: "Tanya pesanan",
  pengaturan: "Pengaturan",
  lainnya: "Lainnya",
};

function useJumlahPerluCek(): number | null {
  const { batchAktif, versiData } = useApp();
  const [n, setN] = useState<number | null>(null);
  useEffect(() => {
    if (!batchAktif) return setN(null);
    let batal = false;
    api
      .daftarPesanan(batchAktif.id, "perlu_cek")
      .then((d) => !batal && setN(d.length))
      .catch(() => !batal && setN(null));
    return () => {
      batal = true;
    };
  }, [batchAktif, versiData]);
  return n;
}

export default function App() {
  const { masuk, batchAktif } = useApp();
  const rute = useRute();
  const perluCek = useJumlahPerluCek();
  const [online, setOnline] = useState(() => navigator.onLine);

  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  // Aksesibilitas pindah layar: judul tab ikut berganti, fokus pindah ke judul layar baru, dan pembaca layar
  // diberi tahu nama layarnya. Tanpa ini pengguna pembaca layar tidak tahu bahwa isi halaman sudah berganti.
  const judulLayar = masuk ? (JUDUL_LAYAR[rute.segmen[0] ?? ""] ?? "Beranda") : "Masuk";
  const pathSebelum = useRef(rute.path);
  const [umumkan, setUmumkan] = useState("");
  useEffect(() => {
    document.title = `${judulLayar} · RekaPesan`;
    // Hanya saat benar-benar pindah layar. Saat muat pertama fokus dibiarkan di awal dokumen.
    if (pathSebelum.current === rute.path) return;
    pathSebelum.current = rute.path;
    setUmumkan(`Layar ${judulLayar}`);
    const id = requestAnimationFrame(() => {
      const tujuan = document.querySelector<HTMLElement>("#isi h1") ?? document.getElementById("isi");
      if (!tujuan) return;
      if (!tujuan.hasAttribute("tabindex")) tujuan.setAttribute("tabindex", "-1");
      tujuan.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(id);
  }, [rute.path, judulLayar]);

  if (!masuk) {
    return (
      <>
        <Login />
        <Toasts />
      </>
    );
  }

  const [s0, s1] = rute.segmen;
  let halaman;
  switch (s0) {
    case undefined:
      halaman = <Beranda perluCek={perluCek} />;
      break;
    case "impor":
      halaman = <Impor rute={rute} />;
      break;
    case "cek":
      halaman = <Review rute={rute} />;
      break;
    case "pesanan":
      halaman = <Detail id={s1 ?? ""} />;
      break;
    case "rekap":
      halaman = <Rekap />;
      break;
    case "katalog":
      halaman = <Katalog />;
      break;
    case "tanya":
      halaman = <Tanya />;
      break;
    case "pengaturan":
      halaman = <Pengaturan />;
      break;
    case "lainnya":
      halaman = <Lainnya />;
      break;
    default:
      halaman = <Beranda perluCek={perluCek} />;
  }


  return (
    <>
      <a href="#isi" className="lewati">
        Lompat ke isi
      </a>
      {!online && (
        <div className="pita-offline" role="status">
          <Icon nama="info" ukuran={16} /> Sedang offline. Data terakhir tetap bisa dilihat, perubahan menunggu internet.
        </div>
      )}
      <header className="bilah-atas-wrap">
        <div className="bilah-atas">
          <a href="#/" className="merek" aria-label="RekaPesan, ke beranda">
            <TandaLogo ukuran={30} />
            <TeksLogo />
          </a>
          <nav className="nav-atas" aria-label="Menu utama">
            {NAV_ATAS.map((n) => {
              const aktif = n.cocok.includes(s0 ?? "");
              return (
                <a key={n.path} href={`#${n.path}`} className={aktif ? "aktif" : ""} aria-current={aktif ? "page" : undefined}>
                  {n.label}
                  {n.path === "/cek" && perluCek ? <span className="hitung">{perluCek > 99 ? "99+" : perluCek}</span> : null}
                </a>
              );
            })}
          </nav>
          <div className="bilah-kanan">
            {batchAktif && (
              <a href="#/" className="chip-po" title={`PO aktif: ${batchAktif.nama}`}>
                <Icon nama="kalender" ukuran={15} />
                <span>{batchAktif.nama}</span>
              </a>
            )}
            <a
              href="#/lainnya"
              className="tombol tombol-hantu tombol-ikon"
              aria-label="Lainnya: katalog dan pengaturan"
              title="Katalog dan pengaturan"
              aria-current={s0 === "lainnya" ? "page" : undefined}
            >
              <Icon nama="pengaturan" ukuran={19} />
            </a>
          </div>
        </div>
      </header>
      <main id="isi" className="isi" tabIndex={-1}>
        <div key={rute.path} className="masuk-halaman">
          {halaman}
        </div>
      </main>
      <nav className="nav-bawah" aria-label="Menu utama (bawah)">
        {NAV.map((n) => {
          const aktif = n.cocok.includes(s0 ?? "");
          return (
            <a key={n.path} href={`#${n.path}`} className={`nav-item ${aktif ? "aktif" : ""}`} aria-current={aktif ? "page" : undefined}>
              <span className="nav-ikon">
                <Icon nama={n.ikon} ukuran={21} />
                {n.path === "/cek" && perluCek ? (
                  <span className="nav-lencana" aria-label={`${perluCek} pesanan perlu dicek`}>
                    {perluCek > 99 ? "99+" : perluCek}
                  </span>
                ) : null}
              </span>
              <span className="nav-label">{n.label}</span>
            </a>
          );
        })}
      </nav>
      <Toasts />
      <p className="sr" role="status" aria-live="polite">
        {umumkan}
      </p>
    </>
  );
}
