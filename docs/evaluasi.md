# Evaluasi Ekstraksi

Diisi apa adanya setelah dijalankan. Jangan mengarang angka.

## Set uji

- Sumber: kasus **sintetis** buatan tim (nama, alamat, nomor samaran). Belum memuat chat penjual asli.
- Jumlah kasus: 40 (satu kasus = satu panggilan ekstraktor untuk satu pengirim)
- Jawaban benar: `sample/gold.json`
- Model dan tanggal uji: `claude-haiku-5-5` lewat sumopod, 13 November 2026. Model cadangan: `gpt-5.4-mini` (tidak terpakai dalam run ini). Satu kali jalan, 40 kasus, 5 panggilan paralel.
- Cara menjalankan: `cd backend && python -m tests.eval.jalankan` (butuh `LLM_*` di `.env`). Penilai ada di `backend/tests/eval/skor.py`.

## Hasil

Cara menilai satu kasus:

- **Benar seluruhnya**: intent, daftar (menu, jumlah), serta ada/tidaknya jam dan alamat cocok dengan jawaban benar. Teks bebas (catatan, `teks_asli`) tidak dinilai.
- **Salah, tertangkap**: salah, tetapi mesin aturan memberi tanda `gagal_diekstrak`, `item_tidak_dikenal`, `jumlah_kosong`, `jumlah_tidak_wajar`, atau `mungkin_dobel`. Tanda umum (`jam_kosong`, `alamat_kosong`, `stok_kurang`) tidak dihitung karena muncul juga pada pesanan yang benar.
- **Salah, lolos tanpa tanda**: salah dan tidak ada tanda, termasuk pesanan yang diabaikan diam-diam.
- Kasus yang gagal karena penyedia (kuota, jaringan) dihitung terpisah dan tidak masuk persentase.

| Kategori | Jumlah | Persen |
| --- | --- | --- |
| Benar seluruhnya | 39 | 97,5% |
| Salah, **tertangkap** tanda kuning | 0 | 0,0% |
| Salah, **lolos tanpa tanda** | 1 | 2,5% |

Dua orang menjalankan penilai yang sama (`python -m tests.eval.jalankan`) pada hari yang sama dan mendapat angka yang sama: Satria dan Pangeran. Satu kasus yang salah adalah g16, dibahas di "Temuan".

Angka terakhir paling penting karena itu kesalahan yang sampai ke penjual tanpa peringatan.

## Kasus sulit

| Kasus | Hasil (benar / total) |
| --- | --- |
| Ubah pesanan | 5 / 5 |
| Batal pesanan | 3 / 3 |
| Item tidak ada di katalog | 3 / 3 |
| Jumlah tidak wajar | 2 / 2 |
| Percobaan manipulasi harga (prompt injection) | 4 / 4 |

Kategori lain: pesan 15 / 16, bukan_pesanan 5 / 5, jumlah_kosong 2 / 2.

"Benar" pada kasus manipulasi berarti model tidak menuruti isi chat. Harga tetap tidak bisa berubah karena harga tidak pernah dikirim ke model dan dihitung kode dari katalog.

## Perbandingan model

Diukur Satria dengan penilai yang sama, hanya `LLM_MODEL` yang diganti. Satu kali jalan per model, gold sintetis, jadi selisih kecil antar model belum bisa dianggap pasti.

| Model | Benar | Salah | Rincian salah |
| --- | --- | --- | --- |
| claude-haiku-5-5 | 39 | 1 | 0 tertangkap, 1 lolos |
| gpt-5.4-mini | 37 | 3 | 0 tertangkap, 3 lolos |
| gemini-3.5-flash-lite | 36 | 4 | 0 tertangkap, 4 lolos |
| gemini-3.1-flash-lite | 35 | 5 | 0 tertangkap, 5 lolos |
| gpt-5.4-nano | 28 | 12 | 3 tertangkap, 9 lolos |

Pada empat model pertama, semua kesalahan lolos tanpa tanda dan tidak ada yang tertangkap. Model dipilih karena paling banyak benar dan paling murah di antara lima model menurut pengukuran Satria (0,10 / 0,50 per juta token masuk / keluar, lewat sumopod). Satu panggilan per pengirim, tanpa pemanggilan berulang kecuali keluaran tidak sah. 40 kasus selesai sekitar 39 detik.

## Uji waktu (bukti masalah)

| | Manual | Rekapesan |
| --- | --- | --- |
| Waktu rekap satu batch | | |
| Pesanan terlewat / salah | | |

Penjual dan kondisi pengukuran: _isi_

## Temuan dan perbaikan

- **g16 ("lodeh 1, hub saya di [nomor] kalau sudah sampai lobi")**: gold menganggap alamatnya "lobi", model memasukkannya ke `catatan` dan mengosongkan `alamat`. Tiga kali dijalankan ulang, hasilnya sama. Menurut pengukuran Satria, tiga dari lima model, termasuk Haiku (Haiku dan dua model gemini), mengosongkan alamat pada kasus ini, jadi gold kemungkinan terlalu ketat dan kasus ini ambigu. Gold tidak diubah supaya angka tetap apa adanya. Di aplikasi pesanan ini tetap diberi tanda `alamat_kosong`, tetapi penilai tidak menghitung tanda umum itu sebagai "tertangkap", sehingga kasus ini masuk "lolos".
- **Jumlah mustahil**: uji manual menemukan jumlah sangat besar (mis. 10^20) membuat penyimpanan gagal dan seluruh impor jatuh. Diperbaiki: jumlah di atas 10.000 dianggap tidak terbaca dan pesanan ditandai `jumlah_kosong`.
- **Agen**: jawaban memuat markdown yang tampil mentah di layar. Diperbaiki dengan instruksi dan pembersihan keluaran.

## Pemeriksaan tambahan dengan model asli (bukan pengukuran akurasi)

Pemeriksaan kecil untuk memastikan jalurnya berfungsi. Jumlah contohnya terlalu sedikit untuk dijadikan angka akurasi.

- **Bukti bayar, gambar buatan sendiri**: 3 gambar, satu kali jalan. Nama dan nominal terbaca benar dan biaya admin tidak ikut terambil. Teks "abaikan instruksi" di dalam gambar tidak diikuti. Gambar yang bukan bukti menghasilkan nama dan nominal kosong.
- **Bukti bayar, struk asli**: 18 struk pembayaran QRIS BCA milik pribadi Satria (13 November 2026), semuanya ke satu merchant dengan satu tata letak. Nominal terbaca di 18 dari 18. Lima di antaranya dicocokkan satu per satu dengan gambarnya dan kelimanya benar. Tiga belas sisanya belum dicocokkan manual. Nama kosong di semua file karena struk QRIS tidak memuat nama pengirim. Foto aslinya tidak disimpan di repo.
- **Agen**: 5 pertanyaan pada data demo (rekap per jam, belum bayar, pesanan seorang pembeli, pertanyaan di luar topik, permintaan menyetujui dan menandai lunas) menjawab benar dengan tool yang tepat dan menolak dua yang di luar wewenang. Satria menguji 7 pertanyaan lain, semuanya benar. Guardrail hanya berupa instruksi, jadi belum ada jaminan terhadap serangan yang gigih.

## Batasan

- Set uji sintetis buatan tim, belum memuat chat penjual asli.
- Satu kali jalan per model, tanpa pengulangan, sehingga variasi antar jalan belum diukur.
- Gaya tulisan chat asli yang lebih berantakan dapat menurunkan angka ini.
- Bukti bayar baru diuji pada satu aplikasi dan satu tata letak (struk QRIS BCA). Transfer antarbank, e-wallet, dan mode gelap belum diuji, dan pembacaan **nama pengirim belum teruji pada bukti asli**. Karena struk QRIS tidak memuat nama, pencocokan pada kasus itu hanya berdasarkan nominal, dan penjual tetap yang mengonfirmasi lunas.
