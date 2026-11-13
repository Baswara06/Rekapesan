import { useEffect, useState } from "react";
import { Icon, type NamaIkon } from "./components/Icon";
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
  { path: "/lainnya", label: "Lainnya", ikon: "lainnya", cocok: ["lainnya", "katalog", "tanya", "pengaturan"] },
];

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
  const { masuk } = useApp();
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

  if (!masuk) {
    return (
      <>
        <Latar />
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
      <Latar />
      <a href="#isi" className="lewati">
        Lompat ke isi
      </a>
      {!online && (
        <div className="pita-offline" role="status">
          <Icon nama="info" ukuran={18} /> Sedang offline. Data terakhir tetap bisa dilihat, perubahan menunggu internet.
        </div>
      )}
      <main id="isi" className="isi" tabIndex={-1}>
        {halaman}
      </main>
      <nav className="nav-bawah kaca" aria-label="Menu utama">
        {NAV.map((n) => {
          const aktif = n.cocok.includes(s0 ?? "");
          return (
            <a key={n.path} href={`#${n.path}`} className={`nav-item ${aktif ? "aktif" : ""}`} aria-current={aktif ? "page" : undefined}>
              <span className="nav-ikon">
                <Icon nama={n.ikon} ukuran={24} />
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
    </>
  );
}

/** Latar gradien dengan gumpalan warna yang bergerak pelan, sumber cahaya untuk efek kaca. */
function Latar() {
  return (
    <div className="latar" aria-hidden="true">
      <span className="gumpal g1" />
      <span className="gumpal g2" />
      <span className="gumpal g3" />
    </div>
  );
}
