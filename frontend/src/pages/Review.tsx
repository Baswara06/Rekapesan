import { useMemo, useState } from "react";
import { PilihBatch } from "../components/Batch";
import { Icon } from "../components/Icon";
import { KartuPesanan } from "../components/KartuPesanan";
import { Galat, Kaca, Kepala, Konfirmasi, Kosong, Memuat, Tombol } from "../components/ui";
import { api, ApiError, type Order, type StatusPesanan } from "../lib/api";
import { rupiah } from "../lib/format";
import type { Rute } from "../lib/router";
import { useApp, useMuat } from "../lib/store";

type Saring = "perlu_cek" | "disetujui" | "batal" | "semua";

const SARING: { id: Saring; label: string; cocok: (s: StatusPesanan) => boolean }[] = [
  { id: "perlu_cek", label: "Perlu dicek", cocok: (s) => s === "perlu_cek" },
  { id: "disetujui", label: "Disetujui", cocok: (s) => s === "dikonfirmasi" || s === "dibayar" || s === "dikirim" },
  { id: "batal", label: "Batal", cocok: (s) => s === "batal" },
  { id: "semua", label: "Semua", cocok: () => true },
];

export default function Review({ rute }: { rute: Rute }) {
  const { batchAktif, batches, versiData, dataBerubah, toast } = useApp();
  const [saring, setSaring] = useState<Saring>((rute.query.get("saring") as Saring) || "perlu_cek");
  const [hanyaBertanda, setHanyaBertanda] = useState(false);
  const [akanDitolak, setAkanDitolak] = useState<Order | null>(null);
  const [konfirmasiSemua, setKonfirmasiSemua] = useState(false);
  const pesanan = useMuat(batchAktif ? () => api.daftarPesanan(batchAktif.id) : null, [batchAktif?.id, versiData]);

  const semua = pesanan.data ?? [];
  const jumlah = useMemo(() => Object.fromEntries(SARING.map((s) => [s.id, semua.filter((o) => s.cocok(o.status)).length])), [semua]);
  const bersih = semua.filter((o) => o.status === "perlu_cek" && o.tanda.length === 0);
  const tampil = semua
    .filter((o) => SARING.find((s) => s.id === saring)!.cocok(o.status))
    .filter((o) => !hanyaBertanda || o.tanda.length > 0)
    // Pesanan bertanda kuning didahulukan supaya penjual melihat yang meragukan lebih dulu.
    .sort((a, b) => Number(b.tanda.length > 0) - Number(a.tanda.length > 0));

  function ganti(o: Order) {
    pesanan.setData((d) => d?.map((x) => (x.id === o.id ? o : x)) ?? null);
    dataBerubah();
  }

  async function setujui(o: Order) {
    try {
      ganti(await api.setujui(o.id));
      toast(`Pesanan ${o.customer.nama_tampil} disetujui.`);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Gagal menyetujui.", "galat");
    }
  }

  async function tolak(o: Order) {
    try {
      ganti(await api.tolak(o.id));
      toast(`Pesanan ${o.customer.nama_tampil} ditolak.`, "info");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Gagal menolak.", "galat");
    }
  }

  async function setujuiBersih() {
    if (!batchAktif) return;
    try {
      const r = await api.setujuiYangBersih(batchAktif.id);
      toast(`${r.disetujui} pesanan disetujui. ${r.masih_bertanda} masih perlu dicek.`);
      pesanan.muatUlang();
      dataBerubah();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Gagal menyetujui.", "galat");
    }
  }

  return (
    <div className="tumpuk">
      <Kepala judul="Cek pesanan" sub="Langkah 2 dari 3. AI hanya menyarankan, Anda yang memutuskan." />
      {batches.length === 0 ? <PilihBatch /> : <PilihBatch ringkas />}

      {batchAktif && (
        <>
          <div className="saring" role="tablist" aria-label="Saring pesanan">
            {SARING.map((s) => (
              <button
                key={s.id}
                type="button"
                role="tab"
                aria-selected={saring === s.id}
                className={saring === s.id ? "aktif" : ""}
                onClick={() => setSaring(s.id)}
              >
                {s.label} <span className="saring-jumlah">{jumlah[s.id] ?? 0}</span>
              </button>
            ))}
          </div>

          {saring === "perlu_cek" && bersih.length > 0 && (
            <Kaca className="kartu kartu-aksi-massal">
              <div>
                <strong>{bersih.length} pesanan tanpa tanda kuning</strong>
                <p className="redup kecil">
                  Total {rupiah(bersih.reduce((a, o) => a + o.total, 0))}. Yang bertanda kuning tetap menunggu Anda.
                </p>
              </div>
              <Tombol varian="sukses" ikon="centang" onClick={() => setKonfirmasiSemua(true)}>
                Setujui semua yang bersih
              </Tombol>
            </Kaca>
          )}

          {semua.some((o) => o.tanda.length > 0) && (
            <label className="sakelar">
              <input type="checkbox" checked={hanyaBertanda} onChange={(e) => setHanyaBertanda(e.target.checked)} />
              <span className="sakelar-tuas" aria-hidden="true" />
              Tampilkan hanya yang bertanda kuning
            </label>
          )}

          {pesanan.memuat && !pesanan.data ? (
            <Memuat label="Memuat pesanan" />
          ) : pesanan.galat ? (
            <Galat galat={pesanan.galat} ulang={pesanan.muatUlang} />
          ) : tampil.length === 0 ? (
            semua.length === 0 ? (
              <Kaca className="kartu">
                <Kosong ikon="impor" judul="Belum ada pesanan">
                  <p>Masukkan chat grup dulu, nanti pesanannya muncul di sini.</p>
                  <a href="#/impor" className="tombol tombol-utama tombol-besar">
                    <Icon nama="impor" />
                    <span>Masukkan chat</span>
                  </a>
                </Kosong>
              </Kaca>
            ) : saring === "perlu_cek" ? (
              <Kaca className="kartu">
                <Kosong ikon="centang" judul="Semua sudah dicek">
                  <p>Tidak ada pesanan yang menunggu. Rekap sudah lengkap.</p>
                  <a href="#/rekap" className="tombol tombol-utama tombol-besar">
                    <Icon nama="rekap" />
                    <span>Lihat rekap</span>
                  </a>
                </Kosong>
              </Kaca>
            ) : (
              <p className="redup tengah">Tidak ada pesanan di bagian ini.</p>
            )
          ) : (
            <div className="daftar-pesanan">
              {tampil.map((o) => (
                <KartuPesanan key={o.id} order={o} setujui={setujui} tolak={setAkanDitolak} />
              ))}
            </div>
          )}
        </>
      )}

      <Konfirmasi
        buka={!!akanDitolak}
        tutup={() => setAkanDitolak(null)}
        judul="Tolak pesanan ini?"
        pesan={
          <p>
            Pesanan <strong>{akanDitolak?.customer.nama_tampil}</strong> akan ditandai batal dan tidak masuk rekap. Masih bisa dibuka lagi
            dari bagian "Batal".
          </p>
        }
        labelYa="Ya, tolak"
        bahaya
        aksi={() => (akanDitolak ? tolak(akanDitolak) : undefined)}
      />
      <Konfirmasi
        buka={konfirmasiSemua}
        tutup={() => setKonfirmasiSemua(false)}
        judul={`Setujui ${bersih.length} pesanan?`}
        pesan={<p>Hanya pesanan tanpa tanda kuning yang disetujui. Pesanan yang meragukan tetap menunggu Anda cek satu per satu.</p>}
        labelYa="Ya, setujui"
        aksi={setujuiBersih}
      />
    </div>
  );
}
