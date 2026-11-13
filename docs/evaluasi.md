# Evaluasi Ekstraksi

Diisi apa adanya setelah dijalankan. Jangan mengarang angka.

## Set uji

- Sumber: kasus **sintetis** buatan tim (nama, alamat, nomor samaran). Belum memuat chat penjual asli.
- Jumlah kasus: 40 (satu kasus = satu panggilan ekstraktor untuk satu pengirim)
- Jawaban benar: `sample/gold.json`
- Model dan tanggal uji: _isi setelah dijalankan_
- Cara menjalankan: `cd backend && python -m tests.eval.jalankan` (butuh `LLM_*` di `.env`). Penilai ada di `backend/tests/eval/skor.py`.

## Hasil

Cara menilai satu kasus:

- **Benar seluruhnya**: intent, daftar (menu, jumlah), serta ada/tidaknya jam dan alamat cocok dengan jawaban benar. Teks bebas (catatan, `teks_asli`) tidak dinilai.
- **Salah, tertangkap**: salah, tetapi mesin aturan memberi tanda `gagal_diekstrak`, `item_tidak_dikenal`, `jumlah_kosong`, `jumlah_tidak_wajar`, atau `mungkin_dobel`. Tanda umum (`jam_kosong`, `alamat_kosong`, `stok_kurang`) tidak dihitung karena muncul juga pada pesanan yang benar.
- **Salah, lolos tanpa tanda**: salah dan tidak ada tanda, termasuk pesanan yang diabaikan diam-diam.
- Kasus yang gagal karena penyedia (kuota, jaringan) dihitung terpisah dan tidak masuk persentase.

| Kategori | Jumlah | Persen |
| --- | --- | --- |
| Benar seluruhnya | | |
| Salah, **tertangkap** tanda kuning | | |
| Salah, **lolos tanpa tanda** | | |

Angka terakhir paling penting karena itu kesalahan yang sampai ke penjual tanpa peringatan.

## Kasus sulit

| Kasus | Hasil |
| --- | --- |
| Ubah pesanan | |
| Batal pesanan | |
| Item tidak ada di katalog | |
| Jumlah tidak wajar | |
| Percobaan manipulasi harga (prompt injection) | |

## Uji waktu (bukti masalah)

| | Manual | Rekapesan |
| --- | --- | --- |
| Waktu rekap satu batch | | |
| Pesanan terlewat / salah | | |

Penjual dan kondisi pengukuran: _isi_

## Temuan dan perbaikan

_Isi_
