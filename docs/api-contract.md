# Kontrak API Rekapesan (v0, rancangan awal)

Pemilik kontrak: **Raihan**. Perubahan harus disepakati lewat PR yang mengubah berkas ini, karena Amad membangun FE (dan mock) dari sini.

Basis: `/api`. Format: JSON. Autentikasi: header `Authorization: Bearer <token>` kecuali `/auth/login` dan `/health`. Uang dalam rupiah (integer). Waktu ISO 8601.

Kesalahan seragam:

```json
{ "error": { "kode": "kuota_llm_habis", "pesan": "Kuota model habis. Coba lagi nanti atau gunakan cadangan." } }
```

Kode kesalahan yang diharapkan: `tidak_terautentikasi`, `tidak_ditemukan`, `validasi_gagal`, `kuota_llm_habis`, `llm_gagal`, `format_file_tidak_dikenal`.

## Autentikasi

| Method | Path | Isi |
| --- | --- | --- |
| POST | `/auth/login` | `{username, password}` → `{token}` |
| GET | `/health` | `{status: "ok"}` |

## Katalog

| Method | Path | Isi |
| --- | --- | --- |
| GET | `/products` | daftar `Product` |
| POST | `/products` | buat `Product` |
| PATCH | `/products/{id}` | ubah sebagian |
| DELETE | `/products/{id}` | nonaktifkan |

```json
Product = {
  "id": "uuid", "nama": "Ayam Bakar", "alias": ["aybak", "ayam bkr"],
  "harga": 18000, "stok_harian": 30, "aktif": true,
  "resep": [{ "bahan": "ayam", "jumlah": 0.25, "satuan": "kg" }]
}
```

## Batch

| Method | Path | Isi |
| --- | --- | --- |
| GET | `/batches` | daftar `Batch` |
| POST | `/batches` | `{nama, tanggal_kirim}` |
| DELETE | `/batches/{id}` | hapus batch **beserta pesan mentah dan pesanan** |

## Impor

| Method | Path | Isi |
| --- | --- | --- |
| POST | `/batches/{id}/import` | `multipart/form-data` dengan `file` (.txt/.zip) **atau** JSON `{text}` |

Respons:

```json
{ "pesan_baru": 42, "pesan_dilewati": 130, "pesanan_dibuat": 11, "pesanan_diubah": 2, "perlu_cek": 4 }
```

Share target PWA: service worker menerima berkas dari menu Bagikan dan meneruskannya ke endpoint di atas (batch aktif atau batch baru yang dipilih pengguna).

## Pesanan dan review

| Method | Path | Isi |
| --- | --- | --- |
| GET | `/batches/{id}/orders?status=` | daftar `Order` |
| GET | `/orders/{id}` | `Order` lengkap + `pesan_sumber` |
| PATCH | `/orders/{id}` | ubah item, alamat, jam, catatan, status |
| POST | `/orders/{id}/approve` | setujui |
| POST | `/orders/{id}/reject` | tolak |
| POST | `/batches/{id}/orders/approve-clean` | setujui semua yang tanpa tanda |
| GET | `/orders/{id}/reply` | `{teks}` balasan konfirmasi dari templat |

```json
Order = {
  "id": "uuid", "customer": {"id": "uuid", "nama_tampil": "Bu Rina"},
  "status": "perlu_cek",
  "jam_kirim": "12:00", "alamat": "Blok C no 4", "catatan": null,
  "items": [{ "id": "uuid", "product_id": "uuid|null", "teks_asli": "ayam bakar pedes",
              "qty": 2, "harga_satuan": 18000, "catatan_item": "pedas" }],
  "total": 36000,
  "tanda": ["jam_kosong"],
  "perubahan": { "sebelum": null, "sesudah": null },
  "pesan_sumber": [{ "id": "uuid", "waktu": "2026-11-12T09:15:00", "pengirim": "Bu Rina", "isi": "ayam bakar 2 ya" }]
}
```

Status: `perlu_cek`, `dikonfirmasi`, `dibayar`, `dikirim`, `batal`.
Kode tanda: `item_tidak_dikenal`, `jumlah_kosong`, `jumlah_tidak_wajar`, `alamat_kosong`, `jam_kosong`, `stok_kurang`, `mungkin_dobel`, `gagal_diekstrak`.

## Rekap

| Method | Path | Isi |
| --- | --- | --- |
| GET | `/batches/{id}/recap` | produksi, urutan kirim, omzet, belum bayar |
| GET | `/batches/{id}/shopping-list` | daftar belanja dari resep |

```json
Recap = {
  "produksi": [{ "product_id": "uuid", "nama": "Ayam Bakar", "qty": 24, "stok_sisa": 6 }],
  "urutan_kirim": [{ "jam": "12:00", "order_ids": ["uuid"] }],
  "omzet": 432000,
  "belum_bayar": [{ "order_id": "uuid", "nama": "Bu Rina", "total": 36000 }]
}
```

## Bukti bayar

| Method | Path | Isi |
| --- | --- | --- |
| POST | `/orders/{id}/payment-proof` | `multipart` gambar → saran `{nama, nominal, cocok: true/false}` |
| POST | `/orders/{id}/payment-confirm` | penjual mengonfirmasi → status `dibayar` |

Model hanya memberi saran. Status berubah hanya setelah `payment-confirm`.

## Agen tanya-jawab

| Method | Path | Isi |
| --- | --- | --- |
| POST | `/agent/ask` | `{batch_id, pertanyaan, riwayat: []}` |

```json
{ "jawaban": "Ayam bakar untuk jam 12:00: 9 porsi.",
  "trace": [{ "tool": "rekap_produksi", "argumen": {"batch_id": "uuid", "jam": "12:00"}, "hasil_ringkas": "..." }] }
```

## Pengaturan

| Method | Path | Isi |
| --- | --- | --- |
| GET/PATCH | `/settings` | `{ambang_jumlah_tidak_wajar: 20}` |
