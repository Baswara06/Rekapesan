import { useEffect, useRef, useState, type DragEvent } from "react";
import contohChat from "../../../sample/ekspor-contoh.txt?raw";
import { PilihBatch } from "../components/Batch";
import { Icon } from "../components/Icon";
import { Galat, Kaca, Kepala, Tombol } from "../components/ui";
import { api, ApiError, type ImportResult } from "../lib/api";
import type { Rute } from "../lib/router";
import { useApp } from "../lib/store";

const CACHE_BAGIKAN = "rekapesan-bagikan";
const MAKS_BYTE = 20 * 1024 * 1024;

type Mode = "tempel" | "berkas";

export default function Impor({ rute }: { rute: Rute }) {
  const { batchAktif, batches, dataBerubah, toast, katalog, katalogSiap } = useApp();
  const katalogKosong = katalogSiap && !katalog.some((p) => p.aktif);
  const [mode, setMode] = useState<Mode>("tempel");
  const [teks, setTeks] = useState("");
  const [berkas, setBerkas] = useState<File | null>(null);
  const [seret, setSeret] = useState(false);
  const [jalan, setJalan] = useState(false);
  const [galat, setGalat] = useState<ApiError | null>(null);
  const [hasil, setHasil] = useState<ImportResult | null>(null);
  const inputBerkas = useRef<HTMLInputElement>(null);

  // Berkas yang dibagikan dari WhatsApp lewat share target PWA disimpan service worker di cache.
  useEffect(() => {
    if (rute.query.get("bagikan") !== "1" || !("caches" in window)) return;
    (async () => {
      const cache = await caches.open(CACHE_BAGIKAN);
      const resBerkas = await cache.match("/bagikan/berkas");
      const resTeks = await cache.match("/bagikan/teks");
      if (resBerkas) {
        const nama = decodeURIComponent(resBerkas.headers.get("X-Nama-Berkas") ?? "chat.txt");
        const blob = await resBerkas.blob();
        setBerkas(new File([blob], nama, { type: blob.type }));
        setMode("berkas");
        toast("Chat dari WhatsApp siap diimpor. Periksa hari tujuan, lalu tekan Impor.", "info");
      } else if (resTeks) {
        setTeks(await resTeks.text());
        setMode("tempel");
        toast("Teks dari WhatsApp siap diimpor.", "info");
      }
      await cache.delete("/bagikan/berkas");
      await cache.delete("/bagikan/teks");
    })().catch(() => toast("Berkas bagikan tidak bisa dibaca. Coba tempel teks.", "galat"));
  }, [rute.query, toast]);

  function pilihBerkas(f: File | undefined | null) {
    setGalat(null);
    setHasil(null);
    if (!f) return;
    if (!/\.(txt|zip)$/i.test(f.name)) {
      setGalat(new ApiError(400, "format_file_tidak_dikenal", "Pilih berkas .txt atau .zip hasil Ekspor chat WhatsApp."));
      return;
    }
    if (f.size > MAKS_BYTE) {
      setGalat(new ApiError(413, "validasi_gagal", "Berkas terlalu besar (maksimal 20 MB). Ekspor chat tanpa media."));
      return;
    }
    setBerkas(f);
  }

  function lepas(e: DragEvent) {
    e.preventDefault();
    setSeret(false);
    pilihBerkas(e.dataTransfer.files?.[0]);
  }

  async function impor() {
    if (!batchAktif) return;
    setJalan(true);
    setGalat(null);
    setHasil(null);
    try {
      const r = mode === "berkas" && berkas ? await api.imporBerkas(batchAktif.id, berkas, berkas.name) : await api.imporTeks(batchAktif.id, teks);
      setHasil(r);
      dataBerubah();
      if (mode === "tempel") setTeks("");
      else setBerkas(null);
    } catch (e) {
      setGalat(e instanceof ApiError ? e : new ApiError(0, "galat", String(e)));
    } finally {
      setJalan(false);
    }
  }

  const siap = !!batchAktif && (mode === "tempel" ? teks.trim().length > 0 : !!berkas);

  return (
    <div className="tumpuk halaman-sempit">
      <Kepala judul="Masukkan chat" sub="Langkah 1 dari 3" />
      <PilihBatch ringkas />

      {katalogKosong && galat?.kode !== "katalog_kosong" && (
        <div className="kartu-ajak nada-kuning kaca" role="note">
          <Icon nama="peringatan" />
          <span>
            <strong>Isi menu dulu.</strong> Tanpa menu di Katalog, pesanan tidak bisa dicocokkan dan harganya tidak bisa dihitung.
          </span>
          <a href="#/katalog" className="tombol tombol-utama">
            Buka Katalog
          </a>
        </div>
      )}

      {batches.length > 0 && (
        <Kaca className="kartu">
          <div className="segmen" role="tablist" aria-label="Cara memasukkan chat">
            <button role="tab" type="button" aria-selected={mode === "tempel"} className={mode === "tempel" ? "aktif" : ""} onClick={() => setMode("tempel")}>
              <Icon nama="salin" /> Tempel teks
            </button>
            <button role="tab" type="button" aria-selected={mode === "berkas"} className={mode === "berkas" ? "aktif" : ""} onClick={() => setMode("berkas")}>
              <Icon nama="berkas" /> Unggah file
            </button>
          </div>

          {mode === "tempel" ? (
            <div className="isian" role="tabpanel">
              <label htmlFor="teks-chat">Tempel chat grup di sini</label>
              <textarea
                id="teks-chat"
                rows={9}
                value={teks}
                onChange={(e) => {
                  setTeks(e.target.value);
                  setHasil(null);
                }}
                placeholder={"12/11/26 09.15 - Bu Rina: ayam bakar 2 ya, kirim ke Blok C no 4\n12/11/26 09.17 - Pak Anton: aybak 1 sama es teh 1"}
                aria-describedby="bantu-tempel"
              />
              <p id="bantu-tempel" className="bantu">
                Salin dari chat ekspor, atau pilih beberapa pesan di WhatsApp lalu Salin.
              </p>
              <Tombol varian="hantu" ikon="chat" onClick={() => setTeks(contohChat)}>
                Pakai contoh chat
              </Tombol>
            </div>
          ) : (
            <div role="tabpanel">
              <div
                className={`zona-lepas ${seret ? "seret" : ""} ${berkas ? "terisi" : ""}`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setSeret(true);
                }}
                onDragLeave={() => setSeret(false)}
                onDrop={lepas}
              >
                <Icon nama={berkas ? "berkas" : "impor"} ukuran={36} />
                {berkas ? (
                  <>
                    <strong className="putus-kata">{berkas.name}</strong>
                    <span className="redup">{(berkas.size / 1024).toFixed(0)} KB</span>
                  </>
                ) : (
                  <>
                    <strong>Pilih berkas ekspor chat</strong>
                    <span className="redup">.txt atau .zip, maksimal 20 MB</span>
                  </>
                )}
                <Tombol onClick={() => inputBerkas.current?.click()} ikon="berkas">
                  {berkas ? "Ganti berkas" : "Pilih berkas"}
                </Tombol>
                <input
                  ref={inputBerkas}
                  type="file"
                  accept=".txt,.zip,text/plain,application/zip"
                  className="sr"
                  tabIndex={-1}
                  aria-hidden="true"
                  onChange={(e) => {
                    pilihBerkas(e.target.files?.[0]);
                    e.target.value = "";
                  }}
                />
              </div>
              <CaraEkspor />
            </div>
          )}

          <Tombol varian="utama" besar penuh ikon="impor" memuat={jalan} disabled={!siap} onClick={impor}>
            {jalan ? "Sedang dibaca…" : `Impor ke ${batchAktif?.nama ?? "hari ini"}`}
          </Tombol>

          {jalan && (
            <div className="proses" role="status">
              <p>
                <strong>Sedang diproses.</strong> Biasanya beberapa detik.
              </p>
              <ul>
                <li>Memecah chat per pengirim</li>
                <li>Menyamarkan nomor telepon</li>
                <li>AI memahami isi pesanan (tanpa harga)</li>
                <li>Harga dan total dihitung dari katalog Anda</li>
              </ul>
            </div>
          )}
        </Kaca>
      )}

      {galat &&
        (galat.kode === "katalog_kosong" ? (
          // Mengulang impor tidak ada gunanya sebelum menu diisi, jadi yang ditawarkan hanya jalan ke Katalog.
          <Galat galat={galat}>
            <a href="#/katalog" className="tombol tombol-utama">
              <Icon nama="katalog" /> Buka Katalog
            </a>
          </Galat>
        ) : (
          <Galat galat={galat} ulang={siap ? impor : undefined} />
        ))}
      {galat?.kode === "impor_bentrok" && <p className="bantu">Impor sebelumnya masih berjalan. Tunggu beberapa detik.</p>}

      {hasil && <HasilImpor hasil={hasil} />}
    </div>
  );
}

function HasilImpor({ hasil }: { hasil: ImportResult }) {
  const tidakAdaBaru = hasil.pesan_baru === 0;
  return (
    <Kaca className="kartu hasil-impor" role="status" aria-live="polite">
      <div className="hasil-kepala">
        <span className="bulat-sukses">
          <Icon nama="centang" ukuran={28} />
        </span>
        <div>
          <h2>{tidakAdaBaru ? "Tidak ada pesan baru" : "Chat berhasil dibaca"}</h2>
          <p className="redup">
            {hasil.pesan_baru} pesan baru, {hasil.pesan_dilewati} dilewati
            {hasil.pesan_dilewati > 0 && " (sudah pernah masuk atau di luar tanggalnya)"}.
          </p>
        </div>
      </div>
      <dl className="kisi-hasil">
        <div>
          <dt>Pesanan baru</dt>
          <dd>{hasil.pesanan_dibuat}</dd>
        </div>
        <div>
          <dt>Pesanan berubah</dt>
          <dd>{hasil.pesanan_diubah}</dd>
        </div>
        <div className={hasil.perlu_cek ? "nada-kuning" : ""}>
          <dt>Perlu dicek</dt>
          <dd>{hasil.perlu_cek}</dd>
        </div>
      </dl>
      <a href="#/cek" className="tombol tombol-utama tombol-besar tombol-penuh">
        <Icon nama="cek" />
        <span>Lanjut cek pesanan</span>
      </a>
    </Kaca>
  );
}

function CaraEkspor() {
  return (
    <details className="lipat">
      <summary>
        <Icon nama="info" /> Cara mengambil ekspor chat dari WhatsApp
      </summary>
      <div className="lipat-isi">
        <h3>
          <Icon nama="hp" ukuran={18} /> Android
        </h3>
        <ol>
          <li>Buka chat pesanan di WhatsApp.</li>
          <li>Ketuk titik tiga di kanan atas, pilih <strong>Lainnya</strong>, lalu <strong>Ekspor chat</strong>.</li>
          <li>
            Pilih <strong>Tanpa media</strong>.
          </li>
          <li>
            Pilih <strong>RekaPesan</strong> di daftar bagikan (bila aplikasi sudah dipasang), atau simpan ke berkas lalu unggah di sini.
          </li>
        </ol>
        <h3>
          <Icon nama="hp" ukuran={18} /> iPhone
        </h3>
        <ol>
          <li>Buka grup, ketuk nama grup di atas.</li>
          <li>
            Gulir ke bawah, ketuk <strong>Ekspor Chat</strong>, pilih <strong>Tanpa Media</strong>.
          </li>
          <li>
            Pilih <strong>Simpan ke File</strong>, lalu unggah di sini. iPhone belum mendukung bagikan langsung ke aplikasi web.
          </li>
        </ol>
      </div>
    </details>
  );
}
