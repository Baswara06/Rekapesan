"""Uji penilai evaluasi (tanpa LLM): tiga kategori hasil dan galat penyedia dipisah."""

import asyncio

from app.schemas import ExtractedItem, Extraction
from tests.eval.skor import evaluasi, laporan_markdown, muat_gold, ringkas

GOLD = muat_gold()


def _kunci(isi_pesan, aktif):
    return (tuple(isi_pesan), repr(aktif))


JAWABAN = {
    _kunci([p["isi"] for p in k["pesan"]], k["pesanan_aktif"]): Extraction.model_validate(k["harapan"])
    for k in GOLD["kasus"]
}
assert len(JAWABAN) == len(GOLD["kasus"])  # kunci harus unik, kalau tidak oracle ambigu


async def oracle(pesan, _katalog, aktif=None):
    """Mengembalikan jawaban benar dari gold."""
    return JAWABAN[_kunci([m.isi for m in pesan], aktif)]


def jalankan(extractor):
    return asyncio.run(evaluasi(extractor, GOLD))


def test_penilai_memberi_semua_benar_untuk_jawaban_gold():
    n = ringkas(jalankan(oracle))
    assert n == {"benar": len(GOLD["kasus"])}


def test_salah_dengan_tanda_dihitung_tertangkap():
    async def ngawur(pesan, _k, _a=None):
        # id produk karangan: aturan menjadikannya null -> item_tidak_dikenal
        return Extraction(intent="pesan", items=[ExtractedItem(product_id="p-x", teks_asli="x", qty=1)])

    kasus = next(k for k in GOLD["kasus"] if k["id"] == "g01")
    hasil = asyncio.run(evaluasi(ngawur, {**GOLD, "kasus": [kasus]}))
    assert hasil[0].status == "tertangkap" and "item_tidak_dikenal" in hasil[0].tanda


def test_salah_tanpa_tanda_dihitung_lolos():
    async def diam(_p, _k, _a=None):
        return Extraction(intent="bukan_pesanan")  # pesanan hilang diam-diam

    kasus = next(k for k in GOLD["kasus"] if k["id"] == "g01")
    hasil = asyncio.run(evaluasi(diam, {**GOLD, "kasus": [kasus]}))
    assert hasil[0].status == "lolos" and "intent" in hasil[0].alasan


def test_jumlah_salah_yang_tampak_wajar_lolos():
    async def keliru(_p, _k, _a=None):
        return Extraction(intent="pesan", items=[ExtractedItem(product_id="p-ayam-bakar", teks_asli="ayam", qty=5)],
                          alamat="Blok C no 4")

    kasus = next(k for k in GOLD["kasus"] if k["id"] == "g01")
    assert asyncio.run(evaluasi(keliru, {**GOLD, "kasus": [kasus]}))[0].status == "lolos"


def test_gagal_diekstrak_tertangkap_dan_galat_penyedia_dipisah():
    async def gagal(_p, _k, _a=None):
        return Extraction(intent="bukan_pesanan", gagal=True)

    async def mati(_p, _k, _a=None):
        raise RuntimeError("kuota habis")

    kasus = {**GOLD, "kasus": [GOLD["kasus"][0]]}
    assert asyncio.run(evaluasi(gagal, kasus))[0].status == "tertangkap"
    h = asyncio.run(evaluasi(mati, kasus))
    assert h[0].status == "galat" and "kuota habis" in h[0].alasan
    assert "1 galat penyedia" in laporan_markdown(h)


def test_jam_dan_alamat_dinilai_sebagai_ada_atau_tidak():
    async def tanpa_alamat(pesan, _k, aktif=None):
        return (await oracle(pesan, _k, aktif)).model_copy(update={"alamat": None})

    kasus = next(k for k in GOLD["kasus"] if k["id"] == "g01")  # alamat seharusnya terisi
    h = asyncio.run(evaluasi(tanpa_alamat, {**GOLD, "kasus": [kasus]}))[0]
    assert h.status == "lolos" and "alamat" in h.alasan


def test_laporan_memuat_tiga_angka_dan_kasus_salah():
    md = laporan_markdown(jalankan(oracle))
    assert "Benar seluruhnya" in md and "lolos tanpa tanda" in md and "100.0%" in md
