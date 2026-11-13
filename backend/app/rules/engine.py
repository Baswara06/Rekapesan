"""Mesin aturan deterministik: harga, total, stok, tanda kuning, ubah/batal. Pemilik: Satria.

Tidak ada LLM dan tidak ada akses DB di sini. Semua fungsi murni, supaya mudah diuji.
Harga selalu diambil dari katalog. `Extraction` tidak punya kolom harga sama sekali.

Bentuk `order_context` (disusun oleh `services/import_service.py`):

    {
      "catalog": {product_id: {"nama": str, "harga": int, "stok_harian": int | None, "aktif": bool}},
      "active_order": None | {
          "id": str, "status": str, "jam_kirim": str | None, "alamat": str | None,
          "catatan": str | None, "total": int, "tanda": list[str],
          "items": [{"product_id", "teks_asli", "qty", "harga_satuan", "catatan_item"}],
      },
      "terpakai": {product_id: int},   # qty pesanan yang MASUK LEBIH DULU di batch yang sama
      "ambang_jumlah_tidak_wajar": int,  # opsional, default 20
    }
"""

import re
from typing import Any

from app.schemas import ExtractedItem, Extraction, OrderChange, Tanda

AMBANG_DEFAULT = 20
STATUS_PERLU_CEK = "perlu_cek"
STATUS_BATAL = "batal"

_URUTAN_TANDA: tuple[Tanda, ...] = (
    "gagal_diekstrak",
    "item_tidak_dikenal",
    "jumlah_kosong",
    "jumlah_tidak_wajar",
    "stok_kurang",
    "mungkin_dobel",
    "jam_kosong",
    "alamat_kosong",
)

_JAM = re.compile(r"(?<!\d)(\d{1,2})(?:\s*[.:]\s*(\d{2}))?(?!\d)")


def normalisasi_jam(jam: str | None) -> str | None:
    """Ubah "12", "jam 11.30", "9:5" menjadi "HH:MM". Teks tanpa jam yang sah menjadi None."""
    if not jam:
        return None
    m = _JAM.search(jam)
    if not m:
        return None
    h, mnt = int(m.group(1)), int(m.group(2) or 0)
    teks = jam.lower()
    if h < 12 and re.search(r"\b(sore|malam|pm)\b", teks):
        h += 12
    elif h < 11 and re.search(r"\bsiang\b", teks):
        h += 12
    if h > 23 or mnt > 59:
        return None
    return f"{h:02d}:{mnt:02d}"


def _teks(nilai: str | None) -> str | None:
    nilai = (nilai or "").strip()
    return nilai or None


def validasi_product_id(extraction: Extraction, catalog: dict[str, Any]) -> Extraction:
    """`product_id` yang tidak ada di katalog (atau nonaktif) dijadikan None."""
    items = []
    for it in extraction.items:
        produk = catalog.get(it.product_id) if it.product_id else None
        sah = produk is not None and produk.get("aktif", True)
        items.append(it if sah else it.model_copy(update={"product_id": None}))
    return extraction.model_copy(update={"items": items})


def beri_harga(items: list[ExtractedItem], catalog: dict[str, Any]) -> list[dict[str, Any]]:
    """Tempel `harga_satuan` dari katalog ke tiap item. Item tak dikenal: harga None."""
    hasil = []
    for it in items:
        produk = catalog.get(it.product_id) if it.product_id else None
        hasil.append(
            {
                "product_id": it.product_id if produk else None,
                "teks_asli": it.teks_asli,
                "qty": it.qty,
                "harga_satuan": int(produk["harga"]) if produk else None,
                "catatan_item": _teks(it.catatan_item),
            }
        )
    return hasil


def hitung_total(items: list[dict[str, Any]]) -> int:
    """Jumlah qty x harga_satuan. Item tanpa harga atau tanpa jumlah yang sah tidak dihitung."""
    return sum(
        it["qty"] * it["harga_satuan"]
        for it in items
        if it.get("harga_satuan") is not None and isinstance(it.get("qty"), int) and it["qty"] > 0
    )


def qty_per_produk(items: list[dict[str, Any]]) -> dict[str, int]:
    hasil: dict[str, int] = {}
    for it in items:
        if it.get("product_id") and isinstance(it.get("qty"), int) and it["qty"] > 0:
            hasil[it["product_id"]] = hasil.get(it["product_id"], 0) + it["qty"]
    return hasil


def sisa_stok(catalog: dict[str, Any], terpakai: dict[str, int]) -> dict[str, int | None]:
    """Sisa stok per menu. None berarti stok menu itu tidak dibatasi. Bisa negatif (kelebihan pesan)."""
    return {
        pid: None if p.get("stok_harian") is None else p["stok_harian"] - terpakai.get(pid, 0)
        for pid, p in catalog.items()
    }


def tanda_pesanan(
    items: list[dict[str, Any]],
    jam_kirim: str | None,
    alamat: str | None,
    catalog: dict[str, Any],
    terpakai: dict[str, int],
    ambang: int = AMBANG_DEFAULT,
    tambahan: set[str] | None = None,
) -> list[Tanda]:
    """Hitung semua tanda kuning untuk satu pesanan, dalam urutan tetap."""
    tanda: set[str] = set(tambahan or ())
    if not items and "gagal_diekstrak" not in tanda:
        tanda.add("item_tidak_dikenal")
    for it in items:
        if not it.get("product_id"):
            tanda.add("item_tidak_dikenal")
        qty = it.get("qty")
        if not isinstance(qty, int) or qty <= 0:
            tanda.add("jumlah_kosong")
        elif qty > ambang:
            tanda.add("jumlah_tidak_wajar")
    if stok_kurang(items, catalog, terpakai):
        tanda.add("stok_kurang")
    if not jam_kirim:
        tanda.add("jam_kosong")
    if not _teks(alamat):
        tanda.add("alamat_kosong")
    return [t for t in _URUTAN_TANDA if t in tanda]


def atur_tanda(tanda: list[str], kode: Tanda, pasang: bool) -> list[str]:
    """Pasang atau lepas satu tanda tanpa mengubah tanda lain, dalam urutan tetap."""
    kumpulan = set(tanda) | {kode} if pasang else set(tanda) - {kode}
    return [t for t in _URUTAN_TANDA if t in kumpulan]


def stok_kurang(items: list[dict[str, Any]], catalog: dict[str, Any], terpakai: dict[str, int]) -> bool:
    """True bila pesanan ini, ditambah yang sudah terpakai pesanan SEBELUMNYA, melebihi stok harian."""
    for pid, qty in qty_per_produk(items).items():
        stok = (catalog.get(pid) or {}).get("stok_harian")
        if stok is not None and terpakai.get(pid, 0) + qty > stok:
            return True
    return False


def _potret(order: dict[str, Any]) -> dict[str, Any]:
    """Salinan pesanan untuk kolom sebelum/sesudah."""
    return {
        "status": order.get("status", STATUS_PERLU_CEK),
        "jam_kirim": order.get("jam_kirim"),
        "alamat": order.get("alamat"),
        "catatan": order.get("catatan"),
        "items": [
            {k: it.get(k) for k in ("product_id", "teks_asli", "qty", "harga_satuan", "catatan_item")}
            for it in order.get("items", [])
        ],
        "total": order.get("total", 0),
        "tanda": list(order.get("tanda", [])),
    }


def apply_intent(order_context: dict[str, Any], extraction: Extraction) -> OrderChange:
    """Terapkan hasil ekstraksi ke pesanan aktif pelanggan. Semua angka dihitung kode, bukan LLM.

    - `pesan` tanpa pesanan aktif  -> buat pesanan baru.
    - `pesan` dengan pesanan aktif -> item ditambahkan. Menu yang sudah ada diberi `mungkin_dobel`.
    - `ubah`  -> item (bila ada) menggantikan item lama; jam/alamat/catatan diisi bila disebut.
                 Tanpa pesanan aktif diperlakukan sebagai pesanan baru.
    - `batal` -> status pesanan aktif menjadi batal. Tanpa pesanan aktif: abaikan.
    - `bukan_pesanan` -> abaikan.
    - `gagal` -> pesanan diberi `gagal_diekstrak` supaya penjual memeriksa chat aslinya.

    Hasil selalu berstatus `perlu_cek` (kecuali batal): keputusan akhir tetap di penjual.
    """
    catalog: dict[str, Any] = order_context.get("catalog") or {}
    aktif: dict[str, Any] | None = order_context.get("active_order")
    terpakai: dict[str, int] = order_context.get("terpakai") or {}
    ambang: int = order_context.get("ambang_jumlah_tidak_wajar") or AMBANG_DEFAULT

    order_id = aktif.get("id") if aktif else None
    sebelum = _potret(aktif) if aktif else None
    extraction = validasi_product_id(extraction, catalog)

    def susun(items, jam, alamat, catatan, tambahan=None) -> dict[str, Any]:
        return {
            "status": STATUS_PERLU_CEK,
            "jam_kirim": jam,
            "alamat": alamat,
            "catatan": catatan,
            "items": items,
            "total": hitung_total(items),
            "tanda": tanda_pesanan(items, jam, alamat, catalog, terpakai, ambang, tambahan),
        }

    def hasil(aksi: str, sesudah: dict[str, Any] | None) -> OrderChange:
        return OrderChange(
            order_id=order_id,
            aksi=aksi,
            sebelum=sebelum,
            sesudah=sesudah,
            tanda=sesudah["tanda"] if sesudah else [],
        )

    if extraction.gagal:
        if aktif:
            return hasil(
                "ubah",
                susun(sebelum["items"], sebelum["jam_kirim"], sebelum["alamat"], sebelum["catatan"], {"gagal_diekstrak"}),
            )
        # Tidak ada isi yang bisa dinilai, jadi cukup satu tanda: penjual membaca chat aslinya.
        return hasil("buat", dict(susun([], None, None, None), tanda=["gagal_diekstrak"]))

    if extraction.intent == "bukan_pesanan":
        return OrderChange(order_id=order_id, aksi="abaikan")

    if extraction.intent == "batal":
        if not aktif:
            return OrderChange(aksi="abaikan")
        sesudah = dict(sebelum, status=STATUS_BATAL, tanda=[])
        return hasil("batal", sesudah)

    items_baru = beri_harga(extraction.items, catalog)
    jam_baru = normalisasi_jam(extraction.jam)
    alamat_baru = _teks(extraction.alamat)
    catatan_baru = _teks(extraction.catatan)

    if not aktif:
        if not items_baru:
            # "ubah" tanpa pesanan dan tanpa item: tidak ada yang bisa dibuat.
            return OrderChange(aksi="abaikan")
        return hasil("buat", susun(items_baru, jam_baru, alamat_baru, catatan_baru))

    jam = jam_baru or sebelum["jam_kirim"]
    alamat = alamat_baru or sebelum["alamat"]
    catatan = catatan_baru or sebelum["catatan"]

    if extraction.intent == "ubah":
        items = items_baru or sebelum["items"]
        return hasil("ubah", susun(items, jam, alamat, catatan))

    # intent "pesan" padahal pelanggan sudah punya pesanan aktif: tambahkan, tandai bila menu sama.
    if not items_baru:
        return OrderChange(order_id=order_id, aksi="abaikan")
    lama = {it["product_id"] for it in sebelum["items"] if it.get("product_id")}
    teks_lama = {it["teks_asli"].strip().lower() for it in sebelum["items"]}
    dobel = any(
        (it["product_id"] in lama) if it["product_id"] else (it["teks_asli"].strip().lower() in teks_lama)
        for it in items_baru
    )
    return hasil(
        "ubah",
        susun(sebelum["items"] + items_baru, jam, alamat, catatan, {"mungkin_dobel"} if dobel else None),
    )
