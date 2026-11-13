import { Icon, type NamaIkon } from "../components/Icon";
import { Kepala } from "../components/ui";

const MENU: { href: string; ikon: NamaIkon; judul: string; isi: string }[] = [
  { href: "#/tanya", ikon: "tanya", judul: "Tanya pesanan", isi: "Tanya AI soal rekap, siapa belum bayar, dan lainnya." },
  { href: "#/katalog", ikon: "katalog", judul: "Katalog menu", isi: "Menu, harga, stok, nama panggilan, dan resep." },
  { href: "#/pengaturan", ikon: "pengaturan", judul: "Pengaturan", isi: "Ukuran huruf, tema, hapus data PO, keluar." },
];

export default function Lainnya() {
  return (
    <div className="tumpuk">
      <Kepala judul="Lainnya" />
      <ul className="langkah-daftar">
        {MENU.map((m) => (
          <li key={m.href}>
            <a href={m.href} className="kaca langkah-kartu">
              <span className="langkah-no ikon-bulat" aria-hidden="true">
                <Icon nama={m.ikon} />
              </span>
              <span className="langkah-teks">
                <strong>{m.judul}</strong>
                <span>{m.isi}</span>
              </span>
              <Icon nama="kanan" />
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
