import { useState } from "react";
import { Icon, type NamaIkon } from "../components/Icon";
import { Kaca, Kepala, Konfirmasi, Tombol } from "../components/ui";
import { api, ApiError } from "../lib/api";
import { tanggalPanjang } from "../lib/format";
import { useApp, type Tema } from "../lib/store";

const TEMA: { id: Tema; label: string; ikon: NamaIkon }[] = [
  { id: "otomatis", label: "Ikuti HP", ikon: "hp" },
  { id: "terang", label: "Terang", ikon: "matahari" },
  { id: "gelap", label: "Gelap", ikon: "bulan" },
];

export default function Pengaturan() {
  const { tema, setTema, batches, muatBatch, keluar, toast, dataBerubah } = useApp();
  const [hapus, setHapus] = useState<{ id: string; nama: string } | null>(null);

  return (
    <div className="tumpuk halaman-sempit">
      <Kepala judul="Pengaturan" kembali="#/lainnya" />

      <Kaca className="kartu">
        <fieldset className="pilihan-grup">
          <legend className="judul-kartu">
            <Icon nama="matahari" /> Tampilan
          </legend>
          <div className="pilihan-kisi">
            {TEMA.map((t) => (
              <label key={t.id} className={`pilihan ${tema === t.id ? "aktif" : ""}`}>
                <input type="radio" name="tema" value={t.id} checked={tema === t.id} onChange={() => setTema(t.id)} />
                <Icon nama={t.ikon} ukuran={26} />
                <span>{t.label}</span>
              </label>
            ))}
          </div>
        </fieldset>
      </Kaca>

      <Kaca className="kartu">
        <h2 className="judul-kartu">
          <Icon nama="perisai" /> AI dan privasi
        </h2>
        <ul className="daftar-janji">
          <li>
            <Icon nama="centang" ukuran={18} /> Nomor telepon disamarkan sebelum chat dibaca AI.
          </li>
          <li>
            <Icon nama="centang" ukuran={18} /> AI hanya memahami isi chat. Harga, total, stok, dan rekap dihitung sistem dari katalog Anda.
          </li>
          <li>
            <Icon nama="centang" ukuran={18} /> Tidak ada pesanan yang final sebelum Anda setujui.
          </li>
          <li>
            <Icon nama="centang" ukuran={18} /> Chat yang menyuruh mengubah harga diabaikan, karena isi chat adalah data, bukan perintah.
          </li>
          <li>
            <Icon nama="centang" ukuran={18} /> Menghapus PO ikut menghapus chat mentahnya.
          </li>
        </ul>
      </Kaca>

      <Kaca className="kartu">
        <h2 className="judul-kartu">
          <Icon nama="hapus" /> Hapus data PO
        </h2>
        <p className="redup">Menghapus PO beserta chat mentah, data pembeli, dan pesanannya. Tidak bisa dibatalkan.</p>
        {batches.length === 0 ? (
          <p className="redup miring">Belum ada PO.</p>
        ) : (
          <ul className="daftar-baris">
            {batches.map((b) => (
              <li key={b.id} className="baris-hapus">
                <span>
                  <strong>{b.nama}</strong>
                  <span className="redup kecil">Kirim {tanggalPanjang(b.tanggal_kirim)}</span>
                </span>
                <Tombol varian="hantu" ikon="hapus" className="teks-bahaya" onClick={() => setHapus(b)} aria-label={`Hapus ${b.nama}`}>
                  Hapus
                </Tombol>
              </li>
            ))}
          </ul>
        )}
      </Kaca>

      <Tombol ikon="keluar" besar penuh onClick={keluar}>
        Keluar
      </Tombol>

      <Konfirmasi
        buka={!!hapus}
        tutup={() => setHapus(null)}
        judul={`Hapus ${hapus?.nama ?? ""}?`}
        pesan={
          <p>
            Semua chat mentah, data pembeli, dan pesanan di PO ini <strong>dihapus permanen</strong>. Rekapnya juga hilang.
          </p>
        }
        labelYa="Ya, hapus permanen"
        bahaya
        aksi={async () => {
          if (!hapus) return;
          try {
            await api.hapusBatch(hapus.id);
            await muatBatch();
            dataBerubah();
            toast(`${hapus.nama} dihapus beserta chat mentahnya.`, "info");
          } catch (e) {
            toast(e instanceof ApiError ? e.message : "Gagal menghapus.", "galat");
          }
        }}
      />
    </div>
  );
}
