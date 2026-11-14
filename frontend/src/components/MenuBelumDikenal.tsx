import { useState, type FormEvent } from "react";
import { api, ApiError, type MenuBelumDikenal as Item } from "../lib/api";
import { useApp, useMuat } from "../lib/store";
import { Icon } from "./Icon";
import { Tombol } from "./ui";

/**
 * Menu yang dipesan pembeli tapi belum ada di katalog (mungkin penjual lupa menambahkannya).
 * Penjual mengisi harga sendiri. Setelah ditambah, pesanan lama dicocokkan ulang oleh server dan tanda kuningnya hilang.
 */
export function MenuBelumDikenal({ tertanam = false }: { tertanam?: boolean }) {
  const { versiData, dataBerubah, muatKatalog } = useApp();
  const daftar = useMuat(() => api.menuBelumDikenal(), [versiData]);
  const item = daftar.data ?? [];
  if (item.length === 0) return null;
  return (
    <section className={tertanam ? "menu-baru menu-baru-tertanam" : "kaca kartu menu-baru"} aria-labelledby="judul-menu-baru">
      <h2 id="judul-menu-baru" className="judul-kartu">
        <Icon nama="peringatan" /> Dipesan, tapi belum ada di katalog
      </h2>
      <p className="redup kecil">Mungkin lupa ditambahkan. Isi harganya, pesanan yang memakai menu ini langsung dihitung ulang.</p>
      <ul className="menu-baru-daftar">
        {item.map((m) => (
          <BarisMenu
            key={m.kunci}
            m={m}
            selesai={async () => {
              await muatKatalog();
              dataBerubah();
            }}
          />
        ))}
      </ul>
    </section>
  );
}

function BarisMenu({ m, selesai }: { m: Item; selesai: () => Promise<void> }) {
  const { toast } = useApp();
  const [nama, setNama] = useState(m.nama);
  const [harga, setHarga] = useState("");
  const [jalan, setJalan] = useState(false);
  const [galat, setGalat] = useState("");
  const id = `menu-baru-${m.kunci.replace(/\s+/g, "-")}`;

  async function simpan(e: FormEvent) {
    e.preventDefault();
    const angka = Number(harga);
    if (!nama.trim() || !Number.isInteger(angka) || angka <= 0) {
      setGalat("Isi nama dan harga (angka lebih dari 0).");
      return;
    }
    setGalat("");
    setJalan(true);
    try {
      const r = await api.tambahMenuBelumDikenal(m.kunci, nama.trim(), angka);
      toast(`${r.menu.nama} ditambahkan. ${r.pesanan_dicocokkan} pesanan dihitung ulang.`);
      await selesai();
    } catch (err) {
      setGalat(err instanceof ApiError ? err.message : "Gagal menambahkan menu.");
    } finally {
      setJalan(false);
    }
  }

  return (
    <li>
      <form className="menu-baru-baris" onSubmit={simpan} noValidate>
        <div className="menu-baru-info">
          <label htmlFor={`${id}-nama`} className="sr">
            Nama menu
          </label>
          <input id={`${id}-nama`} value={nama} onChange={(e) => setNama(e.target.value)} maxLength={120} />
          <span className="redup kecil">
            Dipesan {m.total_porsi} porsi di {m.jumlah_pesanan} pesanan · di chat: “{m.contoh}”
          </span>
        </div>
        <div className="menu-baru-aksi">
          <label htmlFor={`${id}-harga`} className="sr">
            Harga {nama}
          </label>
          <input
            id={`${id}-harga`}
            inputMode="numeric"
            placeholder="Harga, mis. 16000"
            value={harga}
            onChange={(e) => setHarga(e.target.value.replace(/[^0-9]/g, ""))}
            aria-describedby={galat ? `${id}-galat` : undefined}
          />
          <Tombol type="submit" varian="utama" ikon="tambah" memuat={jalan}>
            Tambah ke katalog
          </Tombol>
        </div>
        {galat && (
          <p id={`${id}-galat`} className="teks-galat kecil" role="alert">
            {galat}
          </p>
        )}
      </form>
    </li>
  );
}
