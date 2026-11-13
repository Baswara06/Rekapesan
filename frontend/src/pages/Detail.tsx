import { useEffect, useState } from "react";
import { Icon } from "../components/Icon";
import { GelembungChat, Perubahan } from "../components/KartuPesanan";
import {
  ChipTanda,
  Galat,
  Kaca,
  Kepala,
  Konfirmasi,
  LencanaStatus,
  Memuat,
  salinTeks,
  Stepper,
  tautanWhatsApp,
  Tombol,
} from "../components/ui";
import { api, ApiError, type Order, type OrderPatch, type ProofSuggestion, type StatusPesanan } from "../lib/api";
import { PINDAH_STATUS, rupiah, STATUS } from "../lib/format";
import { useApp, useMuat } from "../lib/store";

type BarisItem = { kunci: string; product_id: string | null; teks_asli: string; qty: number | null; catatan_item: string };

let urut = 0;
const kunciBaru = () => `b${++urut}`;

function keBaris(o: Order): BarisItem[] {
  return o.items.map((it) => ({
    kunci: it.id ?? kunciBaru(),
    product_id: it.product_id,
    teks_asli: it.teks_asli,
    qty: it.qty,
    catatan_item: it.catatan_item ?? "",
  }));
}

const LABEL_PINDAH: Record<StatusPesanan, { label: string; ikon: "centang" | "ulang" | "tutup" | "truk"; varian: "sukses" | "kedua" | "bahaya" }> = {
  dikonfirmasi: { label: "Setujui", ikon: "centang", varian: "sukses" },
  perlu_cek: { label: "Kembalikan ke perlu dicek", ikon: "ulang", varian: "kedua" },
  batal: { label: "Batalkan pesanan", ikon: "tutup", varian: "bahaya" },
  dikirim: { label: "Tandai sudah dikirim", ikon: "truk", varian: "kedua" },
  dibayar: { label: "Sudah bayar", ikon: "centang", varian: "kedua" },
};

export default function Detail({ id }: { id: string }) {
  const { katalog, katalogMap, dataBerubah, toast } = useApp();
  const muat = useMuat(() => api.pesanan(id), [id]);
  const order = muat.data;

  const [baris, setBaris] = useState<BarisItem[]>([]);
  const [jam, setJam] = useState("");
  const [alamat, setAlamat] = useState("");
  const [catatan, setCatatan] = useState("");
  const [simpan, setSimpan] = useState(false);
  const [galatForm, setGalatForm] = useState("");
  const [pindahKe, setPindahKe] = useState<StatusPesanan | null>(null);

  useEffect(() => {
    if (!order) return;
    setBaris(keBaris(order));
    setJam(order.jam_kirim ?? "");
    setAlamat(order.alamat ?? "");
    setCatatan(order.catatan ?? "");
  }, [order]);

  if (muat.memuat && !order) return <Memuat label="Memuat pesanan" />;
  if (muat.galat || !order)
    return (
      <div className="tumpuk">
        <Kepala judul="Detail pesanan" kembali="#/cek" />
        <Galat galat={muat.galat ?? new Error("Pesanan tidak ditemukan.")} ulang={muat.muatUlang} />
      </div>
    );

  const bisaUbah = order.status !== "dikirim" && order.status !== "batal";
  const menuAktif = katalog.filter((p) => p.aktif);

  const itemBerubah =
    JSON.stringify(baris.map(({ kunci: _k, ...r }) => ({ ...r, catatan_item: r.catatan_item || null }))) !==
    JSON.stringify(order.items.map((it) => ({ product_id: it.product_id, teks_asli: it.teks_asli, qty: it.qty, catatan_item: it.catatan_item ?? null })));
  const berubah = itemBerubah || jam !== (order.jam_kirim ?? "") || alamat !== (order.alamat ?? "") || catatan !== (order.catatan ?? "");

  function perbarui(o: Order) {
    muat.setData(o);
    dataBerubah();
  }

  async function simpanUbahan() {
    if (!order) return;
    setGalatForm("");
    if (baris.some((b) => !b.teks_asli.trim())) {
      setGalatForm("Setiap item perlu menu atau tulisan.");
      return;
    }
    const patch: OrderPatch = {};
    if (itemBerubah)
      patch.items = baris.map((b) => ({
        product_id: b.product_id,
        teks_asli: b.teks_asli.trim(),
        qty: b.qty,
        catatan_item: b.catatan_item.trim() || null,
      }));
    if (jam !== (order.jam_kirim ?? "")) patch.jam_kirim = jam.trim() || null;
    if (alamat !== (order.alamat ?? "")) patch.alamat = alamat.trim() || null;
    if (catatan !== (order.catatan ?? "")) patch.catatan = catatan.trim() || null;
    setSimpan(true);
    try {
      perbarui(await api.ubahPesanan(order.id, patch));
      toast("Perubahan disimpan. Total dan tanda dihitung ulang.");
    } catch (e) {
      setGalatForm(e instanceof ApiError ? e.message : "Gagal menyimpan.");
    } finally {
      setSimpan(false);
    }
  }

  async function pindahStatus(ke: StatusPesanan) {
    if (!order) return;
    try {
      let o: Order;
      if (ke === "dikonfirmasi" && order.status === "perlu_cek") o = await api.setujui(order.id);
      else if (ke === "batal" && order.status === "perlu_cek") o = await api.tolak(order.id);
      else o = await api.ubahPesanan(order.id, { status: ke });
      perbarui(o);
      toast(`Status menjadi "${STATUS[o.status].label}".`);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Gagal mengubah status.", "galat");
    }
  }

  function ubahBaris(kunci: string, ubah: Partial<BarisItem>) {
    setBaris((bs) => bs.map((b) => (b.kunci === kunci ? { ...b, ...ubah } : b)));
  }

  return (
    <div className="tumpuk dengan-bilah">
      <Kepala judul={order.customer.nama_tampil} sub={<LencanaStatus status={order.status} />} kembali="#/cek" />

      <div className="kisi-detail">
      <div className="kolom">
      <Kaca className="kartu kartu-total">
        <span className="label-kecil">Total dihitung dari katalog</span>
        <strong className="total-besar">{rupiah(order.total)}</strong>
        {order.tanda.length > 0 && (
          <div className="baris-tanda">
            {order.tanda.map((t) => (
              <ChipTanda key={t} kode={t} rinci />
            ))}
          </div>
        )}
      </Kaca>

      {order.perubahan.sebelum && <Perubahan sebelum={order.perubahan.sebelum} sesudah={order.perubahan.sesudah} katalog={katalogMap} />}

      <Kaca className="kartu">
        <h2 className="judul-kartu">
          <Icon nama="chat" /> Chat asli
        </h2>
        <GelembungChat pesan={order.pesan_sumber} />
      </Kaca>
      </div>

      <div className="kolom">
      <Kaca className="kartu">
        <h2 className="judul-kartu">
          <Icon nama="ubah" /> Isi pesanan
        </h2>
        {!bisaUbah && <p className="redup">Pesanan {STATUS[order.status].label.toLowerCase()} tidak bisa diubah.</p>}
        <fieldset disabled={!bisaUbah} className="formulir">
          <legend className="sr">Item pesanan</legend>
          <ul className="edit-item-daftar">
            {baris.map((b, i) => {
              const tidakDikenal = !b.product_id || !katalogMap.has(b.product_id);
              return (
                <li key={b.kunci} className={`edit-item ${tidakDikenal ? "item-asing" : ""}`}>
                  <div className="isian">
                    <label htmlFor={`menu-${b.kunci}`}>Menu {i + 1}</label>
                    <div className="pilih-wrap">
                      <select
                        id={`menu-${b.kunci}`}
                        value={b.product_id ?? ""}
                        onChange={(e) => {
                          const pid = e.target.value || null;
                          const p = pid ? katalogMap.get(pid) : undefined;
                          ubahBaris(b.kunci, { product_id: pid, teks_asli: b.teks_asli || p?.nama || "" });
                        }}
                      >
                        <option value="">- Tidak ada di katalog -</option>
                        {menuAktif.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.nama} ({rupiah(p.harga)})
                          </option>
                        ))}
                      </select>
                      <Icon nama="bawah" className="pilih-panah" />
                    </div>
                    {b.teks_asli && <p className="bantu">Tulisan pembeli: "{b.teks_asli}"</p>}
                  </div>
                  <div className="edit-item-bawah">
                    <Stepper label={`Jumlah menu ${i + 1}`} nilai={b.qty} ubah={(n) => ubahBaris(b.kunci, { qty: n })} />
                    <Tombol
                      varian="hantu"
                      ikon="hapus"
                      className="teks-bahaya"
                      onClick={() => setBaris((bs) => bs.filter((x) => x.kunci !== b.kunci))}
                      aria-label={`Hapus menu ${i + 1}`}
                    >
                      Hapus
                    </Tombol>
                  </div>
                  <div className="isian">
                    <label htmlFor={`cat-${b.kunci}`}>Catatan menu (opsional)</label>
                    <input
                      id={`cat-${b.kunci}`}
                      value={b.catatan_item}
                      onChange={(e) => ubahBaris(b.kunci, { catatan_item: e.target.value })}
                      placeholder="mis. pedas, tanpa sambal"
                    />
                  </div>
                </li>
              );
            })}
          </ul>
          <Tombol
            ikon="tambah"
            penuh
            disabled={menuAktif.length === 0}
            onClick={() => {
              const p = menuAktif[0];
              setBaris((bs) => [...bs, { kunci: kunciBaru(), product_id: p?.id ?? null, teks_asli: p?.nama ?? "", qty: 1, catatan_item: "" }]);
            }}
          >
            Tambah menu
          </Tombol>

          <div className="isian">
            <label htmlFor="jam">
              <Icon nama="jam" ukuran={18} /> Jam kirim
            </label>
            <input id="jam" value={jam} onChange={(e) => setJam(e.target.value)} placeholder="mis. 12:00 atau jam 11.30" inputMode="text" />
          </div>
          <div className="isian">
            <label htmlFor="alamat">
              <Icon nama="lokasi" ukuran={18} /> Alamat
            </label>
            <textarea id="alamat" rows={2} value={alamat} onChange={(e) => setAlamat(e.target.value)} placeholder="mis. Blok C no 4" />
          </div>
          <div className="isian">
            <label htmlFor="catatan">Catatan pesanan (opsional)</label>
            <textarea id="catatan" rows={2} value={catatan} onChange={(e) => setCatatan(e.target.value)} />
          </div>
          {galatForm && (
            <p className="teks-galat" role="alert">
              <Icon nama="peringatan" ukuran={18} /> {galatForm}
            </p>
          )}
        </fieldset>
      </Kaca>

      {PINDAH_STATUS[order.status].length > 0 && (
        <Kaca className="kartu">
          <h2 className="judul-kartu">
            <Icon nama="langkah" /> Status pesanan
          </h2>
          <div className="tumpuk-tombol">
            {PINDAH_STATUS[order.status].map((s) => (
              <Tombol key={s} varian={LABEL_PINDAH[s].varian} ikon={LABEL_PINDAH[s].ikon} penuh onClick={() => setPindahKe(s)}>
                {order.status === "batal" && s === "perlu_cek" ? "Buka lagi untuk dicek" : LABEL_PINDAH[s].label}
              </Tombol>
            ))}
          </div>
        </Kaca>
      )}

      {(order.status === "dikonfirmasi" || order.status === "dibayar" || order.status === "dikirim") && <Balasan orderId={order.id} />}

      {order.status === "dikonfirmasi" && <Pembayaran order={order} sesudahBayar={() => muat.muatUlang()} />}
      {order.status === "dibayar" && (
        <Kaca className="kartu nada-biru-lembut">
          <p className="baris-ikon">
            <Icon nama="dompet" /> <strong>Sudah bayar</strong>, dikonfirmasi oleh Anda.
          </p>
        </Kaca>
      )}

      </div>
      </div>

      {berubah && bisaUbah && (
        <div className="bilah-simpan kaca" role="region" aria-label="Simpan perubahan">
          <span>Ada perubahan belum disimpan</span>
          <div className="baris-tombol">
            <Tombol
              onClick={() => {
                setBaris(keBaris(order));
                setJam(order.jam_kirim ?? "");
                setAlamat(order.alamat ?? "");
                setCatatan(order.catatan ?? "");
                setGalatForm("");
              }}
            >
              Urungkan
            </Tombol>
            <Tombol varian="utama" ikon="centang" memuat={simpan} onClick={simpanUbahan}>
              Simpan
            </Tombol>
          </div>
        </div>
      )}

      <Konfirmasi
        buka={!!pindahKe}
        tutup={() => setPindahKe(null)}
        judul={pindahKe ? `${LABEL_PINDAH[pindahKe].label}?` : ""}
        pesan={
          <p>
            Status pesanan <strong>{order.customer.nama_tampil}</strong> berubah dari "{STATUS[order.status].label}" menjadi "
            {pindahKe ? STATUS[pindahKe].label : ""}".
            {berubah && " Perubahan isi yang belum disimpan tidak ikut tersimpan."}
          </p>
        }
        labelYa="Ya, ubah"
        bahaya={pindahKe === "batal"}
        aksi={() => (pindahKe ? pindahStatus(pindahKe) : undefined)}
      />
    </div>
  );
}

function Balasan({ orderId }: { orderId: string }) {
  const { toast } = useApp();
  const [teks, setTeks] = useState<string | null>(null);
  const [jalan, setJalan] = useState(false);

  async function buat() {
    setJalan(true);
    try {
      setTeks((await api.balasan(orderId)).teks);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Gagal membuat balasan.", "galat");
    } finally {
      setJalan(false);
    }
  }

  return (
    <Kaca className="kartu">
      <h2 className="judul-kartu">
        <Icon nama="kirim" /> Balasan konfirmasi
      </h2>
      {teks === null ? (
        <>
          <p className="redup">Pesan konfirmasi untuk pembeli, disusun dari templat (bukan AI). Total diambil dari sistem.</p>
          <Tombol ikon="chat" penuh memuat={jalan} onClick={buat}>
            Buat balasan
          </Tombol>
        </>
      ) : (
        <>
          <pre className="teks-balasan" tabIndex={0} aria-label="Isi balasan">
            {teks}
          </pre>
          <div className="baris-tombol">
            <Tombol
              ikon="salin"
              onClick={async () => toast((await salinTeks(teks)) ? "Balasan disalin." : "Gagal menyalin. Tekan lama teks untuk menyalin.", "info")}
            >
              Salin
            </Tombol>
            <a className="tombol tombol-utama" href={tautanWhatsApp(teks)} target="_blank" rel="noopener noreferrer">
              <Icon nama="kirim" />
              <span>Kirim ke WhatsApp</span>
            </a>
          </div>
        </>
      )}
    </Kaca>
  );
}

function Pembayaran({ order, sesudahBayar }: { order: Order; sesudahBayar: () => void }) {
  const { dataBerubah, toast } = useApp();
  const [saran, setSaran] = useState<ProofSuggestion | null>(null);
  const [baca, setBaca] = useState(false);
  const [galat, setGalat] = useState<ApiError | null>(null);
  const [pratinjau, setPratinjau] = useState<string | null>(null);
  const [konfirmasi, setKonfirmasi] = useState(false);

  useEffect(() => () => {
    if (pratinjau) URL.revokeObjectURL(pratinjau);
  }, [pratinjau]);

  async function unggah(f: File | undefined) {
    if (!f) return;
    setGalat(null);
    setSaran(null);
    if (f.size > 5 * 1024 * 1024) {
      setGalat(new ApiError(413, "validasi_gagal", "Gambar terlalu besar (maksimal 5 MB)."));
      return;
    }
    setPratinjau(URL.createObjectURL(f));
    setBaca(true);
    try {
      setSaran(await api.bacaBuktiBayar(order.id, f));
    } catch (e) {
      setGalat(e instanceof ApiError ? e : new ApiError(0, "galat", String(e)));
    } finally {
      setBaca(false);
    }
  }

  return (
    <Kaca className="kartu">
      <h2 className="judul-kartu">
        <Icon nama="dompet" /> Pembayaran
      </h2>
      <p className="redup">Unggah tangkapan layar transfer. AI hanya membaca nama dan nominal, Anda yang memastikan.</p>
      <label className="tombol tombol-kedua tombol-penuh">
        <Icon nama="gambar" />
        <span>{baca ? "Membaca bukti…" : "Unggah bukti bayar"}</span>
        <input type="file" accept="image/*" className="sr" onChange={(e) => unggah(e.target.files?.[0])} disabled={baca} />
      </label>
      {pratinjau && <img src={pratinjau} alt="Bukti bayar yang diunggah" className="pratinjau-bukti" />}
      {saran && (
        <div className={`saran-bayar ${saran.cocok ? "cocok" : "tidak-cocok"}`} role="status">
          <p className="baris-ikon">
            <Icon nama={saran.cocok ? "centang" : "peringatan"} />
            <strong>{saran.cocok ? "Nominal sama dengan total" : "Nominal berbeda dari total"}</strong>
          </p>
          <dl className="dl-rapi">
            <dt>Nama pengirim terbaca</dt>
            <dd>{saran.nama ?? "-"}</dd>
            <dt>Nominal terbaca</dt>
            <dd>{rupiah(saran.nominal)}</dd>
            <dt>Total pesanan</dt>
            <dd>{rupiah(order.total)}</dd>
          </dl>
        </div>
      )}
      {galat && <p className="bantu">{galat.message} Anda tetap bisa menandai sudah bayar secara manual.</p>}
      <Tombol varian="utama" ikon="centang" penuh onClick={() => setKonfirmasi(true)}>
        Tandai sudah bayar
      </Tombol>
      <Konfirmasi
        buka={konfirmasi}
        tutup={() => setKonfirmasi(false)}
        judul="Tandai sudah bayar?"
        pesan={
          <p>
            Pastikan uang {rupiah(order.total)} dari <strong>{order.customer.nama_tampil}</strong> sudah masuk ke rekening Anda.
          </p>
        }
        labelYa="Ya, sudah masuk"
        aksi={async () => {
          try {
            await api.konfirmasiBayar(order.id);
            toast("Pembayaran dicatat.");
            dataBerubah();
            sesudahBayar();
          } catch (e) {
            toast(e instanceof ApiError ? e.message : "Gagal mencatat pembayaran.", "galat");
          }
        }}
      />
    </Kaca>
  );
}
