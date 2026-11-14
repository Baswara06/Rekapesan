import { PilihBatch } from "../components/Batch";
import { AjakIsiNamaToko, SiapkanToko } from "../components/Toko";
import { Icon } from "../components/Icon";
import { LencanaStatus } from "../components/ui";
import { api, type Order } from "../lib/api";
import { inisial, namaMenu, rupiah, sapaan, tanggalPanjang } from "../lib/format";
import { useApp, useMuat } from "../lib/store";

const MAKS_TERBARU = 5;
const MAKS_BATANG = 7;
const MAKS_BAYAR = 3;

export default function Beranda({ perluCek }: { perluCek: number | null }) {
  const { batchAktif, batches, batchSiap, versiData, akun, katalog, katalogSiap } = useApp();
  const data = useMuat(
    batchAktif
      ? async () => {
          const [rekap, pesanan] = await Promise.all([api.rekap(batchAktif.id), api.daftarPesanan(batchAktif.id)]);
          return { rekap, pesanan };
        }
      : null,
    [batchAktif?.id, versiData],
  );
  const r = data.data?.rekap;
  const pesanan = data.data?.pesanan ?? [];
  const terbaru = [...pesanan].reverse().slice(0, MAKS_TERBARU);
  const kosong = data.galat ? "-" : "…";
  const namaToko = akun?.nama_toko ?? null;
  // Akun lama (sebelum ada kolom nama toko) diminta mengisinya. null dari server berarti memang belum diisi.
  const mintaNamaToko = !!akun && !namaToko;
  // Checklist tampil selama akun belum lengkap: belum ada menu, belum ada PO, atau PO aktif belum berisi pesanan.
  const pesananSiap = !batchAktif || !!data.data;
  const tokoLengkap = katalog.some((p) => p.aktif) && batches.length > 0 && pesanan.length > 0;
  const tampilSiapkan = batchSiap && katalogSiap && pesananSiap && !tokoLengkap;

  if (batchSiap && batches.length === 0) {
    return (
      <div className="tumpuk halaman-sempit">
        <header className="beranda-kepala">
          <div>
            <p className="label-huruf-besar">{sapaan()}</p>
            <h1>{namaToko ? `Selamat datang, ${namaToko}` : "Selamat datang di RekaPesan"}</h1>
          </div>
        </header>
        {mintaNamaToko && <AjakIsiNamaToko />}
        {katalogSiap ? <SiapkanToko adaPesanan={false} /> : <CaraKerja />}
      </div>
    );
  }

  // Grafik produksi: porsi per menu dari rekap (angka dari server), terbanyak di kiri dan disorot.
  const produksi = r ? [...r.produksi].filter((p) => p.qty > 0).sort((a, b) => b.qty - a.qty).slice(0, MAKS_BATANG) : [];
  const maksPorsi = produksi[0]?.qty ?? 0;
  // Disorot hanya bila satu menu benar-benar terbanyak; kalau seri, tidak ada yang diklaim "paling banyak".
  const adaTeratas = produksi.length > 0 && maksPorsi > (produksi[1]?.qty ?? 0);
  const totalPorsi = r ? r.produksi.reduce((a, p) => a + p.qty, 0) : null;
  const belumBayar = r?.belum_bayar ?? [];

  const aksiCepat = [
    { href: "#/impor", ikon: "impor", label: "Impor" },
    { href: "#/cek", ikon: "cek", label: "Cek", jumlah: perluCek || 0, sorot: !!perluCek },
    { href: "#/rekap", ikon: "rekap", label: "Rekap" },
    { href: "#/tanya", ikon: "tanya", label: "Tanya AI" },
  ] as const;

  return (
    <div className="tumpuk beranda">
      <header className="beranda-kepala">
        <div>
          <p className="label-huruf-besar">
            {sapaan()}
            {namaToko && (
              <>
                <span aria-hidden="true"> · </span>
                <span className="sr">, </span>
                <span className="nama-toko">{namaToko}</span>
              </>
            )}
          </p>
          <h1>{batchAktif?.nama ?? "RekaPesan"}</h1>
        </div>
      </header>
      {mintaNamaToko && <AjakIsiNamaToko />}
      {tampilSiapkan && <SiapkanToko adaPesanan={pesanan.length > 0} />}

      <div className="kisi-beranda">
        <div className="tumpuk">
          {batchAktif && (
            <section className="ringkasan" aria-label="Ringkasan PO">
              <div className="ringkasan-atas">
                <span className="label-huruf-besar">Omzet disetujui</span>
                {perluCek ? (
                  <a href="#/cek" className="chip-emas">
                    <Icon nama="peringatan" ukuran={14} /> {perluCek} perlu dicek
                  </a>
                ) : perluCek === 0 && pesanan.length > 0 ? (
                  <span className="chip-emas chip-tenang">
                    <Icon nama="centang" ukuran={14} /> Semua sudah dicek
                  </span>
                ) : null}
              </div>
              <strong className="angka-utama">{r ? rupiah(r.omzet) : kosong}</strong>
              <p className="ringkasan-meta">
                {tanggalPanjang(batchAktif.tanggal_kirim)} · {pesanan.length} pesanan
              </p>
              <div className="ringkasan-tombol">
                <a href="#/impor" className="tombol tombol-emas tombol-besar">
                  <Icon nama="impor" ukuran={18} /> Masukkan chat
                </a>
                <a href="#/cek" className="tombol tombol-garis-terang tombol-besar">
                  <Icon nama="cek" ukuran={18} /> Cek pesanan
                </a>
              </div>
            </section>
          )}

          <nav className="aksi-cepat" aria-label="Aksi cepat">
            {aksiCepat.map((a) => (
              <a key={a.href} href={a.href} className={`aksi-cepat-item${"sorot" in a && a.sorot ? " sorot" : ""}`}>
                <span className="aksi-cepat-ikon">
                  <Icon nama={a.ikon} ukuran={20} />
                  {"jumlah" in a && a.jumlah > 0 && <span className="aksi-cepat-jumlah">{a.jumlah}</span>}
                </span>
                <span className="aksi-cepat-label">
                  {a.label}
                  {"jumlah" in a && a.jumlah > 0 && <span className="sr"> ({a.jumlah} perlu dicek)</span>}
                </span>
              </a>
            ))}
          </nav>
          {data.galat && <p className="kecil teks-bahaya">Data belum bisa dimuat: {data.galat.message}</p>}

          <section className="kaca terbaru" aria-labelledby="judul-terbaru">
            <div className="bagian-kepala">
              <h2 id="judul-terbaru">Pesanan terbaru</h2>
              {pesanan.length > 0 && (
                <a href="#/cek?saring=semua" className="tautan-kecil">
                  Lihat semua <Icon nama="kanan" ukuran={15} />
                </a>
              )}
            </div>
            {data.memuat && !data.data ? (
              <div className="kerangka-baris" role="status" aria-label="Memuat pesanan" />
            ) : terbaru.length === 0 ? (
              <div className="terbaru-kosong">
                <p>Belum ada pesanan di PO ini. Masukkan chat grup, nanti setiap pesan pembeli muncul di sini sebagai pesanan yang rapi.</p>
                <a href="#/impor" className="tombol tombol-utama">
                  <Icon nama="impor" />
                  <span>Masukkan chat</span>
                </a>
              </div>
            ) : (
              <ul className="daftar-terbaru">
                {terbaru.map((o) => (
                  <li key={o.id}>
                    <BarisTerbaru order={o} />
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <div className="tumpuk">
          {batchSiap ? <PilihBatch ringkas /> : <div className="kaca kerangka" />}

          {batchAktif && (
            <section className="kaca kartu-produksi" aria-labelledby="judul-produksi">
              <div className="ringkasan-atas">
                <span className="label-huruf-besar redup" id="judul-produksi">
                  Porsi dimasak
                </span>
                <a href="#/rekap" className="tautan-kecil">
                  Rekap <Icon nama="kanan" ukuran={15} />
                </a>
              </div>
              <strong className="produksi-total">
                {totalPorsi ?? kosong}
                <span className="redup"> porsi</span>
              </strong>
              {produksi.length > 0 ? (
                <>
                  <ol className="grafik-batang" aria-label="Porsi per menu">
                    {produksi.map((p, i) => (
                      <li key={p.product_id} className={adaTeratas && i === 0 ? "teratas" : ""} title={`${p.nama}: ${p.qty} porsi`}>
                        <span className="grafik-nilai" aria-hidden="true">
                          {p.qty}
                        </span>
                        <span className="grafik-batang-isi" style={{ height: `${Math.max(8, (p.qty / maksPorsi) * 100)}%` }} />
                        <span className="grafik-label" aria-hidden="true">
                          {p.nama}
                        </span>
                        <span className="sr">
                          {p.nama}, {p.qty} porsi
                        </span>
                      </li>
                    ))}
                  </ol>
                  {adaTeratas ? (
                    <p className="grafik-catatan">
                      <span className="titik-emas" aria-hidden="true" />
                      {produksi[0].nama} paling banyak dipesan · {produksi[0].qty} porsi
                    </p>
                  ) : (
                    <p className="grafik-catatan">{produksi.length} menu dimasak dari pesanan yang disetujui</p>
                  )}
                </>
              ) : (
                <p className="redup kecil">Belum ada porsi. Angka muncul setelah pesanan disetujui.</p>
              )}
            </section>
          )}

          {batchAktif && r && (
            <section className="kaca kartu-bayar" aria-labelledby="judul-bayar">
              <div className="ringkasan-atas">
                <h2 id="judul-bayar">Belum bayar</h2>
                <span className="lencana nada-abu">{belumBayar.length} orang</span>
              </div>
              {belumBayar.length === 0 ? (
                <p className="redup kecil">
                  <Icon nama="centang" ukuran={15} /> Tidak ada tagihan tertunda.
                </p>
              ) : (
                <ul className="daftar-bayar">
                  {belumBayar.slice(0, MAKS_BAYAR).map((b) => (
                    <li key={b.order_id}>
                      <a href={`#/pesanan/${b.order_id}`}>
                        <span className="avatar" aria-hidden="true">
                          {inisial(b.nama)}
                        </span>
                        <span className="daftar-bayar-nama">{b.nama}</span>
                        <strong>{rupiah(b.total)}</strong>
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}

          {pesanan.length === 0 && !tampilSiapkan && <CaraKerja />}
        </div>
      </div>
    </div>
  );
}

/** Satu pesanan: potongan chat asli di kiri, hasil yang sudah rapi di kanan. */
function BarisTerbaru({ order }: { order: Order }) {
  const { katalogMap } = useApp();
  const chat = order.pesan_sumber.map((m) => m.isi).join(" · ");
  const isi = order.items.map((it) => `${it.qty ?? "?"}× ${namaMenu(it.product_id, it.teks_asli, katalogMap)}`).join(", ");
  return (
    <a href={`#/pesanan/${order.id}`} className="baris-terbaru">
      <span className="avatar" aria-hidden="true">
        {inisial(order.customer.nama_tampil)}
      </span>
      <span className="terbaru-isi">
        <span className="terbaru-atas">
          <strong>{order.customer.nama_tampil}</strong>
          <LencanaStatus status={order.status} />
          {order.tanda.length > 0 && (
            <span className="jumlah-tanda" title="Jumlah tanda kuning">
              <Icon nama="peringatan" ukuran={13} /> {order.tanda.length}
            </span>
          )}
        </span>
        <span className="terbaru-ubah">
          <span className="potongan-chat">{chat || "—"}</span>
          <Icon nama="kanan" ukuran={15} className="terbaru-panah" />
          <span className="terbaru-hasil">{isi || "Belum ada item"}</span>
        </span>
      </span>
      <span className="terbaru-total">{rupiah(order.total)}</span>
    </a>
  );
}

function CaraKerja() {
  const langkah = [
    { judul: "Masukkan chat", isi: "Tempel teks atau unggah ekspor chat grup WhatsApp." },
    { judul: "Cek pesanan", isi: "AI membaca chat, harga dihitung dari katalog. Anda yang menyetujui." },
    { judul: "Lihat rekap", isi: "Jumlah masak, urutan kirim, dan siapa yang belum bayar." },
  ];
  return (
    <section className="kaca cara-kerja" aria-labelledby="judul-cara">
      <h2 id="judul-cara">Cara kerja</h2>
      <ol>
        {langkah.map((l, i) => (
          <li key={l.judul}>
            <span className="cara-no">{i + 1}</span>
            <span>
              <strong>{l.judul}</strong>
              <span className="redup kecil">{l.isi}</span>
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
