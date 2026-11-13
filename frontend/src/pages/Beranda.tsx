import { PilihBatch } from "../components/Batch";
import { Icon } from "../components/Icon";
import { LencanaStatus } from "../components/ui";
import { api, type Order } from "../lib/api";
import { inisial, namaMenu, rupiah, sapaan, tanggalPanjang } from "../lib/format";
import { useApp, useMuat } from "../lib/store";

const MAKS_TERBARU = 5;

export default function Beranda({ perluCek }: { perluCek: number | null }) {
  const { batchAktif, batches, batchSiap, versiData } = useApp();
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

  if (batchSiap && batches.length === 0) {
    return (
      <div className="tumpuk halaman-sempit">
        <header className="beranda-kepala">
          <div>
            <p className="redup">{sapaan()}</p>
            <h1>Selamat datang di Rekapesan</h1>
          </div>
        </header>
        <PilihBatch />
        <CaraKerja />
      </div>
    );
  }

  return (
    <div className="tumpuk">
      <header className="beranda-kepala">
        <div>
          <p className="redup">{sapaan()}</p>
          <h1>{batchAktif?.nama ?? "Rekapesan"}</h1>
          {batchAktif && (
            <p className="redup kecil">
              Dikirim {tanggalPanjang(batchAktif.tanggal_kirim)} · {pesanan.length} pesanan
            </p>
          )}
        </div>
        {batchAktif && (
          <a href="#/impor" className="tombol tombol-utama">
            <Icon nama="impor" />
            <span>Masukkan chat</span>
          </a>
        )}
      </header>

      {batchAktif && (
        <section className="kaca ringkasan" aria-label="Ringkasan PO">
          <div className="ringkasan-utama">
            <span className="label-kecil">Omzet pesanan disetujui</span>
            <strong className="angka-utama">{r ? rupiah(r.omzet) : kosong}</strong>
          </div>
          <dl className="ringkasan-angka">
            <div className={perluCek ? "perlu" : ""}>
              <dt>Perlu dicek</dt>
              <dd>{perluCek ?? "…"}</dd>
            </div>
            <div>
              <dt>Porsi dimasak</dt>
              <dd>{r ? r.produksi.reduce((a, p) => a + p.qty, 0) : kosong}</dd>
            </div>
            <div>
              <dt>Belum bayar</dt>
              <dd>{r ? `${r.belum_bayar.length} orang` : kosong}</dd>
            </div>
          </dl>
          {perluCek ? (
            <a href="#/cek" className="ringkasan-ajak">
              <Icon nama="peringatan" ukuran={17} />
              <span>
                <strong>{perluCek} pesanan</strong> menunggu persetujuan Anda. Rekap belum lengkap sampai semuanya dicek.
              </span>
              <span className="ringkasan-ajak-aksi">
                Cek sekarang <Icon nama="kanan" ukuran={16} />
              </span>
            </a>
          ) : null}
        </section>
      )}
      {data.galat && <p className="kecil teks-bahaya">Data belum bisa dimuat: {data.galat.message}</p>}

      <div className="kisi-beranda">
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

        <div className="tumpuk">
          {batchSiap ? <PilihBatch ringkas /> : <div className="kaca kerangka" />}
          <a href="#/tanya" className="kaca kartu-tanya">
            <span className="kartu-tanya-ikon">
              <Icon nama="tanya" ukuran={19} />
            </span>
            <span className="kartu-tanya-teks">
              <strong>Tanya soal pesanan</strong>
              <span className="redup kecil">Misalnya "berapa ayam bakar untuk jam 12?". Jawaban disertai data yang dibaca.</span>
            </span>
            <Icon nama="kanan" ukuran={18} />
          </a>
          {pesanan.length === 0 && <CaraKerja />}
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
