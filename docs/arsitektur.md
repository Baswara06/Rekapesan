# Arsitektur Rekapesan

## Prinsip

LLM dipakai hanya untuk memahami teks tidak terstruktur. Semua yang deterministik (harga, total, stok, tanda kuning, rekap, balasan konfirmasi) dihitung kode. Penjual memutuskan semua yang meragukan.

## Alur impor

```mermaid
flowchart TD
    A[File ekspor / teks tempel / Share target] --> B[parser: pecah pesan]
    B --> C[sidik + saring tanggal + buang yang sudah ada]
    C --> D[anonymize: samarkan nomor]
    D --> E[extractor: LLM per pengirim, paralel]
    E --> F[validasi skema Pydantic]
    F --> G[rules: cocokkan katalog, hitung total, cek stok]
    G --> H[rules: tanda kuning, terapkan ubah/batal]
    H --> I[(DB)]
    I --> J[review di FE]
```

## Modul dan pemilik

| Modul | Folder | Pemilik |
| --- | --- | --- |
| API CRUD, auth, templat balasan | `backend/app/api`, `core` | Raihan |
| Skema DB, rekap | `backend/app/db` | Satria |
| Mesin aturan, orkestrasi impor | `backend/app/rules`, `services` | Satria |
| Parser, sidik, anonimisasi | `backend/app/parser` | Satria |
| Ekstraktor, agen, vision | `backend/app/extractor`, `agent` | Pangeran |
| Frontend + PWA | `frontend/` | Amad |

## Antarmuka antar-modul

| Dari → Ke | Fungsi |
| --- | --- |
| parser → services | `parse_export(file_or_text, batch_date) -> list[Message]` |
| parser → extractor | `anonymize(text) -> str` |
| services → extractor | `extract_orders(sender_messages, catalog, active_order) -> Extraction` |
| extractor → rules | `Extraction` (intent, items, tanggal, jam, alamat, catatan) |
| rules → services | `apply_intent(order_context, extraction) -> OrderChange` |
| agent → DB | koneksi **read-only** |

### Rincian yang disepakati (modul Satria)

- **`parse_export(file_or_text, batch_date)`**: `batch_date` adalah **tanggal chat PO dibuka** (`batches.tanggal_mulai`), bukan tanggal kirim. Pesan sebelum tanggal itu dibuang. `None` berarti tanpa saringan. Masukan boleh teks tempel, bytes `.txt`, bytes `.zip`, atau berkas terbuka. Format tak dikenal melempar `FormatTidakDikenal` (kode API `format_file_tidak_dikenal`).
- **Sidik**: `sha256(waktu dibulatkan ke menit + pengirim + isi + urutan)`. `urutan` adalah nomor urut pesan kembar (pengirim dan isi sama) di menit yang sama. Unik per batch di tabel `messages`.
- **`anonymize(text)`**: nomor telepon menjadi `[nomor]`, surel menjadi `[email]`, deret 10 digit atau lebih (rekening, NIK) menjadi `[angka]`. Nama pengirim berupa nomor ikut disamarkan sebelum ke LLM, tetapi di DB tetap asli untuk penjual.
- **`extract_orders(..., active_order)`**: `active_order` yang dikirim ke ekstraktor berisi `jam_kirim`, `alamat`, `catatan`, dan `items` (`product_id`, `teks_asli`, `qty`, `catatan_item`). **Tanpa harga dan tanpa total.** Untuk intent `ubah`, `items` adalah **daftar akhir lengkap** pesanan; `items` kosong berarti item tidak berubah (hanya jam/alamat/catatan).
- **`apply_intent(order_context, extraction)`**: bentuk `order_context` ada di docstring `backend/app/rules/engine.py` (`catalog`, `active_order`, `terpakai`, `ambang_jumlah_tidak_wajar`). Hasilnya selalu `perlu_cek` (atau `batal`); pesanan yang sudah dikonfirmasi lalu diubah pembeli kembali ke `perlu_cek`.
- **Impor**: `services.import_batch(db, batch_id, file_or_text, extractor=None)`. Ekstraktor yang gagal untuk sebagian pengirim menghasilkan pesanan bertanda `gagal_diekstrak`, impor tetap lanjut. Bila gagal untuk **semua** pengirim, impor dibatalkan tanpa menyimpan apa pun dan melempar `EkstraksiGagalTotal` (kode API `kuota_llm_habis` untuk HTTP 429 dari penyedia, selain itu `llm_gagal`), supaya penjual bisa mengulang. Syaratnya ekstraktor **melempar galat** saat penyedia utama dan cadangan sama-sama gagal, bukan mengembalikan `gagal=True`. Dua impor bersamaan ke batch yang sama: yang kalah melempar `ImporBentrok` (HTTP 409, kode `impor_bentrok`).
- **Rekap**: `services.build_recap(db, batch_id)` dan `services.build_shopping_list(db, batch_id)`. Hanya pesanan yang disetujui (`dikonfirmasi`, `dibayar`, `dikirim`) yang dihitung. `Recap` mendapat tambahan `menunggu_persetujuan` (jumlah pesanan `perlu_cek`). `belum_bayar` = pesanan berstatus `dikonfirmasi`.
- **DB**: model di `backend/app/db/models.py`, sesi lewat `get_db` (API) dan `get_readonly_session()` (agen; database menolak tulis). Tabel dibuat `init_db()` saat aplikasi mulai, belum memakai alat migrasi.

## Keamanan

- Harga tidak dikirim ke LLM, tidak diterima dari LLM.
- `product_id` dari LLM divalidasi terhadap DB, id tak dikenal menjadi `null`.
- Isi chat diperlakukan sebagai data, bukan instruksi.
- Agen: tool hanya baca, DB read-only, guardrail di system prompt.
- Kredensial hanya di `.env`.
