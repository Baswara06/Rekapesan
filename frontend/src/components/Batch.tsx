import { useId, useState, type FormEvent } from "react";
import { api, ApiError } from "../lib/api";
import { hariIniISO, tanggalPanjang } from "../lib/format";
import { useApp } from "../lib/store";
import { Icon } from "./Icon";
import { Dialog, Kaca, Kosong, Tombol } from "./ui";

/** Pemilih batch PO aktif. Semua layar (impor, cek, rekap, tanya) bekerja pada batch ini. */
export function PilihBatch({ ringkas }: { ringkas?: boolean }) {
  const { batches, batchAktif, pilihBatch } = useApp();
  const [buatBuka, setBuatBuka] = useState(false);
  const id = useId();

  if (batches.length === 0) {
    return (
      <Kaca className="kartu">
        <Kosong ikon="kalender" judul="Belum ada pesanan">
          <p>Masukkan chat WhatsApp. Pesanan dikelompokkan per hari secara otomatis.</p>
          <a href="#/masukkan-chat" className="tombol tombol-utama tombol-besar">
            <Icon nama="impor" /> Masukkan chat
          </a>
        </Kosong>
        <BuatBatch buka={buatBuka} tutup={() => setBuatBuka(false)} />
      </Kaca>
    );
  }

  return (
    <Kaca className={`kartu pilih-batch ${ringkas ? "ringkas" : ""}`}>
      <label htmlFor={id} className="label-kecil">
        <Icon nama="kalender" ukuran={18} /> Hari yang ditampilkan
      </label>
      <div className="pilih-batch-baris">
        <div className="pilih-wrap">
          <select id={id} value={batchAktif?.id ?? ""} onChange={(e) => pilihBatch(e.target.value)}>
            {batches.map((b) => (
              <option key={b.id} value={b.id}>
                {b.nama}
              </option>
            ))}
          </select>
          <Icon nama="bawah" className="pilih-panah" />
        </div>
        <Tombol ikon="tambah" onClick={() => setBuatBuka(true)} aria-label="Buat kelompok pesanan manual" className="tombol-ikon-teks">
          Baru
        </Tombol>
      </div>
      {batchAktif && !ringkas && (
        <p className="redup kecil">
          <Icon nama="truk" ukuran={16} /> Dikirim {tanggalPanjang(batchAktif.tanggal_kirim)}
        </p>
      )}
      <BuatBatch buka={buatBuka} tutup={() => setBuatBuka(false)} />
    </Kaca>
  );
}

export function BuatBatch({ buka, tutup }: { buka: boolean; tutup: () => void }) {
  const { muatBatch, pilihBatch, toast } = useApp();
  const [nama, setNama] = useState("");
  const [kirim, setKirim] = useState(hariIniISO(1));
  const [mulai, setMulai] = useState(hariIniISO());
  const [jalan, setJalan] = useState(false);
  const [galat, setGalat] = useState("");

  async function simpan(e: FormEvent) {
    e.preventDefault();
    if (mulai && kirim && mulai > kirim) {
      setGalat("Tanggal mulai tidak boleh setelah tanggal kirim.");
      return;
    }
    setJalan(true);
    setGalat("");
    try {
      const b = await api.buatBatch({ nama: nama.trim(), tanggal_kirim: kirim, tanggal_mulai: mulai || null });
      await muatBatch();
      pilihBatch(b.id);
      toast(`Kelompok "${b.nama}" dibuat.`);
      setNama("");
      tutup();
    } catch (err) {
      setGalat(err instanceof ApiError ? err.message : "Gagal membuat kelompok pesanan.");
    } finally {
      setJalan(false);
    }
  }

  return (
    <Dialog buka={buka} tutup={tutup} judul="Buat kelompok pesanan manual" lembar>
      <form onSubmit={simpan} className="formulir">
        <div className="isian">
          <label htmlFor="nama-po">Nama kelompok</label>
          <input id="nama-po" value={nama} onChange={(e) => setNama(e.target.value)} placeholder="mis. Pesanan Jumat" required maxLength={120} />
        </div>
        <div className="isian">
          <label htmlFor="mulai-po">Tanggal mulai chat</label>
          <input id="mulai-po" type="date" value={mulai} onChange={(e) => setMulai(e.target.value)} aria-describedby="mulai-bantu" />
          <p id="mulai-bantu" className="bantu">Chat sebelum tanggal ini tidak ikut dibaca.</p>
        </div>
        <div className="isian">
          <label htmlFor="kirim-po">Tanggal kirim</label>
          <input id="kirim-po" type="date" value={kirim} onChange={(e) => setKirim(e.target.value)} required />
        </div>
        {galat && (
          <p className="teks-galat" role="alert">
            <Icon nama="peringatan" ukuran={18} /> {galat}
          </p>
        )}
        <Tombol type="submit" varian="utama" besar penuh memuat={jalan} disabled={!nama.trim() || !kirim}>
          Simpan PO
        </Tombol>
      </form>
    </Dialog>
  );
}
