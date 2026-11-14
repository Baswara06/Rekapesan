import { useState, type FormEvent } from "react";
import { Icon } from "../components/Icon";
import { Dialog, Kaca, Kepala, Konfirmasi, Kosong, Tombol } from "../components/ui";
import { api, ApiError, type Product, type ProductIn, type Resep } from "../lib/api";
import { angka, pisahAlias, rupiah } from "../lib/format";
import { useApp } from "../lib/store";

export default function Katalog() {
  const { katalog, muatKatalog, toast } = useApp();
  const [edit, setEdit] = useState<Product | "baru" | null>(null);
  const [nonaktif, setNonaktif] = useState<Product | null>(null);
  const [lihatNonaktif, setLihatNonaktif] = useState(false);

  const aktif = katalog.filter((p) => p.aktif);
  const mati = katalog.filter((p) => !p.aktif);

  return (
    <div className="tumpuk">
      <Kepala
        judul="Katalog menu"
        sub="Harga hanya disimpan di sini. AI tidak pernah melihat atau mengubah harga."
        kembali="#/lainnya"
      />
      <Tombol varian="utama" ikon="tambah" besar penuh onClick={() => setEdit("baru")}>
        Tambah menu
      </Tombol>

      {aktif.length === 0 ? (
        <Kaca className="kartu">
          <Kosong ikon="katalog" judul="Katalog masih kosong">
            <p>Tambahkan menu yang dijual, beserta nama panggilan yang biasa dipakai pembeli (mis. "aybak").</p>
          </Kosong>
        </Kaca>
      ) : (
        <ul className="daftar-menu">
          {aktif.map((p) => (
            <li key={p.id}>
              <KartuMenu p={p} ubah={() => setEdit(p)} matikan={() => setNonaktif(p)} />
            </li>
          ))}
        </ul>
      )}

      {mati.length > 0 && (
        <details className="lipat" open={lihatNonaktif} onToggle={(e) => setLihatNonaktif((e.target as HTMLDetailsElement).open)}>
          <summary>
            <Icon nama="info" /> Menu nonaktif ({mati.length})
          </summary>
          <ul className="daftar-menu">
            {mati.map((p) => (
              <li key={p.id}>
                <Kaca className="kartu kartu-menu redup-kartu">
                  <div className="menu-kepala">
                    <h2>{p.nama}</h2>
                    <span className="harga">{rupiah(p.harga)}</span>
                  </div>
                  <Tombol
                    ikon="ulang"
                    onClick={async () => {
                      try {
                        await api.ubahMenu(p.id, { aktif: true });
                        await muatKatalog();
                        toast(`${p.nama} aktif lagi.`);
                      } catch (e) {
                        toast(e instanceof ApiError ? e.message : "Gagal.", "galat");
                      }
                    }}
                  >
                    Aktifkan lagi
                  </Tombol>
                </Kaca>
              </li>
            ))}
          </ul>
        </details>
      )}

      <FormMenu target={edit} tutup={() => setEdit(null)} />
      <Konfirmasi
        buka={!!nonaktif}
        tutup={() => setNonaktif(null)}
        judul={`Nonaktifkan ${nonaktif?.nama ?? ""}?`}
        pesan={<p>Menu tidak dihapus karena pesanan lama masih memakainya. Pesanan baru untuk menu ini akan diberi tanda kuning.</p>}
        labelYa="Ya, nonaktifkan"
        bahaya
        aksi={async () => {
          if (!nonaktif) return;
          try {
            await api.nonaktifkanMenu(nonaktif.id);
            await muatKatalog();
            toast(`${nonaktif.nama} dinonaktifkan.`, "info");
          } catch (e) {
            toast(e instanceof ApiError ? e.message : "Gagal.", "galat");
          }
        }}
      />
    </div>
  );
}

function KartuMenu({ p, ubah, matikan }: { p: Product; ubah: () => void; matikan: () => void }) {
  return (
    <Kaca as="article" className="kartu kartu-menu">
      <div className="menu-kepala">
        <h2>{p.nama}</h2>
        <span className="harga">{rupiah(p.harga)}</span>
      </div>
      <p className="menu-stok">
        <Icon nama="katalog" ukuran={16} /> {p.stok_harian == null ? "Stok tidak dibatasi" : `Stok ${p.stok_harian} porsi per PO`}
      </p>
      {p.alias.length > 0 && (
        <p className="menu-alias">
          <span className="sr">Nama panggilan: </span>
          {p.alias.map((a) => (
            <span key={a} className="tag">
              {a}
            </span>
          ))}
        </p>
      )}
      {p.resep.length > 0 && (
        <p className="redup kecil">Resep: {p.resep.map((r) => `${r.bahan} ${angka(r.jumlah)} ${r.satuan}`).join(", ")}</p>
      )}
      <div className="baris-tombol">
        <Tombol ikon="ubah" onClick={ubah} aria-label={`Ubah ${p.nama}`}>
          Ubah
        </Tombol>
        <Tombol varian="hantu" ikon="hapus" className="teks-bahaya" onClick={matikan} aria-label={`Nonaktifkan ${p.nama}`}>
          Nonaktifkan
        </Tombol>
      </div>
    </Kaca>
  );
}

type ResepBaris = { bahan: string; jumlah: string; satuan: string };

function FormMenu({ target, tutup }: { target: Product | "baru" | null; tutup: () => void }) {
  const lama = target && target !== "baru" ? target : null;
  return (
    <Dialog buka={!!target} tutup={tutup} judul={lama ? `Ubah ${lama.nama}` : "Menu baru"} lembar>
      {target && <IsiFormMenu key={lama?.id ?? "baru"} lama={lama} tutup={tutup} />}
    </Dialog>
  );
}

function IsiFormMenu({ lama, tutup }: { lama: Product | null; tutup: () => void }) {
  const { muatKatalog, toast } = useApp();
  const [nama, setNama] = useState(lama?.nama ?? "");
  const [alias, setAlias] = useState(lama?.alias.join(", ") ?? "");
  const [harga, setHarga] = useState(lama ? String(lama.harga) : "");
  const [batasStok, setBatasStok] = useState(lama ? lama.stok_harian != null : true);
  const [stok, setStok] = useState(lama?.stok_harian != null ? String(lama.stok_harian) : "");
  const [resep, setResep] = useState<ResepBaris[]>(lama?.resep.map((r) => ({ bahan: r.bahan, jumlah: String(r.jumlah), satuan: r.satuan })) ?? []);
  const [jalan, setJalan] = useState(false);
  const [galat, setGalat] = useState("");

  async function simpan(e: FormEvent) {
    e.preventDefault();
    setGalat("");
    const h = Number(harga.replace(/\D/g, ""));
    if (!nama.trim() || !harga || Number.isNaN(h)) return setGalat("Nama dan harga wajib diisi.");
    const resepBersih: Resep[] = [];
    for (const r of resep) {
      if (!r.bahan.trim() && !r.jumlah && !r.satuan.trim()) continue;
      const j = Number(r.jumlah.replace(",", "."));
      if (!r.bahan.trim() || !r.satuan.trim() || !(j > 0)) return setGalat("Setiap bahan resep perlu nama, jumlah lebih dari 0, dan satuan.");
      resepBersih.push({ bahan: r.bahan.trim(), jumlah: j, satuan: r.satuan.trim() });
    }
    const data: ProductIn = {
      nama: nama.trim(),
      alias: pisahAlias(alias),
      harga: h,
      stok_harian: batasStok && stok !== "" ? Number(stok) : null,
      aktif: lama?.aktif ?? true,
      resep: resepBersih,
    };
    setJalan(true);
    try {
      if (lama) await api.ubahMenu(lama.id, data);
      else await api.buatMenu(data);
      await muatKatalog();
      toast(lama ? "Menu diperbarui." : "Menu ditambahkan.");
      tutup();
    } catch (err) {
      setGalat(err instanceof ApiError ? err.message : "Gagal menyimpan menu.");
    } finally {
      setJalan(false);
    }
  }

  return (
    <form onSubmit={simpan} className="formulir">
      <div className="isian">
        <label htmlFor="m-nama">Nama menu</label>
        <input id="m-nama" value={nama} onChange={(e) => setNama(e.target.value)} placeholder="mis. Ayam Bakar" required maxLength={120} />
      </div>
      <div className="isian">
        <label htmlFor="m-harga">Harga (Rp)</label>
        <input
          id="m-harga"
          inputMode="numeric"
          value={harga ? Number(harga).toLocaleString("id-ID") : ""}
          onChange={(e) => setHarga(e.target.value.replace(/\D/g, ""))}
          placeholder="18.000"
          required
        />
      </div>
      <div className="isian">
        <label htmlFor="m-alias">Nama panggilan dari pembeli</label>
        <input id="m-alias" value={alias} onChange={(e) => setAlias(e.target.value)} placeholder="aybak, ayam bkr" aria-describedby="m-alias-bantu" />
        <p id="m-alias-bantu" className="bantu">
          Pisahkan dengan koma. Membantu AI mengenali tulisan singkat di chat.
        </p>
      </div>
      <label className="sakelar">
        <input type="checkbox" checked={batasStok} onChange={(e) => setBatasStok(e.target.checked)} />
        <span className="sakelar-tuas" aria-hidden="true" />
        Batasi stok per PO
      </label>
      {batasStok && (
        <div className="isian">
          <label htmlFor="m-stok">Stok (porsi)</label>
          <input id="m-stok" inputMode="numeric" value={stok} onChange={(e) => setStok(e.target.value.replace(/\D/g, ""))} placeholder="30" />
        </div>
      )}

      <fieldset className="resep">
        <legend>Resep per porsi (untuk daftar belanja)</legend>
        {resep.map((r, i) => (
          <div key={i} className="resep-baris">
            <input aria-label={`Bahan ${i + 1}`} placeholder="Ayam" value={r.bahan} onChange={(e) => setResep((rs) => rs.map((x, j) => (j === i ? { ...x, bahan: e.target.value } : x)))} />
            <input
              aria-label={`Jumlah bahan ${i + 1}`}
              placeholder="0,25"
              inputMode="decimal"
              value={r.jumlah}
              onChange={(e) => setResep((rs) => rs.map((x, j) => (j === i ? { ...x, jumlah: e.target.value } : x)))}
            />
            <input aria-label={`Satuan bahan ${i + 1}`} placeholder="kg" value={r.satuan} onChange={(e) => setResep((rs) => rs.map((x, j) => (j === i ? { ...x, satuan: e.target.value } : x)))} />
            <button type="button" className="tombol tombol-hantu tombol-ikon teks-bahaya" onClick={() => setResep((rs) => rs.filter((_, j) => j !== i))} aria-label={`Hapus bahan ${i + 1}`}>
              <Icon nama="hapus" />
            </button>
          </div>
        ))}
        <Tombol ikon="tambah" onClick={() => setResep((rs) => [...rs, { bahan: "", jumlah: "", satuan: "" }])}>
          Tambah bahan
        </Tombol>
      </fieldset>

      {galat && (
        <p className="teks-galat" role="alert">
          <Icon nama="peringatan" ukuran={18} /> {galat}
        </p>
      )}
      <Tombol type="submit" varian="utama" besar penuh memuat={jalan}>
        Simpan menu
      </Tombol>
    </form>
  );
}
