# Rekapesan: panduan untuk Claude

Perekap pesanan pre-order (PO) makanan dari grup WhatsApp untuk penjual rumahan. Dibuat untuk **LOGICODIX 2026** (HIMTI UNESA), kategori Web, subtema Local MSME and Creative Economy.
**Code freeze: 14 November 23.59 WIB.** Tidak ada commit setelahnya. Submit di `logicodik2026.site`.

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
| Raihan (ketua) | Backend ringan: CRUD API, auth, templat balasan, deploy, integrasi, submission. Waktu terbatas dan masih pemula, jelaskan kode dengan sederhana | `backend/app/api`, `core` |
| Satria | Backend: skema DB, rules, orkestrasi impor, rekap, parser WA, sidik, anonimisasi, data uji. Jalur kritis: skema DB duluan | `backend/app/db`, `rules`, `services`, `parser`, `sample/` |
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

- Satu orang satu akun GitHub. Cabang per fitur (`feat/parser-wa`, `feat/extractor`, `feat/review-screen`), PR ke `main`, dibaca satu orang lain.
- Pesan commit deskriptif dengan awalan `feat:`, `fix:`, `docs:`, `test:`, `refactor:`. **Dilarang** `update`, `final`, `wip`.
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
