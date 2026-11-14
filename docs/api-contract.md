# Kontrak API Rekapesan (v1)

Pemilik kontrak: **Raihan**. Perubahan harus disepakati lewat PR yang mengubah berkas ini, karena Amad membangun FE (dan mock) dari sini.

Basis: `/api`. Format: JSON. Autentikasi: header `Authorization: Bearer <token>` kecuali `/auth/login`, `/auth/register`, dan `/health`. Uang dalam rupiah (integer). Waktu ISO 8601.

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
| `katalog_kosong` | 409 | Impor ditolak karena akun belum punya menu aktif. FE sebaiknya mengarahkan ke Katalog |
| `kuota_llm_habis` | 429 | Kuota model habis |
| `llm_gagal` | 502 | Model atau penyedia tidak bisa dihubungi, atau fitur AI belum tersedia |

Untuk impor, `kuota_llm_habis` dan `llm_gagal` hanya muncul bila ekstraksi gagal **untuk semua pengirim**. Dalam kasus itu **tidak ada yang disimpan**, jadi impor aman diulang. Bila hanya sebagian pengirim gagal, impor berhasil dan pesanan pengirim itu bertanda `gagal_diekstrak`.

## Autentikasi

| Method | Path | Isi |
| --- | --- | --- |
| POST | `/auth/login` | `{username, password}` → `{token}` (berlaku 12 jam) |
| POST | `/auth/register` | `{username, password, nama_toko?}` → 201 `{token}`. Username 3-32 karakter `a-z 0-9 _ .` (disimpan huruf kecil), kata sandi minimal 8 karakter, nama toko 2-60 karakter (spasi berlebih dirapikan). 422 `validasi_gagal` bila tidak sah, 409 `username_dipakai` bila sudah ada (termasuk nama akun demo) |
| GET | `/auth/me` | `{username, nama_toko}`. `nama_toko` bisa `null` (akun lama atau belum diisi). Wajib login |
| PATCH | `/auth/me` | `{nama_toko}` → `{username, nama_toko}`. Kosong → 422. Akun demo → 409 (diatur lewat `.env`) |
| GET | `/health` | `{status: "ok"}` |

`nama_toko` opsional di API supaya klien lama tetap bisa daftar, tetapi **layar Daftar mewajibkannya**. Bila `GET /auth/me` mengembalikan `nama_toko: null`, FE sebaiknya meminta penjual mengisinya (lalu `PATCH /auth/me`). Nama toko dipakai di balasan konfirmasi.

Akun demo diatur lewat `DEMO_USERNAME`, `DEMO_PASSWORD`, dan `DEMO_NAMA_TOKO` di `.env`. Akun hasil register disimpan di tabel `users`, kata sandi di-hash PBKDF2-SHA256. Token ditandatangani dengan `APP_SECRET_KEY`.

**Data terpisah per akun.** Katalog dan batch punya `pemilik` (username di token). Pesanan, pembeli, pesan mentah, rekap, bukti bayar, dan agen ikut pemilik batch-nya. Data akun lain dijawab 404 `tidak_ditemukan`. Database lama tanpa kolom `pemilik` diberi kolom itu saat server mulai, dan datanya diserahkan ke akun demo.

Login akun demo **dimatikan** (401 `tidak_terautentikasi` dengan pesan yang menyebut isian `.env` yang kurang) bila `DEMO_PASSWORD` kosong. Semua login dan register dimatikan bila:

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

### Menu dipesan tapi belum ada di katalog

| Method | Path | Isi |
| --- | --- | --- |
| GET | `/menu-belum-dikenal` | `[{kunci, nama, jumlah_pesanan, total_porsi, contoh}]`: item pesanan (belum batal) tanpa `product_id`, dikelompokkan kode (huruf kecil, tanpa angka dan kata pengisi seperti "porsi", "ya", "kak") |
| POST | `/menu-belum-dikenal/tambahkan` | `{kunci, nama, harga, stok_harian?}` → 201 `{menu, pesanan_dicocokkan}`. Menu dibuat dengan harga dari penjual (alias = `kunci`), lalu item lama yang kuncinya sama diberi `product_id` dan harga, total dan tanda kuning dihitung ulang. 409 bila menu aktif bernama sama sudah ada |

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

`tanggal_mulai` adalah tanggal chat PO dibuka (boleh kosong). Saat impor, pesan sebelum `tanggal_mulai` dan sesudah `tanggal_kirim` dibuang. Tidak boleh setelah `tanggal_kirim`.

## Impor

| Method | Path | Isi |
| --- | --- | --- |
| POST | `/batches/{id}/import` | `multipart/form-data` dengan `file` (.txt/.zip) atau `text`, **atau** JSON `{text}`. Maksimal 20 MB |

Respons:

```json
{ "pesan_baru": 42, "pesan_dilewati": 130, "pesanan_dibuat": 11, "pesanan_diubah": 2, "perlu_cek": 4 }
```

Impor ulang aman: pesan yang sudah pernah masuk dilewati (`pesan_dilewati`) dan tidak membuat pesanan dobel. Kemungkinan galat: `tidak_ditemukan`, `katalog_kosong`, `format_file_tidak_dikenal`, `validasi_gagal` (kosong atau lebih dari 20 MB), `impor_bentrok`, `kuota_llm_habis`, `llm_gagal`.

`katalog_kosong` (409) dikembalikan bila akun belum punya satu pun menu aktif. Pemeriksaan ini terjadi sebelum berkas dibaca, jadi tidak ada pesan yang disimpan dan LLM tidak dipanggil. Tanpa menu, semua pesanan akan bertanda `item_tidak_dikenal` dan harganya tidak bisa dihitung.

Share target PWA: service worker menerima berkas dari menu Bagikan dan meneruskannya ke endpoint di atas (batch aktif atau batch baru yang dipilih pengguna).

### Buku pesanan harian

Alur utama baru: penjual cukup memasukkan chat, tanpa membuat PO dulu. Endpoint per batch di atas tetap jalan.

| Method | Path | Isi |
| --- | --- | --- |
| POST | `/impor/pratinjau` | Body sama dengan impor. Tidak menyimpan apa pun dan tidak memanggil LLM |
| POST | `/impor` | Body sama dengan impor. Satu batch per tanggal chat (maks 14 hari terakhir), lalu impor tiap hari |
| GET | `/ringkasan` | Papan pesanan: keseluruhan, per hari, per jam |

`POST /impor` menerima query opsional `penjual` (nama pengirim penjual di chat; pesannya disimpan tapi tidak diekstrak sebagai pesanan, untuk chat satu lawan satu tanpa daftar menu) dan `baca_bukti=true` (.zip dengan media: foto dari pembeli yang punya pesanan di hari itu, maksimal 30, dibaca `read_payment_proof`; hasilnya `Payment` belum dikonfirmasi dengan `berkas` = nama foto, sehingga impor ulang tidak membacanya lagi). Respons menambah `bukti_terbaca`. `/impor/pratinjau` menambah `pengirim` (semua pengirim, terbanyak dulu).

Jenis `saran` di `/ringkasan`: `sudah_bayar`, `sudah_terima` (dari pembeli, atau "Penjual bilang sudah diantar" bila hari itu hanya ada satu pembeli), `bukti_transfer` (foto bukti: nominal dan cocok/beda dengan total), `bayar_dobel` (informasi saja, mis. "kebayar 2 kali"). Semua tetap hanya saran.

`/impor/pratinjau`:

```json
{ "penjual": "Ratri", "tanggal_awal": "2026-11-14", "tanggal_akhir": "2026-11-16", "jumlah_pesan": 19,
  "hari": [{ "tanggal": "2026-11-14", "jumlah_pesan": 16 }],
  "menu": [{ "nama": "Nasi Ayam Bawang Putih", "harga": 17000, "sudah_ada": false, "product_id": null }] }
```

Dibaca kode, bukan LLM. Pesan dianggap daftar menu bila memuat **minimal dua harga** ("17rb", "17 ribu", "17k", "17.000", "Rp17.000"), jadi pesan seperti "ubah harga jadi 1000" tidak terbaca sebagai menu. Angka di bawah 1000 tanpa "rb"/"k" dianggap jumlah. `penjual` = pengirim dengan pesan daftar menu terbanyak (bisa `null`). Menu disimpan penjual lewat `POST /products`. Harga selalu ditentukan penjual. `menu_dari_pembeli` (`[{nama, jumlah_sebut, contoh}]`): tebakan kode dari pesan pembeli, yaitu kata-kata tepat sebelum/sesudah sebuah jumlah ("geprek 2", "2 risol mayo") yang tidak cocok dengan daftar menu penjual, katalog, maupun alias. Kata alamat/waktu (jam, blok, Jl., kamar, lt) disaring. Ditampilkan tanpa centang dan tanpa harga, penjual yang memutuskan.

`/impor`:

```json
{ "hari": [{ "tanggal": "2026-11-14", "batch_id": "uuid", "nama": "Sabtu, 14 Nov", "pesan_baru": 16, "pesan_dilewati": 0, "pesanan_dibuat": 7, "pesanan_diubah": 0, "perlu_cek": 3 }],
  "total": { "pesan_baru": 16, "pesan_dilewati": 0, "pesanan_dibuat": 7, "pesanan_diubah": 0, "perlu_cek": 3 } }
```

Batch harian adalah batch biasa (`tanggal_mulai` = `tanggal_kirim` = tanggal itu), dipakai ulang bila sudah ada, jadi layar Cek, Rekap, dan agen tetap bekerja per hari. Hari baru yang tidak menghasilkan pesanan (mis. hanya obrolan penjual) tidak disimpan. Galat sama dengan impor per batch. Bila LLM gagal di tengah, hari yang sudah selesai tetap tersimpan dan impor ulang aman.

`/ringkasan`:

```json
{ "keseluruhan": { "perlu_cek": 3, "diproses": 2, "selesai": 1, "batal": 1, "omzet": 150000, "belum_bayar": 85000, "jumlah_belum_bayar": 2 },
  "hari": [{ "tanggal": "2026-11-15", "batch_id": "uuid", "nama": "Minggu, 15 Nov",
    "jam": [{ "jam": "11:30", "pesanan": [{
      "id": "uuid", "nama": "Bu Wulan", "status": "perlu_cek", "status_papan": "perlu_cek", "bayar": "belum",
      "total": 48000, "jam_kirim": "11:30", "alamat": "Perum ...", "items": [{ "nama": "Nasi Ayam Bawang Putih", "qty": 2 }],
      "tanda": [], "saran": [{ "jenis": "sudah_bayar", "teks": "Pembeli bilang sudah bayar", "kutipan": "udah transfer ya kak" }] }] },
      { "jam": null, "pesanan": [] }] }] }
```

`status_papan`: `perlu_cek`, `diproses` (`dikonfirmasi`/`dibayar`), `selesai` (`dikirim`), `batal`. `bayar`: `lunas` bila status `dibayar` atau pelunasan sudah dikonfirmasi, selain itu `belum`. `omzet` dan `belum_bayar` hanya dari pesanan yang disetujui. `jam: null` berarti jam kirim belum ada. `saran` dibaca kode dengan kata kunci dari pesan pembeli ("udah transfer", "bukti tf", "udah sampai", "sudah diterima") dan **tidak pernah mengubah status**. Penjual yang menekan tombol (`payment-confirm` atau `PATCH status: dikirim`).

## Pesanan dan review

| Method | Path | Isi |
| --- | --- | --- |
| GET | `/batches/{id}/orders?status=` | daftar `Order` (status tidak dikenal → 422) |
| GET | `/orders/{id}` | `Order` lengkap + `pesan_sumber` |
| PATCH | `/orders/{id}` | ubah `items`, `alamat`, `jam_kirim`, `catatan`, `status` (semua opsional) |
| POST | `/orders/{id}/approve` | setujui (`perlu_cek` → `dikonfirmasi`). Pesanan batal → 409 |
| POST | `/orders/{id}/reject` | tolak (→ `batal`). Pesanan `dibayar` atau `dikirim` → 409 |
| POST | `/batches/{id}/orders/approve-clean` | setujui semua `perlu_cek` yang tanpa tanda. Respons `{disetujui, masih_bertanda}` |
| GET | `/orders/{id}/reply` | `{teks}` balasan konfirmasi dari templat ("Halo Bu Rina, pesanan kamu di *nama toko* sudah kami catat ya: …"; tanpa "di …" bila nama toko kosong). Hanya untuk pesanan yang sudah disetujui, selain itu 409 |

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
- Stok dibagi menurut urutan pesanan masuk: pesanan diberi `stok_kurang` hanya bila pesanan yang masuk lebih dulu (dan belum batal) ditambah dirinya melebihi stok. Setiap ubah, tolak, atau buka lagi menghitung ulang tanda `stok_kurang` semua pesanan di batch, jadi `tanda` pesanan lain bisa ikut berubah.
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
| POST | `/orders/{id}/payment-confirm` | penjual mengonfirmasi lunas. Pesanan `dikonfirmasi` → `{order_id, status: "dibayar"}`. Pesanan `dikirim` (mis. COD) tetap `dikirim`, pelunasan dicatat di tabel payments sehingga `bayar` di ringkasan jadi `lunas`. Status lain 409 |

Model hanya memberi saran. `cocok` dihitung kode (nominal sama dengan total pesanan). Status berubah hanya setelah `payment-confirm`. Bila pembaca gambar gagal atau belum tersedia, respons `llm_gagal` (502) dan penjual bisa langsung memakai `payment-confirm`.

## Agen tanya-jawab

| Method | Path | Isi |
| --- | --- | --- |
| POST | `/agent/ask` | `{pertanyaan, riwayat: [], batch_id?}`. Tanpa `batch_id`, agen membaca semua hari milik akun (14 terbaru) dan menyaring sendiri lewat argumen tool `tanggal` (YYYY-MM-DD dari daftar hari yang dipilih kode, bukan id batch). Dengan `batch_id`, hanya batch itu |
| GET | `/agent/percakapan` | Riwayat Tanya AI milik akun: `[{id, judul, diubah_pada, berakhir_pada, jumlah_pesan}]`, terbaru dulu |
| GET | `/agent/percakapan/{id}` | `{id, judul, berakhir_pada, pesan: [{peran, isi, trace}]}` |
| DELETE | `/agent/percakapan/{id}` | Hapus satu percakapan (204) |

`/agent/ask` menerima `percakapan_id` opsional. Tanpa itu, percakapan baru dibuat (judul = pertanyaan pertama). Dengan itu, riwayat untuk LLM dibaca dari server (6 pesan terakhir), bukan dari `riwayat` kiriman klien. Respons menyertakan `percakapan_id`. Tanya-jawab disimpan hanya bila agen berhasil menjawab. Percakapan **terhapus otomatis 30 hari setelah pesan terakhir** (dijalankan setiap riwayat dibuka atau pertanyaan dikirim). Agen punya tool read-only `cari_riwayat_tanya(kata_kunci)` untuk membaca percakapan lain milik akun yang sama (yang belum kedaluwarsa, tanpa percakapan yang sedang berjalan); pemilik ditetapkan kode, isi riwayat diperlakukan sebagai data.

```json
{ "jawaban": "Ayam bakar untuk jam 12:00: 9 porsi.",
  "trace": [{ "tool": "rekap_produksi", "argumen": {"batch_id": "uuid", "jam": "12:00"}, "hasil_ringkas": "...", "hasil": { "produksi": [], "total_porsi": 0, "...": "..." } }] }
```

Bila agen gagal atau belum tersedia, respons `llm_gagal` (502).

## Pengaturan

| Method | Path | Isi |
| --- | --- | --- |
| GET/PATCH | `/settings` | `{ambang_jumlah_tidak_wajar: 20}` |

**Belum tersedia.** Sementara ini ambang diambil dari `JUMLAH_TIDAK_WAJAR_DEFAULT` di `.env`. Endpoint ini menunggu tabel pengaturan dari modul DB.
