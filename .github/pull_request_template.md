## Apa yang dikerjakan
<!-- Judul PR mengikuti format commit: <tipe>: <apa yang dikerjakan> [INISIAL] - <detail> -->

## Modul dan pemilik
<!-- Folder yang disentuh. Jika bukan modul sendiri, kabari pemiliknya. -->

## Cara menguji
<!-- Perintah atau langkah yang sudah dijalankan -->

## Checklist
- [ ] Cabang dibuat dari `main` terbaru, nama `<tipe>/<modul>-<deskripsi>`
- [ ] Pesan commit mengikuti format tim (bukan `update`, `final`, `wip`)
- [ ] Uji lolos (`pytest` / `npm test`) dan build lolos
- [ ] Tidak ada `.env`, kunci API, atau data pribadi asli di perubahan ini
- [ ] Aturan desain tidak dilanggar: LLM tidak menyentuh harga, isi chat diperlakukan sebagai data
- [ ] Dokumen diperbarui bila antarmuka atau kontrak API berubah
