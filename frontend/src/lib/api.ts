// Klien API bertipe. Kontrak lengkap ada di docs/api-contract.md.
// Semua angka uang (harga, total, omzet) datang dari server. FE tidak pernah menghitung harga.
const BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const KUNCI_TOKEN = "rekapesan.token";

export type KodeTanda =
  | "item_tidak_dikenal"
  | "jumlah_kosong"
  | "jumlah_tidak_wajar"
  | "alamat_kosong"
  | "jam_kosong"
  | "stok_kurang"
  | "mungkin_dobel"
  | "gagal_diekstrak";

export type StatusPesanan = "perlu_cek" | "dikonfirmasi" | "dibayar" | "dikirim" | "batal";

export interface Resep {
  bahan: string;
  jumlah: number;
  satuan: string;
}

export interface Product {
  id: string;
  nama: string;
  alias: string[];
  harga: number;
  stok_harian: number | null;
  aktif: boolean;
  resep: Resep[];
}

export type ProductIn = Omit<Product, "id">;

/** Akun yang sedang masuk. `nama_toko` bisa null untuk akun lama atau yang belum mengisinya. */
export interface Akun {
  username: string;
  nama_toko: string | null;
}

export interface Batch {
  id: string;
  nama: string;
  tanggal_kirim: string;
  tanggal_mulai: string | null;
  dibuat_pada: string;
}

export interface ImportResult {
  pesan_baru: number;
  pesan_dilewati: number;
  pesanan_dibuat: number;
  pesanan_diubah: number;
  perlu_cek: number;
}

/** Isi chat untuk impor harian: teks tempel atau berkas ekspor (.txt/.zip). */
export type IsiChat = { teks: string } | { berkas: File };

export interface MenuTerdeteksi {
  nama: string;
  harga: number | null;
  sudah_ada: boolean;
  product_id: string | null;
}

/** Hasil POST /impor/pratinjau: dibaca kode, tanpa AI, belum menyimpan apa pun. */
export interface PratinjauImpor {
  penjual: string | null;
  tanggal_awal: string | null;
  tanggal_akhir: string | null;
  jumlah_pesan: number;
  hari: { tanggal: string; jumlah_pesan: number }[];
  menu: MenuTerdeteksi[];
  /** Tebakan kode dari pesan pembeli: disebut tapi tidak ada di daftar menu penjual maupun katalog. Tanpa harga. */
  menu_dari_pembeli?: { nama: string; jumlah_sebut: number; contoh: string }[];
  /** Semua pengirim di chat, terbanyak dulu. Dipakai memilih penjual bila tidak terdeteksi. */
  pengirim?: string[];
}

export interface HasilImporHari extends ImportResult {
  tanggal: string;
  batch_id: string;
  nama: string;
}

export interface HasilImporHarian {
  hari: HasilImporHari[];
  total: ImportResult;
  /** Jumlah foto bukti transfer yang terbaca (hanya bila diminta dan berkasnya .zip dengan media). */
  bukti_terbaca?: number;
}

export type StatusPapan = "perlu_cek" | "diproses" | "selesai" | "batal";
export type StatusBayar = "lunas" | "belum";

export interface SaranPesanan {
  /** `bukti_transfer`: foto bukti dibaca model saat impor. `bayar_dobel`: informasi saja, tanpa tombol. */
  jenis: "sudah_bayar" | "sudah_terima" | "bukti_transfer" | "bayar_dobel";
  teks: string;
  kutipan: string | null;
}

export interface PesananPapan {
  id: string;
  nama: string;
  status: StatusPesanan;
  status_papan: StatusPapan;
  bayar: StatusBayar;
  total: number;
  jam_kirim: string | null;
  alamat: string | null;
  items: { nama: string; qty: number | null }[];
  tanda: KodeTanda[];
  saran: SaranPesanan[];
}

export interface Ringkasan {
  keseluruhan: {
    perlu_cek: number;
    diproses: number;
    selesai: number;
    batal: number;
    omzet: number;
    belum_bayar: number;
    jumlah_belum_bayar: number;
  };
  hari: {
    tanggal: string;
    batch_id: string;
    nama: string;
    jam: { jam: string | null; pesanan: PesananPapan[] }[];
  }[];
}

export interface OrderItem {
  id?: string;
  product_id: string | null;
  teks_asli: string;
  qty: number | null;
  harga_satuan?: number | null;
  catatan_item: string | null;
}

export interface PotretPesanan {
  status: StatusPesanan;
  jam_kirim: string | null;
  alamat: string | null;
  catatan: string | null;
  items: OrderItem[];
  total: number;
  tanda: KodeTanda[];
}

export interface PesanSumber {
  id: string;
  waktu: string;
  pengirim: string;
  isi: string;
}

export interface Order {
  id: string;
  batch_id: string;
  customer: { id: string; nama_tampil: string };
  status: StatusPesanan;
  jam_kirim: string | null;
  alamat: string | null;
  catatan: string | null;
  items: OrderItem[];
  total: number;
  tanda: KodeTanda[];
  perubahan: { sebelum: PotretPesanan | null; sesudah: PotretPesanan | null };
  pesan_sumber: PesanSumber[];
}

export interface OrderPatch {
  items?: { product_id: string | null; teks_asli: string; qty: number | null; catatan_item: string | null }[];
  jam_kirim?: string | null;
  alamat?: string | null;
  catatan?: string | null;
  status?: StatusPesanan;
}

export interface Recap {
  produksi: { product_id: string; nama: string; qty: number; stok_sisa: number | null }[];
  urutan_kirim: { jam: string | null; order_ids: string[] }[];
  omzet: number;
  belum_bayar: { order_id: string; nama: string; total: number }[];
  menunggu_persetujuan: number;
}

export type ShoppingList = { bahan: string; jumlah: number; satuan: string }[];

export interface ProofSuggestion {
  nama: string | null;
  nominal: number | null;
  cocok: boolean;
}

export interface TraceLangkah {
  tool: string;
  argumen: Record<string, unknown>;
  hasil_ringkas: string;
  /** Hasil tool utuh. Bisa tidak ada pada server lama, tampilan lalu memakai `hasil_ringkas`. */
  hasil?: Record<string, unknown>;
}

export interface AgentAnswer {
  jawaban: string;
  trace: TraceLangkah[];
  /** Percakapan tempat jawaban ini disimpan (baru dibuat bila tidak dikirim). */
  percakapan_id?: string;
}

/** Item pesanan yang tidak cocok dengan katalog, dikelompokkan kode per nama. */
export interface MenuBelumDikenal {
  kunci: string;
  nama: string;
  jumlah_pesanan: number;
  total_porsi: number;
  contoh: string;
}

export interface RingkasPercakapan {
  id: string;
  judul: string;
  diubah_pada: string;
  /** Tanggal percakapan terhapus bila tidak ada chat baru (30 hari setelah pesan terakhir). */
  berakhir_pada: string;
  jumlah_pesan: number;
}

export interface DetailPercakapan {
  id: string;
  judul: string;
  berakhir_pada: string;
  pesan: { peran: "pengguna" | "agen"; isi: string; trace: TraceLangkah[] }[];
}

export type RiwayatTanya = { peran: "pengguna" | "agen"; isi: string }[];

/** Galat dari server dengan kode seragam (lihat bagian "Kesalahan seragam" di kontrak). */
export class ApiError extends Error {
  constructor(
    public status: number,
    public kode: string,
    pesan: string,
  ) {
    super(pesan);
    this.name = "ApiError";
  }
}

let token: string | null = bacaToken();
let saatTidakTerautentikasi: (() => void) | null = null;

function bacaToken(): string | null {
  try {
    return localStorage.getItem(KUNCI_TOKEN);
  } catch {
    return null;
  }
}

export function ambilToken(): string | null {
  return token;
}

export function simpanToken(baru: string | null): void {
  token = baru;
  try {
    if (baru) localStorage.setItem(KUNCI_TOKEN, baru);
    else localStorage.removeItem(KUNCI_TOKEN);
  } catch {
    /* penyimpanan diblokir: token tetap hidup di memori sampai tab ditutup */
  }
}

/** Dipanggil sekali oleh aplikasi supaya token kedaluwarsa mengembalikan pengguna ke layar login. */
export function aturSaatTidakTerautentikasi(fn: () => void): void {
  saatTidakTerautentikasi = fn;
}

async function minta<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && typeof init.body === "string") headers.set("Content-Type", "application/json");

  let res: Response;
  try {
    res = await fetch(`${BASE}/api${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "jaringan", "Tidak tersambung ke server. Periksa internet atau pastikan backend menyala.");
  }

  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err = data?.error;
    const kode: string = err?.kode ?? "galat_server";
    const pesan: string = err?.pesan ?? `Server membalas galat (${res.status}). Coba lagi sebentar.`;
    if (res.status === 401 && !path.startsWith("/auth/")) {
      simpanToken(null);
      saatTidakTerautentikasi?.();
    }
    throw new ApiError(res.status, kode, pesan);
  }
  return data as T;
}

const json = (body: unknown) => JSON.stringify(body);

/** Body impor harian: multipart untuk berkas, JSON untuk teks tempel (sama dengan impor per batch). */
function bodyChat(isi: IsiChat): BodyInit {
  if ("berkas" in isi) {
    const form = new FormData();
    form.append("file", isi.berkas, isi.berkas.name || "chat.txt");
    return form;
  }
  return json({ text: isi.teks });
}

export const api = {
  kesehatan: () => minta<{ status: string }>("/health"),
  login: (username: string, password: string) =>
    minta<{ token: string }>("/auth/login", { method: "POST", body: json({ username, password }) }),
  daftar: (username: string, password: string, nama_toko: string) =>
    minta<{ token: string }>("/auth/register", { method: "POST", body: json({ username, password, nama_toko }) }),
  akunSaya: () => minta<Akun>("/auth/me"),
  ubahAkun: (nama_toko: string) => minta<Akun>("/auth/me", { method: "PATCH", body: json({ nama_toko }) }),

  daftarMenu: () => minta<Product[]>("/products"),
  buatMenu: (p: ProductIn) => minta<Product>("/products", { method: "POST", body: json(p) }),
  ubahMenu: (id: string, p: Partial<ProductIn>) =>
    minta<Product>(`/products/${id}`, { method: "PATCH", body: json(p) }),
  nonaktifkanMenu: (id: string) => minta<Product>(`/products/${id}`, { method: "DELETE" }),

  daftarBatch: () => minta<Batch[]>("/batches"),
  buatBatch: (b: { nama: string; tanggal_kirim: string; tanggal_mulai?: string | null }) =>
    minta<Batch>("/batches", { method: "POST", body: json(b) }),
  hapusBatch: (id: string) => minta<void>(`/batches/${id}`, { method: "DELETE" }),

  imporTeks: (batchId: string, text: string) =>
    minta<ImportResult>(`/batches/${batchId}/import`, { method: "POST", body: json({ text }) }),
  imporBerkas: (batchId: string, file: Blob, nama = "chat.txt") => {
    const form = new FormData();
    form.append("file", file, nama);
    return minta<ImportResult>(`/batches/${batchId}/import`, { method: "POST", body: form });
  },

  daftarPesanan: (batchId: string, status?: StatusPesanan) =>
    minta<Order[]>(`/batches/${batchId}/orders${status ? `?status=${status}` : ""}`),
  pesanan: (id: string) => minta<Order>(`/orders/${id}`),
  ubahPesanan: (id: string, patch: OrderPatch) =>
    minta<Order>(`/orders/${id}`, { method: "PATCH", body: json(patch) }),
  setujui: (id: string) => minta<Order>(`/orders/${id}/approve`, { method: "POST" }),
  tolak: (id: string) => minta<Order>(`/orders/${id}/reject`, { method: "POST" }),
  setujuiYangBersih: (batchId: string) =>
    minta<{ disetujui: number; masih_bertanda: number }>(`/batches/${batchId}/orders/approve-clean`, {
      method: "POST",
    }),
  balasan: (id: string) => minta<{ teks: string }>(`/orders/${id}/reply`),

  rekap: (batchId: string) => minta<Recap>(`/batches/${batchId}/recap`),
  daftarBelanja: (batchId: string) => minta<ShoppingList>(`/batches/${batchId}/shopping-list`),

  bacaBuktiBayar: (orderId: string, gambar: File) => {
    const form = new FormData();
    form.append("file", gambar, gambar.name);
    return minta<ProofSuggestion>(`/orders/${orderId}/payment-proof`, { method: "POST", body: form });
  },
  konfirmasiBayar: (orderId: string) =>
    // Untuk pesanan yang sudah dikirim status tetap "dikirim", hanya pembayarannya yang jadi lunas.
    minta<{ order_id: string; status: StatusPesanan }>(`/orders/${orderId}/payment-confirm`, { method: "POST" }),

  pratinjauImpor: (isi: IsiChat) => minta<PratinjauImpor>("/impor/pratinjau", { method: "POST", body: bodyChat(isi) }),
  imporHarian: (isi: IsiChat, opsi: { bacaBukti?: boolean; penjual?: string | null } = {}) => {
    const q = new URLSearchParams();
    if (opsi.bacaBukti) q.set("baca_bukti", "true");
    if (opsi.penjual) q.set("penjual", opsi.penjual);
    const s = q.toString();
    return minta<HasilImporHarian>(`/impor${s ? `?${s}` : ""}`, { method: "POST", body: bodyChat(isi) });
  },
  ringkasan: () => minta<Ringkasan>("/ringkasan"),

  /** Tanpa `batchId`: agen membaca semua hari milik akun. */
  tanya: (pertanyaan: string, riwayat: RiwayatTanya, opsi: { batchId?: string; percakapanId?: string | null } = {}) =>
    minta<AgentAnswer>("/agent/ask", {
      method: "POST",
      body: json({
        ...(opsi.batchId ? { batch_id: opsi.batchId } : {}),
        ...(opsi.percakapanId ? { percakapan_id: opsi.percakapanId } : {}),
        pertanyaan,
        riwayat,
      }),
    }),
  menuBelumDikenal: () => minta<MenuBelumDikenal[]>("/menu-belum-dikenal"),
  tambahMenuBelumDikenal: (kunci: string, nama: string, harga: number) =>
    minta<{ menu: Product; pesanan_dicocokkan: number }>("/menu-belum-dikenal/tambahkan", {
      method: "POST",
      body: json({ kunci, nama, harga }),
    }),
  daftarPercakapan: () => minta<RingkasPercakapan[]>("/agent/percakapan"),
  detailPercakapan: (id: string) => minta<DetailPercakapan>(`/agent/percakapan/${id}`),
  hapusPercakapan: (id: string) => minta<void>(`/agent/percakapan/${id}`, { method: "DELETE" }),
};

/** Dipertahankan untuk kompatibilitas dengan kerangka awal. */
export async function cekKesehatan(): Promise<{ status: string }> {
  return api.kesehatan();
}
