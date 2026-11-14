import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { Icon } from "../components/Icon";
import { TraceAgen } from "../components/TraceAgen";
import { Kaca, Kepala, Konfirmasi, Kosong, Tombol } from "../components/ui";
import { api, ApiError, type RingkasPercakapan, type RiwayatTanya, type TraceLangkah } from "../lib/api";
import { tanggalPanjang } from "../lib/format";
import { useApp } from "../lib/store";

type Pesan = { id: number; peran: "pengguna" | "agen"; isi: string; trace?: TraceLangkah[]; galat?: boolean };

const SARAN = ["Siapa saja yang belum bayar?", "Berapa porsi yang harus dimasak besok?", "Berapa porsi untuk jam 12?", "Total porsi semua hari berapa?"];

/** Batas riwayat yang dikirim: cukup untuk pertanyaan lanjutan, hemat token. */
const MAKS_RIWAYAT = 6;

export default function Tanya() {
  // Tanpa memilih hari: agen membaca semua hari milik akun dan menyaring tanggal sendiri.
  const { batches } = useApp();
  const [pesan, setPesan] = useState<Pesan[]>([]);
  const [teks, setTeks] = useState("");
  const [jalan, setJalan] = useState(false);
  const akhir = useRef<HTMLDivElement>(null);
  const nomor = useRef(0);
  // Riwayat percakapan tersimpan di server, terhapus otomatis 30 hari setelah chat terakhir.
  const [percakapanId, setPercakapanId] = useState<string | null>(null);
  const [daftar, setDaftar] = useState<RingkasPercakapan[]>([]);
  const [bukaRiwayat, setBukaRiwayat] = useState(false);
  const [hapus, setHapus] = useState<RingkasPercakapan | null>(null);
  const { toast } = useApp();

  const muatDaftar = useCallback(() => {
    api.daftarPercakapan().then(setDaftar).catch(() => setDaftar([]));
  }, []);
  useEffect(muatDaftar, [muatDaftar]);

  function percakapanBaru() {
    setPercakapanId(null);
    setPesan([]);
    setBukaRiwayat(false);
  }

  async function bukaPercakapan(id: string) {
    try {
      const d = await api.detailPercakapan(id);
      setPercakapanId(d.id);
      setPesan(d.pesan.map((m) => ({ id: ++nomor.current, peran: m.peran, isi: m.isi, trace: m.peran === "agen" ? m.trace : undefined })));
      setBukaRiwayat(false);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Percakapan tidak bisa dibuka.", "galat");
      muatDaftar();
    }
  }

  useEffect(() => {
    akhir.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [pesan, jalan]);

  async function kirim(pertanyaan: string) {
    const q = pertanyaan.trim();
    if (!q || jalan) return;
    const riwayat: RiwayatTanya = pesan
      .filter((p) => !p.galat)
      .slice(-MAKS_RIWAYAT)
      .map((p) => ({ peran: p.peran, isi: p.isi }));
    setPesan((ps) => [...ps, { id: ++nomor.current, peran: "pengguna", isi: q }]);
    setTeks("");
    setJalan(true);
    try {
      const r = await api.tanya(q, riwayat, { percakapanId });
      setPesan((ps) => [...ps, { id: ++nomor.current, peran: "agen", isi: r.jawaban, trace: r.trace }]);
      if (r.percakapan_id) setPercakapanId(r.percakapan_id);
      muatDaftar();
    } catch (e) {
      setPesan((ps) => [
        ...ps,
        { id: ++nomor.current, peran: "agen", isi: e instanceof ApiError ? e.message : "Agen tidak bisa menjawab sekarang.", galat: true },
      ]);
    } finally {
      setJalan(false);
    }
  }

  function kirimForm(e: FormEvent) {
    e.preventDefault();
    void kirim(teks);
  }

  return (
    <div className="tumpuk halaman-tanya halaman-sempit">
      <Kepala judul="Tanya pesanan" sub="AI hanya membaca data pesanan, tidak bisa mengubah apa pun." />
      {batches.length === 0 && (
        <Kaca className="kartu">
          <Kosong ikon="tanya" judul="Belum ada pesanan untuk ditanyakan">
            <p>Masukkan chat WhatsApp dulu. Setelah itu tanyakan apa saja tentang pesanan di semua hari.</p>
            <a href="#/masukkan-chat" className="tombol tombol-utama tombol-besar">
              <Icon nama="impor" /> Masukkan chat
            </a>
          </Kosong>
        </Kaca>
      )}

      {batches.length > 0 && (
        <>
          <div className="tanya-alat">
            <Tombol ikon="tambah" onClick={percakapanBaru} disabled={jalan || pesan.length === 0}>
              Percakapan baru
            </Tombol>
            <Tombol
              ikon="langkah"
              onClick={() => setBukaRiwayat((v) => !v)}
              aria-expanded={bukaRiwayat}
              aria-controls="daftar-riwayat"
            >
              Riwayat ({daftar.length})
            </Tombol>
          </div>
          {bukaRiwayat && (
            <Kaca className="kartu riwayat-tanya" id="daftar-riwayat">
              <h2 className="judul-kartu">Riwayat percakapan</h2>
              <p className="redup kecil">
                <Icon nama="info" ukuran={16} /> Percakapan terhapus otomatis 30 hari setelah chat terakhir. AI juga bisa membaca riwayat ini, misalnya "kemarin aku tanya apa soal Bu Wulan?".
              </p>
              {daftar.length === 0 ? (
                <p className="redup">Belum ada riwayat.</p>
              ) : (
                <ul className="riwayat-daftar">
                  {daftar.map((d) => (
                    <li key={d.id} className={d.id === percakapanId ? "aktif" : ""}>
                      <button type="button" className="riwayat-buka" onClick={() => bukaPercakapan(d.id)} aria-current={d.id === percakapanId ? "true" : undefined}>
                        <strong>{d.judul}</strong>
                        <span className="redup kecil">
                          {d.jumlah_pesan / 2} pertanyaan · terhapus {tanggalPanjang(d.berakhir_pada)}
                        </span>
                      </button>
                      <button type="button" className="tombol tombol-hantu tombol-ikon" aria-label={`Hapus percakapan ${d.judul}`} onClick={() => setHapus(d)}>
                        <Icon nama="hapus" ukuran={18} />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </Kaca>
          )}
          <div className="obrolan" aria-live="polite" aria-label="Percakapan">
            {pesan.length === 0 && (
              <Kaca className="kartu sambut-tanya">
                <span className="kartu-tanya-ikon">
                  <Icon nama="tanya" ukuran={28} />
                </span>
                <p>Tanyakan apa saja tentang pesanan di semua hari. Sebut harinya kalau perlu, misalnya "besok" atau "Sabtu". Setiap jawaban menunjukkan data apa yang dibaca AI.</p>
                <div className="saran-tanya">
                  {SARAN.map((s) => (
                    <button key={s} type="button" className="tag-tombol" onClick={() => kirim(s)}>
                      {s}
                    </button>
                  ))}
                </div>
              </Kaca>
            )}
            {pesan.map((p) => (
              <div key={p.id} className={`obrolan-baris ${p.peran}`}>
                <div className={`obrolan-gelembung ${p.galat ? "galat" : ""}`}>
                  <span className="sr">{p.peran === "pengguna" ? "Anda:" : "Agen:"}</span>
                  {p.galat && <Icon nama="peringatan" ukuran={18} />}
                  <p>{p.isi}</p>
                  {p.trace && <TraceAgen trace={p.trace} />}
                </div>
              </div>
            ))}
            {jalan && (
              <div className="obrolan-baris agen" role="status">
                <div className="obrolan-gelembung mengetik">
                  <span className="titik" />
                  <span className="titik" />
                  <span className="titik" />
                  <span className="sr">Agen sedang mencari jawaban</span>
                </div>
              </div>
            )}
            <div ref={akhir} />
          </div>

          <form className="kotak-tanya kaca" onSubmit={kirimForm}>
            <label htmlFor="tanya-isi" className="sr">
              Pertanyaan
            </label>
            <input
              id="tanya-isi"
              value={teks}
              onChange={(e) => setTeks(e.target.value)}
              placeholder="Tulis pertanyaan…"
              maxLength={1000}
              autoComplete="off"
              enterKeyHint="send"
            />
            <Tombol type="submit" varian="utama" ikon="kirim" disabled={!teks.trim() || jalan} aria-label="Kirim pertanyaan">
              Kirim
            </Tombol>
          </form>
        </>
      )}
      <Konfirmasi
        buka={hapus !== null}
        tutup={() => setHapus(null)}
        judul="Hapus percakapan ini?"
        pesan={hapus ? `"${hapus.judul}" dan semua jawabannya dihapus. Tidak bisa dibatalkan.` : ""}
        labelYa="Ya, hapus"
        bahaya
        aksi={async () => {
          if (!hapus) return;
          await api.hapusPercakapan(hapus.id);
          if (hapus.id === percakapanId) percakapanBaru();
          muatDaftar();
          toast("Percakapan dihapus.");
        }}
      />
    </div>
  );
}
