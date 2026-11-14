import { AjakIsiNamaToko, SiapkanToko } from "../components/Toko";
import { Icon } from "../components/Icon";
import { MenuBelumDikenal } from "../components/MenuBelumDikenal";
import { PapanPesanan, RingkasanKeseluruhan } from "../components/PapanPesanan";
import { api } from "../lib/api";
import { sapaan } from "../lib/format";
import { useApp, useMuat } from "../lib/store";

/**
 * Beranda = buku pesanan: satu ajakan "Masukkan chat", lalu papan pesanan semua hari.
 * Tidak ada lagi pemilih PO, pintasan yang sama dengan nav bawah, atau kartu per hari yang mengulang papan.
 * Porsi per menu ada di tab Rekap.
 */
export default function Beranda() {
  const { versiData, dataBerubah, akun, katalogSiap, batchSiap } = useApp();
  const papan = useMuat(() => api.ringkasan(), [versiData]);
  const adaPapan = !!papan.data && papan.data.hari.some((h) => h.jam.some((j) => j.pesanan.length > 0));
  const namaToko = akun?.nama_toko ?? null;
  // Akun lama (sebelum ada kolom nama toko) diminta mengisinya. null dari server berarti memang belum diisi.
  const mintaNamaToko = !!akun && !namaToko;
  const siap = batchSiap && katalogSiap && !papan.memuat;

  return (
    <div className="tumpuk halaman-sempit beranda">
      <header className="beranda-kepala">
        <div>
          <p className="label-huruf-besar">{sapaan()}</p>
          <h1>{namaToko ?? "RekaPesan"}</h1>
        </div>
      </header>
      {mintaNamaToko && <AjakIsiNamaToko />}
      <TombolMasukkanChat />
      <MenuBelumDikenal />

      {papan.memuat && !papan.data ? (
        <div className="kerangka-baris" role="status" aria-label="Memuat papan pesanan" />
      ) : adaPapan && papan.data ? (
        <section className="tumpuk" aria-labelledby="judul-papan">
          <h2 id="judul-papan">Papan pesanan</h2>
          <RingkasanKeseluruhan data={papan.data.keseluruhan} />
          <PapanPesanan data={papan.data} saatBerubah={dataBerubah} />
        </section>
      ) : papan.galat ? (
        <p className="kecil teks-bahaya">Papan pesanan belum bisa dimuat: {papan.galat.message}</p>
      ) : siap ? (
        <SiapkanToko adaPesanan={false} />
      ) : (
        <CaraKerja />
      )}
    </div>
  );
}

/** Ajakan utama: masukkan chat beberapa hari sekaligus, pesanan dipisah per hari. */
function TombolMasukkanChat() {
  return (
    <a href="#/masukkan-chat" className="tombol tombol-utama tombol-besar tombol-penuh tombol-masukkan-chat">
      <Icon nama="chat" ukuran={22} />
      <span>Masukkan chat</span>
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
