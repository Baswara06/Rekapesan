# Kontrak API Rekapesan (v1)

Pemilik kontrak: **Raihan**. Perubahan harus disepakati lewat PR yang mengubah berkas ini, karena Amad membangun FE (dan mock) dari sini.

Basis: `/api`. Format: JSON. Autentikasi: header `Authorization: Bearer <token>` kecuali `/auth/login` dan `/health`. Uang dalam rupiah (integer). Waktu ISO 8601.

## Kesalahan seragam

```json
{ "error": { "kode": "kuota_llm_habis", "pesan": "Kuota model habis. Belum ada yang disimpan, coba impor lagi nanti." } }
```

| Kode | Status HTTP | Artinya |
| --- | --- | --- |
| `tidak_terautentikasi` | 401 | Token tidak ada, rusak, atau kedaluwarsa. Login gagal juga memakai kode ini |
| `tidak_ditemukan` | 404 | Batch, pesanan, atau menu tidak ada |
| `validasi_gagal` | 422 | Isian tidak sah (pesan menyebut isian yang salah) |
| `validasi_gagal` | 413 | Berkas impor lebih dari 20 MB |
| `validasi_gagal` | 409 | Aksi tidak cocok dengan status pesanan, mis. menyetujui pesanan batal atau membuat balasan sebelum disetujui |
| `format_file_tidak_dikenal` | 400 | Berkas bukan ekspor WhatsApp yang dikenali |
| `impor_bentrok` | 409 | Ada impor lain untuk batch yang sama sedang berjalan. Tunggu sebentar lalu ulangi |
| `kuota_llm_habis` | 429 | Kuota model habis |
| `llm_gagal` | 502 | Model atau penyedia tidak bisa dihubungi, atau fitur AI belum tersedia |

Untuk impor, `kuota_llm_habis` dan `llm_gagal` hanya muncul bila ekstraksi gagal **untuk semua pengirim**. Dalam kasus itu **tidak ada yang disimpan**, jadi impor aman diulang. Bila hanya sebagian pengirim gagal, impor berhasil dan pesanan pengirim itu bertanda `gagal_diekstrak`.

## Autentikasi

| Method | Path | Isi |
| --- | --- | --- |
| POST | `/auth/login` | `{username, password}` → `{token}` (berlaku 12 jam) |
| GET | `/health` | `{status: "ok"}` |

Akun demo diatur lewat `DEMO_USERNAME` dan `DEMO_PASSWORD` di `.env`. Token ditandatangani dengan `APP_SECRET_KEY`.

Login **dimatikan** (401 `tidak_terautentikasi` dengan pesan yang menyebut isian `.env` yang kurang) bila:

- `DEMO_PASSWORD` kosong, atau
- `APP_SECRET_KEY` kosong, masih nilai bawaan `.env.example`, atau kurang dari 16 karakter. Token yang ditandatangani dengan kunci seperti itu juga ditolak, supaya tidak ada yang bisa membuat token sendiri.

## Katalog

| Method | Path | Isi |
| --- | --- | --- |
| GET | `/products?aktif=` | daftar `Product` (semua, atau saring `aktif=true/false`) |
| POST | `/products` | buat `Product` (201) |
| PATCH | `/products/{id}` | ubah sebagian. `stok_harian: null` berarti stok tidak dibatasi. `resep`, bila dikirim, menggantikan seluruh resep |
| DELETE | `/products/{id}` | nonaktifkan (`aktif: false`), mengembalikan `Product`. Menu tidak dihapus karena pesanan lama merujuknya |

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
| GET | `/batches` | daftar `Batch`, terbaru dulu |
| POST | `/batches` | `{nama, tanggal_kirim, tanggal_mulai?}` (201) |
| DELETE | `/batches/{id}` | hapus batch **beserta pesan mentah, pembeli, dan pesanan**. Respons 204 tanpa isi |

```json
Batch = { "id": "uuid", "nama": "PO Jumat", "tanggal_kirim": "2026-11-13",
          "tanggal_mulai": "2026-11-12", "dibuat_pada": "2026-11-12T08:10:00" }
```

`tanggal_mulai` adalah tanggal chat PO dibuka (boleh kosong). Pesan sebelum tanggal itu dibuang saat impor. Tidak boleh setelah `tanggal_kirim`.

## Impor

| Method | Path | Isi |
| --- | --- | --- |
| POST | `/batches/{id}/import` | `multipart/form-data` dengan `file` (.txt/.zip) atau `text`, **atau** JSON `{text}`. Maksimal 20 MB |

Respons:

```json
{ "pesan_baru": 42, "pesan_dilewati": 130, "pesanan_dibuat": 11, "pesanan_diubah": 2, "perlu_cek": 4 }
```

Impor ulang aman: pesan yang sudah pernah masuk dilewati (`pesan_dilewati`) dan tidak membuat pesanan dobel. Kemungkinan galat: `tidak_ditemukan`, `format_file_tidak_dikenal`, `validasi_gagal` (kosong atau lebih dari 20 MB), `impor_bentrok`, `kuota_llm_habis`, `llm_gagal`.

Share target PWA: service worker menerima berkas dari menu Bagikan dan meneruskannya ke endpoint di atas (batch aktif atau batch baru yang dipilih pengguna).

## Pesanan dan review

| Method | Path | Isi |
| --- | --- | --- |
| GET | `/batches/{id}/orders?status=` | daftar `Order` (status tidak dikenal → 422) |
| GET | `/orders/{id}` | `Order` lengkap + `pesan_sumber` |
| PATCH | `/orders/{id}` | ubah `items`, `alamat`, `jam_kirim`, `catatan`, `status` (semua opsional) |
| POST | `/orders/{id}/approve` | setujui (`perlu_cek` → `dikonfirmasi`). Pesanan batal → 409 |
| POST | `/orders/{id}/reject` | tolak (→ `batal`). Pesanan `dibayar` atau `dikirim` → 409 |
| POST | `/batches/{id}/orders/approve-clean` | setujui semua `perlu_cek` yang tanpa tanda. Respons `{disetujui, masih_bertanda}` |
| GET | `/orders/{id}/reply` | `{teks}` balasan konfirmasi dari templat. Hanya untuk pesanan yang sudah disetujui, selain itu 409 |

```json
Order = {
  "id": "uuid", "batch_id": "uuid", "customer": {"id": "uuid", "nama_tampil": "Bu Rina"},
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

Aturan `PATCH /orders/{id}`:

- `items` yang dikirim **menggantikan** seluruh item: `[{product_id, teks_asli, qty, catatan_item}]`. Server mengisi `harga_satuan` dari katalog dan menghitung ulang `total` serta `tanda`. Kolom `harga_satuan` dan `total` dari klien **diabaikan**. `product_id` yang tidak dikenal menjadi `null` dan pesanan diberi tanda `item_tidak_dikenal`.
- `jam_kirim` diterima dalam bentuk bebas ("12", "jam 11.30") dan disimpan sebagai `HH:MM`. Kosong atau `null` menghapus jam. Jam tidak sah → 422.
- Isian yang tidak dikirim tidak berubah. `alamat: null` atau `""` menghapus alamat.
- Stok dihitung dari pesanan lain di batch yang sama yang belum batal.
- `product_id` menu yang tidak ada atau sudah nonaktif diperlakukan seperti tidak dikenal (`null`), sama seperti jalur impor.
- `status` hanya boleh berpindah menurut tabel di bawah. Di luar itu 409 `validasi_gagal`. Mengirim status yang sama dengan status sekarang tidak mengubah apa pun.

| Dari | Boleh menjadi |
| --- | --- |
| `perlu_cek` | `dikonfirmasi`, `batal` |
| `dikonfirmasi` | `perlu_cek`, `batal`, `dikirim` |
| `dibayar` | `dikonfirmasi` (pelunasan dibatalkan), `dikirim` |
| `dikirim` | tidak ada |
| `batal` | `perlu_cek` (dibuka lagi untuk diperiksa) |

`dibayar` **tidak bisa** dicapai lewat PATCH. Satu-satunya jalan adalah `POST /orders/{id}/payment-confirm`.

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
  "belum_bayar": [{ "order_id": "uuid", "nama": "Bu Rina", "total": 36000 }],
  "menunggu_persetujuan": 4
}

ShoppingList = [{ "bahan": "Ayam", "jumlah": 6.0, "satuan": "kg" }]
```

Hanya pesanan yang sudah disetujui (`dikonfirmasi`, `dibayar`, `dikirim`) yang dihitung. `menunggu_persetujuan` adalah jumlah pesanan `perlu_cek`, supaya penjual tahu rekap belum lengkap. `stok_sisa` bernilai `null` bila stok menu tidak dibatasi, dan jam kirim yang kosong (`jam: null`) diurutkan paling akhir.

## Bukti bayar

| Method | Path | Isi |
| --- | --- | --- |
| POST | `/orders/{id}/payment-proof` | `multipart` gambar (`file`, maksimal 5 MB) → saran `{nama, nominal, cocok: true/false}` |
| POST | `/orders/{id}/payment-confirm` | penjual mengonfirmasi → `{order_id, status: "dibayar"}`. Hanya untuk pesanan `dikonfirmasi`, selain itu 409 |

Model hanya memberi saran. `cocok` dihitung kode (nominal sama dengan total pesanan). Status berubah hanya setelah `payment-confirm`. Bila pembaca gambar gagal atau belum tersedia, respons `llm_gagal` (502) dan penjual bisa langsung memakai `payment-confirm`.

## Agen tanya-jawab

| Method | Path | Isi |
| --- | --- | --- |
| POST | `/agent/ask` | `{batch_id, pertanyaan, riwayat: []}` |

```json
{ "jawaban": "Ayam bakar untuk jam 12:00: 9 porsi.",
  "trace": [{ "tool": "rekap_produksi", "argumen": {"batch_id": "uuid", "jam": "12:00"}, "hasil_ringkas": "..." }] }
```

Bila agen gagal atau belum tersedia, respons `llm_gagal` (502).

## Pengaturan

| Method | Path | Isi |
| --- | --- | --- |
| GET/PATCH | `/settings` | `{ambang_jumlah_tidak_wajar: 20}` |

**Belum tersedia.** Sementara ini ambang diambil dari `JUMLAH_TIDAK_WAJAR_DEFAULT` di `.env`. Endpoint ini menunggu tabel pengaturan dari modul DB.
