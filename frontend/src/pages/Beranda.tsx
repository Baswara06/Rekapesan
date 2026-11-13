import { PilihBatch } from "../components/Batch";
import { Icon, type NamaIkon } from "../components/Icon";
import { api } from "../lib/api";
import { rupiah, sapaan } from "../lib/format";
import { useApp, useMuat } from "../lib/store";

export default function Beranda({ perluCek }: { perluCek: number | null }) {
  const { batchAktif, batchSiap, versiData } = useApp();
  const rekap = useMuat(batchAktif ? () => api.rekap(batchAktif.id) : null, [batchAktif?.id, versiData]);

  const langkah: { no: number; href: string; ikon: NamaIkon; judul: string; isi: string; selesai?: boolean }[] = [
    { no: 1, href: "#/impor", ikon: "impor", judul: "Masukkan chat", isi: "Tempel teks atau unggah ekspor chat grup WhatsApp." },
    {
      no: 2,
      href: "#/cek",
      ikon: "cek",
      judul: "Cek pesanan",
      isi: perluCek ? `${perluCek} pesanan menunggu dicek.` : "AI membaca chat, Anda yang memutuskan.",
    },
    { no: 3, href: "#/rekap", ikon: "rekap", judul: "Lihat rekap", isi: "Jumlah masak, urutan kirim, dan siapa belum bayar." },
  ];

  return (
    <div className="tumpuk">
      <header className="sapa">
        <p className="redup">{sapaan()},</p>
        <h1 className="judul-merek">Rekapesan</h1>
      </header>

      {batchSiap ? <PilihBatch /> : <div className="kaca kerangka" />}

      {batchAktif && (
        <div className="kisi-angka" aria-label="Ringkasan PO">
          <a href="#/cek" className={`kaca angka-kartu ${perluCek ? "nada-kuning" : ""}`}>
            <Icon nama="peringatan" />
            <span className="angka-besar">{perluCek ?? "-"}</span>
            <span className="angka-label">Perlu dicek</span>
          </a>
          <a href="#/rekap" className="kaca angka-kartu">
            <Icon nama="dompet" />
            <span className="angka-besar angka-uang">{rekap.data ? rupiah(rekap.data.omzet) : "-"}</span>
            <span className="angka-label">Omzet disetujui</span>
          </a>
          <a href="#/rekap" className="kaca angka-kartu">
            <Icon nama="orang" />
            <span className="angka-besar">{rekap.data ? rekap.data.belum_bayar.length : "-"}</span>
            <span className="angka-label">Belum bayar</span>
          </a>
          <a href="#/rekap" className="kaca angka-kartu">
            <Icon nama="katalog" />
            <span className="angka-besar">{rekap.data ? rekap.data.produksi.reduce((a, p) => a + p.qty, 0) : "-"}</span>
            <span className="angka-label">Porsi dimasak</span>
          </a>
        </div>
      )}

      <section aria-labelledby="judul-langkah">
        <h2 id="judul-langkah" className="judul-bagian">
          Tiga langkah
        </h2>
        <ol className="langkah-daftar">
          {langkah.map((l) => (
            <li key={l.no}>
              <a href={l.href} className="kaca langkah-kartu">
                <span className="langkah-no" aria-hidden="true">
                  {l.no}
                </span>
                <span className="langkah-teks">
                  <strong>{l.judul}</strong>
                  <span>{l.isi}</span>
                </span>
                <Icon nama="kanan" />
              </a>
            </li>
          ))}
        </ol>
      </section>

      <a href="#/tanya" className="kaca kartu-tanya">
        <span className="kartu-tanya-ikon">
          <Icon nama="tanya" ukuran={26} />
        </span>
        <span>
          <strong>Tanya soal pesanan</strong>
          <span className="redup">"Berapa ayam bakar untuk jam 12?"</span>
        </span>
        <Icon nama="kanan" />
      </a>
    </div>
  );
}
