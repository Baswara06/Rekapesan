import { useId, useState, type FormEvent } from "react";
import { api, ApiError } from "../lib/api";
import { useApp } from "../lib/store";
import { BuatBatch } from "./Batch";
import { Icon, type NamaIkon } from "./Icon";
import { Kaca, Tombol } from "./ui";

const TOKO_MINIMAL = 2;
const TOKO_MAKSIMAL = 60;

interface Langkah {
  judul: string;
  isi: string;
  ikon: NamaIkon;
  selesai: boolean;
  /** Alasan terkunci. Kosong berarti langkah ini bisa dikerjakan. */
  kunci: string;
  aksi: { label: string; href?: string; klik?: () => void };
}

/**
 * Daftar langkah untuk akun baru: tambah menu, buat PO, masukkan chat.
 * Urutannya wajib, karena impor ditolak server (`katalog_kosong`) bila belum ada menu,
 * dan chat selalu masuk ke sebuah PO.
 */
export function SiapkanToko({ adaPesanan }: { adaPesanan: boolean }) {
  const { katalog, batches } = useApp();
  const [buatPO, setBuatPO] = useState(false);
  const idJudul = useId();

  const adaMenu = katalog.some((p) => p.aktif);
  const adaPO = batches.length > 0;
  const langkah: Langkah[] = [
    {
      judul: "Tambah menu",
      isi: "Nama, harga, dan nama panggilan dari pembeli. Harga hanya disimpan di sini, AI tidak melihatnya.",
      ikon: "katalog",
      selesai: adaMenu,
      kunci: "",
      aksi: { label: "Buka Katalog", href: "#/katalog" },
    },
    {
      judul: "Buat PO",
      isi: 'Misalnya "PO Jumat". Semua pesanan dari chat masuk ke PO ini.',
      ikon: "kalender",
      selesai: adaPO,
      kunci: adaMenu ? "" : "Tambah menu dulu",
      aksi: { label: "Buat PO", klik: () => setBuatPO(true) },
    },
    {
      judul: "Masukkan chat",
      isi: "Tempel atau unggah chat grup WhatsApp. AI membaca pesanannya, Anda yang menyetujui.",
      ikon: "impor",
      selesai: adaPesanan,
      // Impor ditolak server tanpa menu, jadi langkah ini butuh menu dan PO sekaligus.
      kunci: !adaMenu ? "Tambah menu dulu" : !adaPO ? "Buat PO dulu" : "",
      aksi: { label: "Masukkan chat", href: "#/impor" },
    },
  ];
  const jumlahSelesai = langkah.filter((l) => l.selesai).length;
  const berikutnya = langkah.findIndex((l) => !l.selesai && !l.kunci);

  return (
    <Kaca as="section" className="kartu siapkan-toko" aria-labelledby={idJudul}>
      <div className="siapkan-kepala">
        <h2 id={idJudul}>Siapkan toko</h2>
        <span className="lencana nada-hijau">
          {jumlahSelesai} dari {langkah.length} selesai
        </span>
      </div>
      <div
        className="siapkan-batang"
        role="progressbar"
        aria-label="Kemajuan menyiapkan toko"
        aria-valuemin={0}
        aria-valuemax={langkah.length}
        aria-valuenow={jumlahSelesai}
      >
        <span style={{ width: `${(jumlahSelesai / langkah.length) * 100}%` }} />
      </div>
      <ol className="siapkan-daftar">
        {langkah.map((l, i) => {
          const status = l.selesai ? "selesai" : l.kunci ? "terkunci" : "siap";
          return (
            <li key={l.judul} className={`siapkan-langkah ${status} ${i === berikutnya ? "berikutnya" : ""}`}>
              <span className="siapkan-no" aria-hidden="true">
                {l.selesai ? <Icon nama="centang" ukuran={18} /> : i + 1}
              </span>
              <div className="siapkan-teks">
                <strong>
                  {l.judul}
                  <span className="sr">
                    {l.selesai ? ", selesai" : l.kunci ? `, terkunci. ${l.kunci}` : ", belum dikerjakan"}
                  </span>
                </strong>
                <span className="redup kecil">{l.kunci && !l.selesai ? `${l.kunci}. ${l.isi}` : l.isi}</span>
              </div>
              {!l.selesai &&
                (l.kunci ? (
                  <span className="siapkan-kunci" aria-hidden="true">
                    <Icon nama="kunci" ukuran={18} />
                  </span>
                ) : l.aksi.href ? (
                  <a href={l.aksi.href} className={`tombol ${i === berikutnya ? "tombol-utama" : ""}`}>
                    {l.aksi.label}
                  </a>
                ) : (
                  <Tombol varian={i === berikutnya ? "utama" : undefined} onClick={l.aksi.klik}>
                    {l.aksi.label}
                  </Tombol>
                ))}
            </li>
          );
        })}
      </ol>
      <BuatBatch buka={buatPO} tutup={() => setBuatPO(false)} />
    </Kaca>
  );
}

/** Form nama toko (PATCH /auth/me). Dipakai di Beranda saat nama toko masih kosong, dan di Pengaturan. */
export function FormNamaToko({ awal = "", label = "Nama toko", tombol = "Simpan", saatTersimpan }: {
  awal?: string;
  label?: string;
  tombol?: string;
  saatTersimpan?: () => void;
}) {
  const { setAkun, toast } = useApp();
  const [nama, setNama] = useState(awal);
  const [jalan, setJalan] = useState(false);
  const [galat, setGalat] = useState("");
  const id = useId();

  async function simpan(e: FormEvent) {
    e.preventDefault();
    const rapi = nama.trim().replace(/\s+/g, " ");
    if (rapi.length < TOKO_MINIMAL || rapi.length > TOKO_MAKSIMAL) {
      setGalat(`Nama toko ${TOKO_MINIMAL}-${TOKO_MAKSIMAL} karakter.`);
      return;
    }
    setJalan(true);
    setGalat("");
    try {
      setAkun(await api.ubahAkun(rapi));
      toast("Nama toko disimpan.");
      saatTersimpan?.();
    } catch (err) {
      setGalat(err instanceof ApiError ? err.message : "Gagal menyimpan nama toko.");
    } finally {
      setJalan(false);
    }
  }

  return (
    <form className="form-toko" onSubmit={simpan} noValidate>
      <label htmlFor={id}>{label}</label>
      <div className="form-toko-baris">
        <input
          id={id}
          value={nama}
          onChange={(e) => {
            setNama(e.target.value);
            setGalat("");
          }}
          maxLength={TOKO_MAKSIMAL}
          autoComplete="organization"
          placeholder="mis. Dapur Bu Rina"
          aria-invalid={!!galat}
          aria-describedby={galat ? `${id}-galat` : undefined}
        />
        <Tombol type="submit" varian="utama" memuat={jalan} disabled={!nama.trim() || nama.trim() === awal}>
          {tombol}
        </Tombol>
      </div>
      {galat && (
        <p id={`${id}-galat`} className="teks-galat" role="alert">
          <Icon nama="peringatan" ukuran={16} /> {galat}
        </p>
      )}
    </form>
  );
}

/** Kartu ajakan di Beranda untuk akun yang nama tokonya masih kosong (akun lama sebelum ada kolom nama toko). */
export function AjakIsiNamaToko() {
  return (
    <Kaca as="section" className="kartu ajak-toko" aria-label="Lengkapi nama toko">
      <p>
        <strong>Lengkapi nama toko Anda.</strong> Nama toko muncul di Beranda dan di balasan konfirmasi ke pembeli.
      </p>
      <FormNamaToko label="Nama toko" />
    </Kaca>
  );
}
