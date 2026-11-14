import { useEffect, useRef, useState, type FormEvent } from "react";
import { PilihBatch } from "../components/Batch";
import { Icon } from "../components/Icon";
import { TraceAgen } from "../components/TraceAgen";
import { Kaca, Kepala, Tombol } from "../components/ui";
import { api, ApiError, type RiwayatTanya, type TraceLangkah } from "../lib/api";
import { useApp } from "../lib/store";

type Pesan = { id: number; peran: "pengguna" | "agen"; isi: string; trace?: TraceLangkah[]; galat?: boolean };

const SARAN = ["Berapa ayam bakar untuk jam 12?", "Siapa saja yang belum bayar?", "Pesanan Bu Rina apa saja?", "Total porsi hari ini berapa?"];

/** Batas riwayat yang dikirim: cukup untuk pertanyaan lanjutan, hemat token. */
const MAKS_RIWAYAT = 6;

export default function Tanya() {
  const { batchAktif, batches } = useApp();
  const [pesan, setPesan] = useState<Pesan[]>([]);
  const [teks, setTeks] = useState("");
  const [jalan, setJalan] = useState(false);
  const akhir = useRef<HTMLDivElement>(null);
  const nomor = useRef(0);

  useEffect(() => {
    setPesan([]);
  }, [batchAktif?.id]);

  useEffect(() => {
    akhir.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [pesan, jalan]);

  async function kirim(pertanyaan: string) {
    const q = pertanyaan.trim();
    if (!q || !batchAktif || jalan) return;
    const riwayat: RiwayatTanya = pesan
      .filter((p) => !p.galat)
      .slice(-MAKS_RIWAYAT)
      .map((p) => ({ peran: p.peran, isi: p.isi }));
    setPesan((ps) => [...ps, { id: ++nomor.current, peran: "pengguna", isi: q }]);
    setTeks("");
    setJalan(true);
    try {
      const r = await api.tanya(batchAktif.id, q, riwayat);
      setPesan((ps) => [...ps, { id: ++nomor.current, peran: "agen", isi: r.jawaban, trace: r.trace }]);
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
      {batches.length === 0 ? <PilihBatch /> : <PilihBatch ringkas />}

      {batchAktif && (
        <>
          <div className="obrolan" aria-live="polite" aria-label="Percakapan">
            {pesan.length === 0 && (
              <Kaca className="kartu sambut-tanya">
                <span className="kartu-tanya-ikon">
                  <Icon nama="tanya" ukuran={28} />
                </span>
                <p>Tanyakan apa saja tentang pesanan di {batchAktif.nama}. Setiap jawaban menunjukkan data apa yang dibaca AI.</p>
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
    </div>
  );
}
