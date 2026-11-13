import pytest

from app.rules import apply_intent, hitung_total, normalisasi_jam, sisa_stok
from app.schemas import ExtractedItem, Extraction

KATALOG = {
    "p-ayam": {"nama": "Ayam Bakar", "harga": 18000, "stok_harian": 30, "aktif": True},
    "p-lodeh": {"nama": "Nasi Lodeh", "harga": 15000, "stok_harian": 10, "aktif": True},
    "p-teh": {"nama": "Es Teh", "harga": 5000, "stok_harian": None, "aktif": True},
    "p-lama": {"nama": "Menu Lama", "harga": 9000, "stok_harian": None, "aktif": False},
}


def ctx(aktif=None, terpakai=None, ambang=20):
    return {"catalog": KATALOG, "active_order": aktif, "terpakai": terpakai or {}, "ambang_jumlah_tidak_wajar": ambang}


def item(pid, qty, teks="x", catatan=None):
    return ExtractedItem(product_id=pid, teks_asli=teks, qty=qty, catatan_item=catatan)


def pesan(*items, intent="pesan", jam="12", alamat="Blok C no 4", **lain):
    return Extraction(intent=intent, items=list(items), jam=jam, alamat=alamat, **lain)


def aktif_dari(change, order_id="o-1"):
    return {"id": order_id, **change.sesudah}


def test_pesanan_bersih_harga_dari_katalog():
    c = apply_intent(ctx(), pesan(item("p-ayam", 2), item("p-teh", 1)))
    assert c.aksi == "buat" and c.tanda == [] and c.sebelum is None
    assert c.sesudah["total"] == 2 * 18000 + 5000
    assert [i["harga_satuan"] for i in c.sesudah["items"]] == [18000, 5000]
    assert c.sesudah["jam_kirim"] == "12:00"
    assert c.sesudah["status"] == "perlu_cek"


def test_item_tidak_dikenal_dan_id_karangan_llm():
    c = apply_intent(ctx(), pesan(item(None, 1, "rendang"), item("id-ngarang", 2, "sate"), item("p-lama", 1)))
    assert c.tanda == ["item_tidak_dikenal"]
    assert all(i["product_id"] is None and i["harga_satuan"] is None for i in c.sesudah["items"])
    assert c.sesudah["total"] == 0


@pytest.mark.parametrize("qty", [None, 0, -3])
def test_jumlah_kosong(qty):
    c = apply_intent(ctx(), pesan(item("p-ayam", qty)))
    assert c.tanda == ["jumlah_kosong"] and c.sesudah["total"] == 0


def test_jumlah_tidak_wajar_dan_stok_kurang():
    c = apply_intent(ctx(), pesan(item("p-ayam", 500)))
    assert c.tanda == ["jumlah_tidak_wajar", "stok_kurang"]
    assert apply_intent(ctx(ambang=600), pesan(item("p-teh", 500))).tanda == []


def test_stok_kurang_menghitung_pesanan_lain():
    assert apply_intent(ctx(terpakai={"p-lodeh": 7}), pesan(item("p-lodeh", 3))).tanda == []
    assert apply_intent(ctx(terpakai={"p-lodeh": 8}), pesan(item("p-lodeh", 3))).tanda == ["stok_kurang"]
    # dua baris menu yang sama dijumlah dulu
    assert apply_intent(ctx(), pesan(item("p-lodeh", 6), item("p-lodeh", 6))).tanda == ["stok_kurang"]


def test_jam_dan_alamat_kosong():
    c = apply_intent(ctx(), pesan(item("p-ayam", 1), jam=None, alamat="  "))
    assert c.tanda == ["jam_kosong", "alamat_kosong"]


def test_gagal_diekstrak_membuat_pesanan_untuk_dicek():
    c = apply_intent(ctx(), Extraction(intent="bukan_pesanan", gagal=True))
    assert c.aksi == "buat" and "gagal_diekstrak" in c.tanda and c.sesudah["items"] == []


def test_gagal_diekstrak_tidak_mengubah_isi_pesanan_aktif():
    awal = apply_intent(ctx(), pesan(item("p-ayam", 2)))
    c = apply_intent(ctx(aktif_dari(awal)), Extraction(intent="pesan", gagal=True))
    assert c.aksi == "ubah" and c.tanda == ["gagal_diekstrak"]
    assert c.sesudah["items"] == awal.sesudah["items"] and c.sesudah["total"] == 36000


def test_bukan_pesanan_diabaikan():
    assert apply_intent(ctx(), Extraction(intent="bukan_pesanan")).aksi == "abaikan"


def test_ubah_mengganti_item_dan_menyimpan_sebelum_sesudah():
    awal = apply_intent(ctx(), pesan(item("p-ayam", 2)))
    c = apply_intent(ctx(aktif_dari(awal)), Extraction(intent="ubah", items=[item("p-ayam", 3)]))
    assert c.aksi == "ubah" and c.order_id == "o-1"
    assert c.sebelum["total"] == 36000 and c.sesudah["total"] == 54000
    assert c.sesudah["alamat"] == "Blok C no 4" and c.sesudah["jam_kirim"] == "12:00"


def test_ubah_hanya_alamat_item_tetap():
    awal = apply_intent(ctx(), pesan(item("p-ayam", 2)))
    c = apply_intent(ctx(aktif_dari(awal)), Extraction(intent="ubah", alamat="Lantai 2", jam="jam 1 siang"))
    assert c.sesudah["items"] == awal.sesudah["items"]
    assert c.sesudah["alamat"] == "Lantai 2" and c.sesudah["jam_kirim"] == "13:00"


def test_ubah_pesanan_yang_sudah_dikonfirmasi_kembali_perlu_cek():
    awal = apply_intent(ctx(), pesan(item("p-ayam", 2)))
    aktif = dict(aktif_dari(awal), status="dikonfirmasi")
    c = apply_intent(ctx(aktif), Extraction(intent="ubah", items=[item("p-ayam", 1)]))
    assert c.sebelum["status"] == "dikonfirmasi" and c.sesudah["status"] == "perlu_cek"


def test_ubah_tanpa_pesanan_aktif_menjadi_pesanan_baru():
    c = apply_intent(ctx(), pesan(item("p-ayam", 3), intent="ubah"))
    assert c.aksi == "buat" and c.sesudah["total"] == 54000


def test_batal():
    awal = apply_intent(ctx(), pesan(item("p-lodeh", 3)))
    c = apply_intent(ctx(aktif_dari(awal)), Extraction(intent="batal"))
    assert c.aksi == "batal" and c.sesudah["status"] == "batal" and c.sebelum["status"] == "perlu_cek"
    assert apply_intent(ctx(), Extraction(intent="batal")).aksi == "abaikan"


def test_pesan_lagi_menu_sama_ditandai_mungkin_dobel():
    awal = apply_intent(ctx(), pesan(item("p-ayam", 2)))
    c = apply_intent(ctx(aktif_dari(awal)), pesan(item("p-ayam", 2), jam=None, alamat=None))
    assert c.aksi == "ubah" and c.tanda == ["mungkin_dobel"]
    assert len(c.sesudah["items"]) == 2 and c.sesudah["total"] == 72000


def test_pesan_lagi_menu_lain_ditambahkan_tanpa_tanda():
    awal = apply_intent(ctx(), pesan(item("p-ayam", 2)))
    c = apply_intent(ctx(aktif_dari(awal)), pesan(item("p-teh", 2), jam=None, alamat=None))
    assert c.tanda == [] and c.sesudah["total"] == 46000


def test_hitung_total_dan_sisa_stok():
    assert hitung_total([{"qty": 2, "harga_satuan": 18000}, {"qty": None, "harga_satuan": 5000}, {"qty": 1, "harga_satuan": None}]) == 36000
    assert sisa_stok(KATALOG, {"p-ayam": 24, "p-lodeh": 12})["p-ayam"] == 6
    assert sisa_stok(KATALOG, {"p-lodeh": 12})["p-lodeh"] == -2
    assert sisa_stok(KATALOG, {})["p-teh"] is None


@pytest.mark.parametrize(
    ("masuk", "keluar"),
    [("12", "12:00"), ("jam 11.30", "11:30"), ("9:05", "09:05"), ("jam 1 siang", "13:00"), ("7 malam", "19:00"),
     ("besok", None), ("25.00", None), (None, None), ("", None)],
)
def test_normalisasi_jam(masuk, keluar):
    assert normalisasi_jam(masuk) == keluar
