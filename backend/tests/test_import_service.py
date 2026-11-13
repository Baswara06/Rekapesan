"""Uji alur impor ujung ke ujung dengan ekstraktor tiruan (tanpa LLM)."""

import asyncio
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db import Batch, Customer, MessageRow, Order, OrderItem
from app.parser import FormatTidakDikenal
from app.schemas import ExtractedItem, Extraction
from app.services import BatchTidakDitemukan, EkstraksiGagalTotal, ImporBentrok, import_batch

CONTOH = (Path(__file__).resolve().parents[2] / "sample" / "ekspor-contoh.txt").read_bytes()


def it(pid, qty, teks):
    return ExtractedItem(product_id=pid, teks_asli=teks, qty=qty)


JAWABAN = {
    "Dewi": Extraction(intent="bukan_pesanan"),
    "Bu Rina": Extraction(intent="pesan", items=[it("p-ayam", 3, "ayam bakar 3")], alamat="Blok C no 4"),
    "Pak Anton": Extraction(intent="pesan", items=[it("p-ayam", 1, "aybak 1"), it("p-teh", 1, "es teh 1")], jam="12"),
    "Mbak Sari": Extraction(intent="batal"),
    "Mas Budi": Extraction(intent="pesan", items=[it("p-ayam", 500, "ayam bakar 500")]),
    "Mas Joko": Extraction(intent="bukan_pesanan"),
}


class Tiruan:
    """Ekstraktor tiruan yang mencatat apa saja yang dikirim kepadanya."""

    def __init__(self, jawaban=None):
        self.jawaban = jawaban or JAWABAN
        self.panggilan = []

    async def __call__(self, sender_messages, catalog, active_order=None):
        self.panggilan.append((sender_messages, catalog, active_order))
        return self.jawaban[sender_messages[0].pengirim]


def jalankan(db, data, extractor, batch_id="b-1"):
    return asyncio.run(import_batch(db, batch_id, data, extractor=extractor))


def pesanan(db, nama):
    return db.scalar(select(Order).join(Customer).where(Customer.nama_tampil == nama))


def test_impor_contoh_ujung_ke_ujung(db, katalog, batch):
    tiruan = Tiruan()
    hasil = jalankan(db, CONTOH, tiruan)
    assert hasil.model_dump() == {
        "pesan_baru": 9, "pesan_dilewati": 0, "pesanan_dibuat": 3, "pesanan_diubah": 0, "perlu_cek": 3,
    }
    assert len(tiruan.panggilan) == 6  # satu panggilan per pengirim

    rina = pesanan(db, "Bu Rina")
    assert rina.status == "perlu_cek" and rina.total == 54000 and rina.tanda == ["jam_kosong"]
    assert [m.isi for m in rina.pesan_sumber] == ["ayam bakar 2 ya, kirim ke Blok C no 4", "eh ganti jadi ayam bakar 3 ya"]

    anton = pesanan(db, "Pak Anton")
    assert anton.total == 23000 and anton.jam_kirim == "12:00" and anton.tanda == ["alamat_kosong"]

    budi = pesanan(db, "Mas Budi")
    assert budi.tanda == ["jumlah_tidak_wajar", "stok_kurang", "jam_kosong", "alamat_kosong"]

    assert pesanan(db, "Mbak Sari") is None and pesanan(db, "Mas Joko") is None
    # harga ayam bakar tidak berubah oleh pesan manipulasi
    assert db.scalar(select(OrderItem.harga_satuan).where(OrderItem.order_id == rina.id)) == 18000


def test_impor_ulang_menghasilkan_nol_pesan_baru(db, katalog, batch):
    jalankan(db, CONTOH, Tiruan())
    tiruan = Tiruan()
    hasil = jalankan(db, CONTOH, tiruan)
    assert hasil.model_dump() == {
        "pesan_baru": 0, "pesan_dilewati": 9, "pesanan_dibuat": 0, "pesanan_diubah": 0, "perlu_cek": 0,
    }
    assert tiruan.panggilan == []  # tidak ada panggilan LLM ulang
    assert db.scalar(select(func.count()).select_from(Order)) == 3
    assert db.scalar(select(func.count()).select_from(MessageRow)) == 9


def test_harga_dan_nomor_tidak_keluar_ke_ekstraktor(db, katalog, batch):
    jalankan(db, CONTOH, Tiruan())
    teks = (
        "13/11/26 07.00 - Bu Rina: tambah es teh 2, wa aku di 0812-3456-7890\n"
        "13/11/26 07.05 - +62 813-1111-2222: lodeh 1\n"
    )
    tiruan = Tiruan(
        {
            "Bu Rina": Extraction(intent="pesan", items=[it("p-teh", 2, "es teh 2")]),
            "[nomor]": Extraction(intent="pesan", items=[it("p-lodeh", 1, "lodeh 1")]),
        }
    )
    hasil = jalankan(db, teks, tiruan)
    assert (hasil.pesanan_dibuat, hasil.pesanan_diubah) == (1, 1)

    terkirim = repr(tiruan.panggilan)
    assert "0812" not in terkirim and "813-1111" not in terkirim and "[nomor]" in terkirim
    assert "18000" not in terkirim and "harga" not in terkirim and "total" not in terkirim
    aktif_rina = next(a for m, _, a in tiruan.panggilan if m[0].pengirim == "Bu Rina")
    assert aktif_rina["items"] == [{"product_id": "p-ayam", "teks_asli": "ayam bakar 3", "qty": 3, "catatan_item": None}]

    rina = pesanan(db, "Bu Rina")
    assert rina.total == 54000 + 10000 and rina.perubahan_sebelum["total"] == 54000
    # pengirim tanpa nama tetap tersimpan apa adanya di DB untuk penjual
    assert pesanan(db, "+62 813-1111-2222").total == 15000


def test_ubah_dan_batal_lewat_impor_berikutnya(db, katalog, batch):
    jalankan(db, CONTOH, Tiruan())
    teks = "13/11/26 07.00 - Bu Rina: jadi 1 aja ayamnya\n13/11/26 07.10 - Pak Anton: batal ya maaf\n"
    hasil = jalankan(
        db,
        teks,
        Tiruan({"Bu Rina": Extraction(intent="ubah", items=[it("p-ayam", 1, "ayam 1")]), "Pak Anton": Extraction(intent="batal")}),
    )
    assert (hasil.pesanan_dibuat, hasil.pesanan_diubah) == (0, 2)
    rina, anton = pesanan(db, "Bu Rina"), pesanan(db, "Pak Anton")
    assert rina.total == 18000 and rina.perubahan_sebelum["total"] == 54000 and rina.perubahan_sesudah["total"] == 18000
    assert anton.status == "batal" and anton.total == 23000
    assert len(rina.pesan_sumber) == 3


DUA_PENGIRIM = "12/11/26 09.15 - Bu Rina: ayam bakar 2\n12/11/26 09.16 - Pak Anton: es teh 1\n"


class Kuota(Exception):
    status_code = 429


def test_gagal_sebagian_menjadi_tanda_gagal_diekstrak(db, katalog, batch):
    async def separuh(sender_messages, catalog, active_order=None):
        if sender_messages[0].pengirim == "Bu Rina":
            raise RuntimeError("keluaran model tidak sah")
        return Extraction(intent="pesan", items=[it("p-teh", 1, "es teh 1")], jam="12", alamat="x")

    hasil = jalankan(db, DUA_PENGIRIM, separuh)
    assert (hasil.pesan_baru, hasil.pesanan_dibuat, hasil.perlu_cek) == (2, 2, 1)
    assert pesanan(db, "Bu Rina").tanda == ["gagal_diekstrak"] and pesanan(db, "Pak Anton").tanda == []


@pytest.mark.parametrize(("galat", "kode"), [(RuntimeError("mati"), "llm_gagal"), (Kuota(), "kuota_llm_habis")])
def test_gagal_total_tidak_menyimpan_apa_pun_dan_bisa_diulang(db, katalog, batch, galat, kode):
    async def rusak(sender_messages, catalog, active_order=None):
        raise galat

    with pytest.raises(EkstraksiGagalTotal) as info:
        jalankan(db, DUA_PENGIRIM, rusak)
    assert info.value.kode == kode
    for tabel in (MessageRow, Order, Customer):
        assert db.scalar(select(func.count()).select_from(tabel)) == 0

    # setelah LLM pulih, berkas yang sama diimpor ulang dan diproses penuh
    pulih = Tiruan({n: Extraction(intent="pesan", items=[it("p-teh", 1, "x")]) for n in ("Bu Rina", "Pak Anton")})
    hasil = jalankan(db, DUA_PENGIRIM, pulih)
    assert (hasil.pesan_baru, hasil.pesan_dilewati, hasil.pesanan_dibuat) == (2, 0, 2)


def test_impor_bersamaan_menjadi_impor_bentrok(db, katalog, batch, monkeypatch):
    jalankan(db, DUA_PENGIRIM, Tiruan({n: Extraction(intent="bukan_pesanan") for n in ("Bu Rina", "Pak Anton")}))
    # Tiru impor kedua yang membaca DB sebelum impor pertama selesai: sidik lama dianggap belum ada.
    monkeypatch.setattr("app.services.import_service.saring_baru", lambda pesan, _ada: pesan)
    with pytest.raises(ImporBentrok):
        jalankan(db, DUA_PENGIRIM, Tiruan())
    assert db.scalar(select(func.count()).select_from(MessageRow)) == 2  # tidak ada baris ganda


def test_stok_dihitung_lintas_pesanan_dalam_satu_impor(db, katalog, batch):
    teks = "12/11/26 09.00 - A: lodeh 6\n12/11/26 09.01 - B: lodeh 6\n"
    jalankan(
        db,
        teks,
        Tiruan({n: Extraction(intent="pesan", items=[it("p-lodeh", 6, "lodeh 6")], jam="12", alamat="x") for n in "AB"}),
    )
    assert pesanan(db, "A").tanda == [] and pesanan(db, "B").tanda == ["stok_kurang"]


def test_saringan_tanggal_mulai_batch(db, katalog, batch):
    teks = "10/11/26 09.00 - Bu Rina: PO minggu lalu ayam 9\n12/11/26 09.15 - Bu Rina: ayam bakar 2\n"
    assert jalankan(db, teks, Tiruan({"Bu Rina": Extraction(intent="bukan_pesanan")})).pesan_baru == 1


def test_galat_batch_dan_format(db, katalog, batch):
    with pytest.raises(BatchTidakDitemukan):
        jalankan(db, CONTOH, Tiruan(), batch_id="tidak-ada")
    with pytest.raises(FormatTidakDikenal):
        jalankan(db, "bukan chat", Tiruan())


def test_hapus_batch_ikut_menghapus_pesan_mentah(db, katalog, batch):
    jalankan(db, CONTOH, Tiruan())
    db.delete(db.get(Batch, "b-1"))
    db.commit()
    for tabel in (MessageRow, Order, OrderItem, Customer):
        assert db.scalar(select(func.count()).select_from(tabel)) == 0
