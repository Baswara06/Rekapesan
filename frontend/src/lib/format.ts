import type { KodeTanda, Product, StatusPesanan } from "./api";

const rupiahFmt = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });

export function rupiah(n: number | null | undefined): string {
  if (n == null) return "-";
  // Intl memberi "Rp 36.000" dengan spasi tak-putus. Disatukan supaya tidak terpotong di layar sempit.
  return rupiahFmt.format(n).replace(/\s/g, "");
}

export function angka(n: number): string {
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 }).format(n);
}

export function tanggalPanjang(iso: string | null | undefined): string {
  if (!iso) return "-";
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("id-ID", { weekday: "long", day: "numeric", month: "long" });
}

export function tanggalPendek(iso: string | null | undefined): string {
  if (!iso) return "-";
  const d = new Date(`${iso.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("id-ID", { day: "numeric", month: "short" });
}

export function jamPesan(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
}

export function hariIniISO(tambahHari = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + tambahHari);
  const z = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
}

export function sapaan(jam = new Date().getHours()): string {
  if (jam < 11) return "Selamat pagi";
  if (jam < 15) return "Selamat siang";
  if (jam < 18) return "Selamat sore";
  return "Selamat malam";
}

export function inisial(nama: string): string {
  const kata = nama
    .replace(/^(bu|pak|mbak|mas|kak|bang|dek|om|tante)\s+/i, "")
    .split(/\s+/)
    .filter(Boolean);
  return (kata[0]?.[0] ?? "?").toUpperCase() + (kata[1]?.[0] ?? "").toUpperCase();
}

/** Penjelasan tanda kuning dengan bahasa penjual, bukan istilah teknis. */
export const TANDA: Record<KodeTanda, { judul: string; saran: string }> = {
  item_tidak_dikenal: { judul: "Menu tidak dikenal", saran: "Pilih menu yang benar dari katalog." },
  jumlah_kosong: { judul: "Jumlah belum ada", saran: "Isi berapa porsi yang dipesan." },
  jumlah_tidak_wajar: { judul: "Jumlah tidak wajar", saran: "Jumlahnya terlalu banyak. Pastikan ke pembeli." },
  alamat_kosong: { judul: "Alamat belum ada", saran: "Tanyakan alamat kirim ke pembeli." },
  jam_kosong: { judul: "Jam kirim belum ada", saran: "Tanyakan jam kirim ke pembeli." },
  stok_kurang: { judul: "Stok kurang", saran: "Pesanan melebihi sisa stok hari ini." },
  mungkin_dobel: { judul: "Mungkin dobel", saran: "Pembeli memesan menu yang sama lagi. Tambahan atau salah kirim?" },
  gagal_diekstrak: { judul: "AI gagal membaca", saran: "Baca chat aslinya, lalu isi pesanan secara manual." },
};

export const STATUS: Record<StatusPesanan, { label: string; nada: "kuning" | "hijau" | "biru" | "ungu" | "abu" }> = {
  perlu_cek: { label: "Perlu dicek", nada: "kuning" },
  dikonfirmasi: { label: "Disetujui", nada: "hijau" },
  dibayar: { label: "Sudah bayar", nada: "biru" },
  dikirim: { label: "Terkirim", nada: "ungu" },
  batal: { label: "Batal", nada: "abu" },
};

/** Perpindahan status yang boleh lewat PATCH, sama dengan tabel di kontrak API. */
export const PINDAH_STATUS: Record<StatusPesanan, StatusPesanan[]> = {
  perlu_cek: ["dikonfirmasi", "batal"],
  dikonfirmasi: ["perlu_cek", "batal", "dikirim"],
  dibayar: ["dikonfirmasi", "dikirim"],
  dikirim: [],
  batal: ["perlu_cek"],
};

export function namaMenu(productId: string | null, teksAsli: string, katalog: Map<string, Product>): string {
  if (!productId) return teksAsli;
  return katalog.get(productId)?.nama ?? teksAsli;
}

export function pisahAlias(teks: string): string[] {
  return teks
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}
