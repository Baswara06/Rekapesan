import { useRef, useState } from "react";
import { Icon } from "../components/Icon";
import { MenuBelumDikenal } from "../components/MenuBelumDikenal";
import { Galat, Kaca, Kepala, Tombol } from "../components/ui";
import { api, ApiError, type HasilImporHarian, type IsiChat, type PratinjauImpor } from "../lib/api";
import { rupiah, tanggalPanjang, tanggalPendek } from "../lib/format";
import { pergi } from "../lib/router";
import { useApp } from "../lib/store";

// Wizard "Masukkan chat" untuk buku pesanan harian:
// 1) tempel/unggah chat → pratinjau (penjual, hari, menu + harga) → penjual cek lalu simpan menu baru,
// 2) proses: AI membaca pesanan per hari (tiap hari = satu PO biasa),
// 3) kembali ke Beranda yang berisi papan pesanan.
// Harga menu diisi/dicek penjual dan disimpan lewat POST /products. AI tidak pernah menentukan harga.

const MAKS_BYTE = 20 * 1024 * 1024;
const LANGKAH = ["Masukkan chat", "Cek menu", "Proses pesanan"] as const;

/** `dariPembeli`: disebut pembeli tapi tidak ada di daftar menu penjual (tebakan kode, tidak dicentang otomatis). */
type BarisMenu = { nama: string; harga: string; sudahAda: boolean; dipilih: boolean; dariPembeli?: { jumlah: number; contoh: string } };

function jadiGalat(e: unknown): ApiError {
  return e instanceof ApiError ? e : new ApiError(0, "galat", String(e));
}

export default function MasukkanChat() {
  const { muatKatalog, muatBatch, dataBerubah, toast } = useApp();
  const [langkah, setLangkah] = useState<0 | 1 | 2>(0);
  const [mode, setMode] = useState<"tempel" | "berkas">("tempel");
  const [teks, setTeks] = useState("");
  const [berkas, setBerkas] = useState<File | null>(null);
  const [pratinjau, setPratinjau] = useState<PratinjauImpor | null>(null);
  const [menu, setMenu] = useState<BarisMenu[]>([]);
  const [menuTersimpan, setMenuTersimpan] = useState(false);
  const [jalan, setJalan] = useState(false);
  const [galat, setGalat] = useState<ApiError | null>(null);
  const [hasil, setHasil] = useState<HasilImporHarian | null>(null);
  const inputBerkas = useRef<HTMLInputElement>(null);

  const isi: IsiChat | null = mode === "berkas" ? (berkas ? { berkas } : null) : teks.trim() ? { teks } : null;

  function pilihBerkas(f: File | undefined | null) {
    setGalat(null);
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

  async function bacaPratinjau() {
    if (!isi) return;
    setJalan(true);
    setGalat(null);
    try {
      const p = await api.pratinjauImpor(isi);
      setPratinjau(p);
      setMenu([
        ...p.menu.map((m) => ({ nama: m.nama, harga: m.harga != null ? String(m.harga) : "", sudahAda: m.sudah_ada, dipilih: true })),
        ...(p.menu_dari_pembeli ?? []).map((m) => ({
          nama: m.nama,
          harga: "",
          sudahAda: false,
          dipilih: false,
          dariPembeli: { jumlah: m.jumlah_sebut, contoh: m.contoh },
        })),
      ]);
      setMenuTersimpan(false);
      setLangkah(1);
    } catch (e) {
      setGalat(jadiGalat(e));
    } finally {
      setJalan(false);
    }
  }

  // Menu terdeteksi sudah tercentang. Hanya menu baru yang dicentang yang disimpan dan wajib punya harga.
  const menuBaru = menu.filter((m) => !m.sudahAda && m.dipilih);
  const hargaValid = (h: string) => /^\d+$/.test(h) && Number(h) > 0;
  const menuBaruValid = menuBaru.every((m) => m.nama.trim() && hargaValid(m.harga));

  async function simpanMenu() {
    setJalan(true);
    setGalat(null);
    try {
      let n = 0;
      for (const [i, m] of menu.entries()) {
        if (m.sudahAda || !m.dipilih) continue;
        await api.buatMenu({ nama: m.nama.trim(), alias: [], harga: Number(m.harga), stok_harian: null, aktif: true, resep: [] });
        // Tandai tersimpan satu per satu supaya "Coba lagi" setelah galat tidak membuat menu dobel.
        ubahMenu(i, { sudahAda: true });
        n++;
      }
      if (n) {
        await muatKatalog();
        toast(`${n} menu disimpan ke Katalog`);
      }
      setMenuTersimpan(n > 0);
      setLangkah(2);
    } catch (e) {
      setGalat(jadiGalat(e));
    } finally {
      setJalan(false);
    }
  }

  async function proses() {
    if (!isi) return;
    setJalan(true);
    setGalat(null);
    try {
      const r = await api.imporHarian(isi);
      setHasil(r);
      await muatBatch();
      dataBerubah();
    } catch (e) {
      setGalat(jadiGalat(e));
    } finally {
      setJalan(false);
    }
  }

  function ubahMenu(i: number, patch: Partial<BarisMenu>) {
    setMenu((lama) => lama.map((m, j) => (j === i ? { ...m, ...patch } : m)));
  }

  return (
    <div className="tumpuk halaman-sempit">
      <Kepala judul="Masukkan chat" sub={`Langkah ${langkah + 1} dari 3: ${LANGKAH[langkah]}`} kembali="#/" />

      <ol className="wizard-langkah" aria-label="Langkah memasukkan chat">
        {LANGKAH.map((l, i) => (
          <li key={l} className={i === langkah ? "aktif" : i < langkah ? "selesai" : ""} aria-current={i === langkah ? "step" : undefined}>
            <span className="wizard-no" aria-hidden="true">
              {i < langkah ? <Icon nama="centang" ukuran={16} /> : i + 1}
            </span>
            <span>
              {l}
              {i < langkah && <span className="sr"> (sudah)</span>}
            </span>
          </li>
        ))}
      </ol>

      {langkah === 0 && (
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
              <label htmlFor="teks-chat-harian">Tempel chat grup di sini</label>
              <textarea
                id="teks-chat-harian"
                rows={9}
                value={teks}
                onChange={(e) => setTeks(e.target.value)}
                placeholder={"14/11/26 09.15 - Bu Rina: nasi ayam 2 ya, kirim jam 11.30\n14/11/26 09.17 - Pak Anton: 1 porsi aja kak"}
                aria-describedby="bantu-tempel-harian"
              />
              <p id="bantu-tempel-harian" className="bantu">
                Boleh chat beberapa hari sekaligus. Pesanan nanti dipisah per hari.
              </p>
            </div>
          ) : (
            <div role="tabpanel" className="zona-lepas">
              <Icon nama={berkas ? "berkas" : "impor"} ukuran={36} />
              {berkas ? (
                <strong className="putus-kata">{berkas.name}</strong>
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
                aria-label="Berkas ekspor chat"
                onChange={(e) => {
                  pilihBerkas(e.target.files?.[0]);
                  e.target.value = "";
                }}
              />
            </div>
          )}
          <Tombol varian="utama" besar penuh ikon="kanan" memuat={jalan} disabled={!isi} onClick={bacaPratinjau}>
            {jalan ? "Sedang membaca chat…" : "Lanjut"}
          </Tombol>
          <p className="redup kecil tengah">
            <a href="#/impor">Impor ke hari tertentu (lanjutan)</a>
          </p>
        </Kaca>
      )}

      {langkah === 1 && pratinjau && (
        <>
          <Kaca className="kartu">
            <h2>Yang terbaca dari chat</h2>
            <dl className="dl-rapi">
              <dt>Penjual</dt>
              <dd>{pratinjau.penjual ?? "Belum terdeteksi"}</dd>
              <dt>Tanggal</dt>
              <dd>
                {pratinjau.tanggal_awal ? tanggalPanjang(pratinjau.tanggal_awal) : "-"}
                {pratinjau.tanggal_akhir && pratinjau.tanggal_akhir !== pratinjau.tanggal_awal ? ` s.d. ${tanggalPanjang(pratinjau.tanggal_akhir)}` : ""}
              </dd>
              <dt>Jumlah pesan</dt>
              <dd>{pratinjau.jumlah_pesan}</dd>
            </dl>
            {pratinjau.hari.length > 0 && (
              <ul className="wizard-hari" aria-label="Pesan per hari">
                {pratinjau.hari.map((h) => (
                  <li key={h.tanggal} className="lencana nada-abu">
                    <Icon nama="kalender" ukuran={15} /> {tanggalPendek(h.tanggal)}: {h.jumlah_pesan} pesan
                  </li>
                ))}
              </ul>
            )}
          </Kaca>

          <Kaca className="kartu">
            <h2>Menu dan harga</h2>
            <p className="bantu">Cek nama dan harga. Harga ini yang dipakai menghitung total, AI tidak menentukan harga.</p>
            {menu.length === 0 ? (
              <div className="kartu-ajak nada-kuning" role="note">
                <Icon nama="peringatan" />
                <span>
                  Menu belum terbaca dari chat. Tambahkan menu di bawah, atau lanjut saja bila menu sudah ada di Katalog.
                </span>
              </div>
            ) : (
              <ul className="wizard-menu">
                {menu.map((m, i) =>
                  m.sudahAda ? (
                    <li key={i} className="wizard-menu-ada">
                      <span>
                        <strong>{m.nama}</strong> <span className="redup">{m.harga ? rupiah(Number(m.harga)) : ""}</span>
                      </span>
                      <span className="lencana nada-hijau">
                        <Icon nama="centang" ukuran={16} /> Sudah di Katalog
                      </span>
                    </li>
                  ) : (
                    <li key={i} className={`wizard-menu-baru${m.dipilih ? "" : " tidak-dipilih"}`}>
                      <label className="wizard-centang">
                        <input type="checkbox" checked={m.dipilih} onChange={(e) => ubahMenu(i, { dipilih: e.target.checked })} />
                        <span>Simpan {m.nama || "menu ini"} ke Katalog</span>
                      </label>
                      <div className="isian">
                        <label htmlFor={`menu-nama-${i}`}>Nama menu</label>
                        <input id={`menu-nama-${i}`} value={m.nama} onChange={(e) => ubahMenu(i, { nama: e.target.value })} />
                      </div>
                      <div className="isian">
                        <label htmlFor={`menu-harga-${i}`}>Harga (Rp) untuk {m.nama || "menu ini"}</label>
                        <input
                          id={`menu-harga-${i}`}
                          inputMode="numeric"
                          value={m.harga}
                          aria-invalid={(m.dipilih && !hargaValid(m.harga)) || undefined}
                          onChange={(e) => ubahMenu(i, { harga: e.target.value.replace(/\D/g, "") })}
                        />
                      </div>
                      {m.dariPembeli ? (
                        <p className="wizard-menu-pembeli">
                          <span className="lencana nada-kuning">
                            <Icon nama="chat" ukuran={16} /> Disebut pembeli, belum ada di daftar menu
                          </span>
                          <span className="redup kecil">
                            {m.dariPembeli.jumlah}× di chat, mis. “{m.dariPembeli.contoh}”. Centang kalau memang menu Anda yang lupa ditambahkan.
                          </span>
                        </p>
                      ) : (
                        <span className="lencana nada-kuning">
                          <Icon nama="tambah" ukuran={16} /> Menu baru
                        </span>
                      )}
                    </li>
                  ),
                )}
              </ul>
            )}
            <Tombol className="tombol-papan" varian="hantu" ikon="tambah" onClick={() => setMenu((lama) => [...lama, { nama: "", harga: "", sudahAda: false, dipilih: true }])}>
              Tambah menu
            </Tombol>
            {!menuBaruValid && <p className="bantu teks-kuning">Isi nama dan harga (angka lebih dari 0) untuk setiap menu yang dicentang, atau hapus centangnya.</p>}
            <div className="baris-tombol">
              <Tombol className="tombol-papan" ikon="kiri" disabled={jalan} onClick={() => setLangkah(0)}>
                Kembali
              </Tombol>
              <Tombol className="tombol-papan" varian="utama" ikon="centang" memuat={jalan} disabled={!menuBaruValid} onClick={simpanMenu}>
                Simpan menu & lanjut
              </Tombol>
            </div>
          </Kaca>
        </>
      )}

      {langkah === 2 && (
        <Kaca className="kartu">
          {!hasil ? (
            <>
              <h2>Proses pesanan</h2>
              <p>
                {menuTersimpan ? "Menu siap. " : ""}AI akan membaca chat per hari dan menyusun pesanan. Harga dan total dihitung dari Katalog Anda.
              </p>
              <Tombol varian="utama" besar penuh ikon="impor" memuat={jalan} onClick={proses}>
                {jalan ? "Sedang diproses…" : "Proses chat"}
              </Tombol>
              {jalan && (
                <div className="proses" role="status">
                  <p>
                    <strong>AI sedang membaca chat per hari…</strong> Bisa sampai satu menit, jangan tutup halaman ini.
                  </p>
                  <ul>
                    <li>Memecah chat per hari dan per pengirim</li>
                    <li>Menyamarkan nomor telepon</li>
                    <li>AI memahami isi pesanan (tanpa harga)</li>
                    <li>Harga dan total dihitung dari Katalog</li>
                  </ul>
                </div>
              )}
            </>
          ) : (
            <div role="status" aria-live="polite" className="tumpuk">
              <div className="hasil-kepala">
                <span className="bulat-sukses">
                  <Icon nama="centang" ukuran={28} />
                </span>
                <div>
                  <h2>Chat berhasil dibaca</h2>
                  <p className="redup">
                    {hasil.total.pesanan_dibuat} pesanan baru, {hasil.total.perlu_cek} perlu dicek, {hasil.total.pesan_dilewati} pesan dilewati.
                  </p>
                </div>
              </div>
              <ul className="wizard-hari-hasil">
                {hasil.hari.map((h) => (
                  <li key={h.batch_id}>
                    <strong>{h.nama}</strong>
                    <span className="redup kecil">
                      {h.pesanan_dibuat} pesanan baru · {h.perlu_cek} perlu dicek
                    </span>
                  </li>
                ))}
              </ul>
              {/* Menu yang dipesan pembeli tapi tidak ada di katalog: baru diketahui setelah AI membaca pesanan. */}
              <MenuBelumDikenal tertanam />
              <Tombol varian="utama" besar penuh ikon="beranda" onClick={() => pergi("/")}>
                Lihat papan pesanan
              </Tombol>
            </div>
          )}
        </Kaca>
      )}

      {galat &&
        (galat.kode === "katalog_kosong" ? (
          <Galat galat={galat}>
            <a href="#/katalog" className="tombol tombol-utama tombol-papan">
              <Icon nama="katalog" /> Buka Katalog
            </a>
          </Galat>
        ) : (
          <Galat galat={galat} ulang={langkah === 0 ? (isi ? bacaPratinjau : undefined) : langkah === 1 ? simpanMenu : proses} />
        ))}
      {galat?.kode === "impor_bentrok" && <p className="bantu">Proses sebelumnya masih berjalan. Tunggu beberapa detik lalu coba lagi.</p>}
    </div>
  );
}
