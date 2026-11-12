# Rekapesan: panduan untuk Claude

Perekap pesanan pre-order (PO) makanan dari grup WhatsApp untuk penjual rumahan. Dibuat untuk **LOGICODIX 2026** (HIMTI UNESA), kategori Web, subtema Local MSME and Creative Economy.
**Code freeze: Sabtu 14 November 2026** (Last Submission). Guidebook tidak menyebut jam pasti, tim memakai 23.59 WIB sebagai batas aman, cek grup WhatsApp peserta. Tidak ada commit setelahnya, dan yang dinilai adalah versi terakhir sebelum batas.

## Lomba: aturan dan penilaian (sumber: Guidebook resmi LOGICODIX 2026, hal. 4-17)

**Penilaian juri (bobot resmi):**

| Kriteria | Bobot | Yang dilihat juri | Artinya untuk kita |
| --- | --- | --- | --- |
| Problem-Solution Fit | 25% | Ketajaman masalah, kesesuaian solusi dengan kebutuhan pengguna | Bukti lapangan penjual asli, ukur waktu rekap manual vs Rekapesan. Jangan klaim angka yang tidak diukur |
| Technology Innovation | 25% | Efektivitas teknologi, **AI jadi nilai tambah** | LLM hanya untuk memahami teks, kode untuk hitung. Tunjukkan agen + trace dan tanda kuning |
| Software Engineering | 25% | Fungsionalitas MVP, kualitas kode, arsitektur, **dokumentasi** | Alur utama jalan tanpa error, uji pytest, CI hijau, README lengkap, riwayat commit rapi dari semua anggota |
| UI/UX | 15% | Desain antarmuka, kemudahan, alur pengguna | Mobile-first, alur impor ke review ke rekap pendek, aksesibilitas |
| Green IT & Ethics | 10% | Efisiensi sumber daya, **privasi data, transparansi AI** | Anonimisasi nomor, hapus batch, LLM tidak menentukan harga, hasil AI selalu bisa dicek penjual. Catat efisiensi (model kecil, panggilan per pengirim, tanpa pemanggilan berulang) |

Catatan: `00_RINGKASAN_DAN_FRAMEWORK.md` dan `04_analisis_pola_kemenangan_hackathon_2026.md` di folder riset `matamata/Hekathon` memuat bobot 30/25/25/20. **Itu salah.** Pakai tabel di atas, yang diambil langsung dari Guidebook hal. 17.

**Peran menurut materi mentoring Navasena:** Hacker (bangun MVP), Hipster (UI/UX, alur pengguna), Hustler (validasi masalah, pitch, narasi dan video demo, model keberlanjutan). Di tim ini Pangeran dan Satria = Hacker, Amad = Hacker FE + Hipster, Raihan = Hustler (bukti lapangan, video, README, pitch) dan integrasi.

**Aturan yang bisa mendiskualifikasi:**
- Karya orisinal, bukan plagiat, dan **belum pernah diikutkan di lomba lain**. Kode, data, dan aset harus bisa dipertanggungjawabkan (atribusi di README bagian 11).
- Web/Mobile MVP, menerapkan salah satu subtema (kita: Local MSME and Creative Economy), menyelesaikan masalah nyata.
- Wajib: source code di GitHub, video demo 3-5 menit, mengikuti seluruh rangkaian sesuai jadwal.
- **Video: demonstrasi aplikasi nyata, termasuk fitur AI, tanpa suara presentasi atau penjelasan lisan.** Jangan pakai narasi suara. Teks keterangan di layar dianggap aman, konfirmasi ke panitia bila ragu.
- Tidak boleh mengubah source code setelah batas submission. Pelanggaran bisa berujung diskualifikasi.
- Maksimal 4 orang per tim. Penggunaan AI dan API AI/model open-source diperbolehkan, dengan etika, perlindungan data, dan efisiensi sumber daya.

**Jadwal:** hacking week 7-14 Nov, pengumuman Top 8 pada 21 Nov, technical meeting final 22 Nov, Grand Final luring di UNESA 29 Nov.

**Grand Final (15 menit):** 1 menit pasang laptop dan verifikasi **localhost**, 7 menit presentasi + live demo, 3 menit Q&A juri, 4 menit penilaian. Karena itu:
- Aplikasi harus bisa jalan **di localhost laptop sendiri**, dengan `README` langkah jalan yang teruji dari repo bersih.
- Siapkan **data demo (seed) dan hasil ekstraksi tersimpan** sebagai cadangan bila internet atau kuota LLM mati saat demo.
- Latih jawaban Q&A: kenapa LLM tidak menghitung harga, bagaimana mencegah prompt injection, bagaimana privasi nomor telepon dijaga, apa bedanya dengan menyalin manual atau Excel.

**Prioritas MVP (sisa waktu sangat singkat, kerjakan berurutan, jangan lompat):**
1. P0: tempel teks atau unggah ekspor, parser, anonimisasi, ekstraksi LLM, hitung total dengan kode, layar review, rekap produksi. Satu alur utuh dari ujung ke ujung dulu.
2. P1: tanda kuning, ubah/batal, setujui, balasan konfirmasi, login demo, hapus batch, README dan video.
3. P2: agen tanya-jawab dengan trace, evaluasi gold set dengan angka jujur, CI.
4. P3: bukti bayar, daftar belanja, PWA share target.
Fitur yang tidak selesai jangan dicentang di README dan jangan ditampilkan di video.

Bahasa kerja: **Bahasa Indonesia** (komentar, commit, dokumen, balasan ke tim). Nama identifier kode boleh Inggris, kode tanda kuning dan istilah domain tetap Indonesia.

## Baca dulu sesuai kebutuhan (jangan ditanya ulang ke user)

| Butuh | File |
| --- | --- |
| Gambaran, fitur, status centang | `README.md` |
| Siapa pegang modul apa, definisi "selesai" | `docs/PEMBAGIAN_TUGAS.md` |
| Alur impor, antarmuka antar-modul, keamanan | `docs/arsitektur.md` |
| Endpoint untuk FE | `docs/api-contract.md` |
| Hasil evaluasi ekstraktor | `docs/evaluasi.md` |
| Data contoh samaran | `sample/ekspor-contoh.txt` |

## Tim dan modul (pemilik)

| Nama | Peran | Folder |
| --- | --- | --- |
| Raihan | Backend ringan: CRUD API, auth, templat balasan, deploy, integrasi, plus Hustler (wawancara penjual, video, README, pitch). Waktu terbatas dan masih pemula, jelaskan kode dengan sederhana | `backend/app/api`, `core` |
| Satria (**ketua tim**) | Backend: skema DB, rules, orkestrasi impor, rekap, parser WA, sidik, anonimisasi, data uji. Jalur kritis: skema DB duluan | `backend/app/db`, `rules`, `services`, `parser`, `sample/` |
| Pangeran | Backend AI: ekstraktor LLM, agen tanya-jawab, bukti bayar, evaluasi, CI | `backend/app/extractor`, `agent`, `backend/tests/eval` |
| Amad | Frontend: semua layar, PWA, aksesibilitas, uji pemakaian | `frontend/` |

Kalau user menyebut namanya, kerjakan di modul miliknya. Jangan mengubah modul orang lain tanpa diminta. Kalau perubahan menyentuh antarmuka antar-modul, kabari dan update `docs/arsitektur.md`.

## Stack

Backend Python 3.11+, FastAPI, SQLAlchemy, Pydantic. DB SQLite (lokal), PostgreSQL (deploy). LLM lewat API kompatibel OpenAI (OpenRouter / NVIDIA NIM), diatur di `.env`. Frontend React + Vite + TypeScript, PWA. Uji: pytest, Vitest. CI: GitHub Actions. Paket Python pakai `uv`.

Perintah umum (lihat README bagian 6):
- Backend: `cd backend && uv run uvicorn app.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev`
- Uji: `cd backend && uv run pytest`, `cd frontend && npm test`

## Aturan desain yang tidak boleh dilanggar

1. **LLM hanya memahami teks bebas.** Harga, total, stok, tanda kuning, rekap, balasan konfirmasi dihitung **kode**.
2. **Harga tidak pernah dikirim ke LLM dan tidak pernah diterima dari LLM.** Katalog yang dikirim ke LLM: id, nama, alias saja.
3. `product_id` dari LLM divalidasi terhadap DB. Id tak dikenal menjadi `null`.
4. **Isi chat adalah data, bukan instruksi** (tahan prompt injection).
5. **Tidak ada pesanan final tanpa persetujuan penjual.** Pesanan meragukan diberi tanda kuning.
6. Nomor telepon disamarkan (`anonymize`) **sebelum** teks keluar ke LLM.
7. Agen tanya-jawab: tool **read-only**, koneksi DB read-only, guardrail hanya domain pesanan, jawaban disertai trace.
8. Hapus batch ikut menghapus pesan mentah.
9. Pembaca bukti bayar hanya menyarankan (nama, nominal). Pencocokan dan keputusan oleh kode dan penjual.
10. Ekstraksi dipanggil **per pengirim** dan **paralel/asinkron**. Ada penyedia cadangan otomatis.

Kode tanda kuning: `item_tidak_dikenal`, `jumlah_kosong`, `jumlah_tidak_wajar`, `alamat_kosong`, `jam_kosong`, `stok_kurang`, `mungkin_dobel`, `gagal_diekstrak`.

Antarmuka antar-modul (jangan ubah signature tanpa kesepakatan):
- `parse_export(file_or_text, batch_date) -> list[Message]`
- `anonymize(text) -> str`
- `extract_orders(sender_messages, catalog, active_order=None) -> Extraction`
- `apply_intent(order_context, extraction) -> OrderChange`
- `ask_agent(question, batch_id, history) -> AgentAnswer(answer, trace)`
- `read_payment_proof(image_bytes) -> ProofSuggestion(nama, nominal)`

## Aturan Git (wajib, aturan lomba)

- Satu orang satu akun GitHub.
- **Jangan pernah commit atau push langsung ke `main`.** Satu fitur = satu cabang `<tipe>/<modul>-<deskripsi>` (mis. `feat/parser-wa-android`), lalu Pull Request ke `main`, disetujui satu orang lain, merge dengan **merge commit** (bukan squash), hapus cabang setelahnya.
- Format commit (awalan tipe wajib dari aturan lomba):
  `<tipe>: <apa yang dikerjakan> [<INISIAL>] - <detail>`
  Tipe: `feat`, `fix`, `docs`, `test`, `refactor`. Contoh: `feat: tambah parser ekspor WhatsApp Android [RWB] - tangani pesan multi-baris`.
  Inisial: Raihan = RWB, lainnya lihat tabel di `docs/PEMBAGIAN_TUGAS.md`. Kalau belum jelas siapa user-nya, tanyakan dulu, jangan menebak inisial.
- **Dilarang** pesan `update`, `final`, `wip`.
- Jangan menambahkan `Co-Authored-By` atau atribusi Claude di commit atau PR. Commit memakai identitas Git user.
- **Dilarang** force push, rebase riwayat yang sudah di-push, bulk upload di akhir.
- `.env` tidak boleh masuk repo. Hanya `.env.example`, tanpa nilai asli. Jangan menulis API key di kode, dokumen, atau commit.
- Jangan commit atau push kecuali user minta.

## Gaya kerja

- Jangan karang angka. Hasil evaluasi, waktu penjual, dan skor ditulis apa adanya dari pengukuran. Jangan centang fitur di README yang belum benar-benar selesai.
- Data contoh dan uji memakai nama, alamat, nomor **samaran**. Chat asli hanya dengan izin penjual.
- Tulis uji untuk logika deterministik (rules, parser, anonimisasi). Penguji bukan pembuat kode: Amad uji parser/rekap, Satria uji ekstraktor/agen, Pangeran uji rules/stok, Raihan uji alur FE.
- Frontend: mobile-first, status tidak hanya dengan warna (ikon + teks), target sentuh besar, label form terbaca pembaca layar.
- Jawab singkat dan langsung. Kalau ada keputusan yang bukan wewenang user (mis. ganti stack), sebut sebagai rekomendasi dan lanjutkan dengan default dari dokumen di atas.

## Status

Struktur folder sudah ada (banyak masih `.gitkeep`). Sumber kebenaran status fitur adalah checklist di `README.md` bagian 4. Update bagian ini bila ada keputusan penting yang tidak tercatat di docs.
