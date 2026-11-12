// Klien API bertipe. Kontrak lengkap ada di docs/api-contract.md.
const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

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

export async function cekKesehatan(): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/api/health`);
  if (!res.ok) throw new Error(`health ${res.status}`);
  return res.json();
}
