"""Orkestrasi impor: parser -> saring sidik -> anonimisasi -> ekstraktor -> rules -> simpan. Pemilik: Satria.

Yang dijaga di sini:
- pesan yang sudah pernah diimpor (sidik sama) dilewati, jadi impor ulang tidak membuat pesanan dobel,
- teks disamarkan sebelum keluar ke LLM, dan pesanan aktif yang dikirim ke LLM tidak memuat harga,
- ekstraksi dipanggil sekali per pengirim, paralel,
- semua pesanan hasil impor berstatus `perlu_cek`: penjual yang menyetujui,
- bila ekstraktor gagal untuk SEMUA pengirim (kuota habis, penyedia mati), impor dibatalkan tanpa
  menyimpan apa pun, supaya penjual bisa mengulang. Gagal sebagian menjadi tanda `gagal_diekstrak`.
"""

import asyncio
import inspect
import logging
from collections.abc import Callable
from typing import IO, Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.models import STATUS_BATAL, Batch, Customer, MessageRow, Order, OrderItem, Product
from app.parser import anonymize, parse_export, saring_baru
from app.rules import apply_intent, qty_per_produk
from app.schemas import CatalogEntry, Extraction, Message, OrderChange
from app.services.stok_service import segarkan_tanda_stok

log = logging.getLogger(__name__)

MAKS_PARALEL = 5
Extractor = Callable[..., Any]


class BatchTidakDitemukan(LookupError):
    pass


class EkstraksiGagalTotal(RuntimeError):
    """Ekstraktor gagal untuk semua pengirim. Tidak ada yang disimpan, impor boleh diulang.

    `kode` mengikuti kontrak API: `kuota_llm_habis` atau `llm_gagal`.
    """

    def __init__(self, kode: str) -> None:
        super().__init__(kode)
        self.kode = kode


class ImporBentrok(RuntimeError):
    """Impor lain ke batch yang sama menyimpan pesan yang sama lebih dulu. Tidak ada yang disimpan."""


class ImportResult(BaseModel):
    """Respons `POST /api/batches/{id}/import` sesuai `docs/api-contract.md`."""

    pesan_baru: int = 0
    pesan_dilewati: int = 0
    pesanan_dibuat: int = 0
    pesanan_diubah: int = 0
    perlu_cek: int = 0


def katalog_untuk_llm(products: list[Product]) -> list[CatalogEntry]:
    """Katalog yang boleh dilihat LLM: id, nama, alias. Tanpa harga dan tanpa stok."""
    return [CatalogEntry(id=p.id, nama=p.nama, alias=list(p.alias or [])) for p in products if p.aktif]


def katalog_untuk_rules(products: list[Product]) -> dict[str, dict[str, Any]]:
    return {
        p.id: {"nama": p.nama, "harga": p.harga, "stok_harian": p.stok_harian, "aktif": p.aktif} for p in products
    }


def order_ke_dict(order: Order) -> dict[str, Any]:
    return {
        "id": order.id,
        "status": order.status,
        "jam_kirim": order.jam_kirim,
        "alamat": order.alamat,
        "catatan": order.catatan,
        "total": order.total,
        "tanda": list(order.tanda or []),
        "items": [
            {
                "product_id": it.product_id,
                "teks_asli": it.teks_asli,
                "qty": it.qty,
                "harga_satuan": it.harga_satuan,
                "catatan_item": it.catatan_item,
            }
            for it in order.items
        ],
    }


def pesanan_aktif_untuk_llm(order: dict[str, Any] | None) -> dict[str, Any] | None:
    """Buang harga dan total sebelum pesanan aktif dikirim ke ekstraktor."""
    if order is None:
        return None
    return {
        "jam_kirim": order["jam_kirim"],
        "alamat": order["alamat"],
        "catatan": order["catatan"],
        "items": [
            {k: it[k] for k in ("product_id", "teks_asli", "qty", "catatan_item")} for it in order["items"]
        ],
    }


def _kuota_habis(exc: BaseException) -> bool:
    """Galat batas kuota dari penyedia LLM (HTTP 429), tanpa bergantung pada pustaka tertentu."""
    status = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
    return status == 429 or type(exc).__name__ == "RateLimitError"


async def _ekstrak(
    extractor: Extractor, kunci: asyncio.Semaphore, pesan, katalog, aktif
) -> tuple[Extraction, BaseException | None]:
    """Panggil ekstraktor untuk satu pengirim. Kembalikan (hasil, galat).

    Kegagalan menjadi `Extraction(gagal=True)` beserta galatnya, supaya pemanggil bisa
    membedakan gagal sebagian (tanda kuning) dari gagal total (impor dibatalkan).
    """
    async with kunci:
        try:
            hasil = extractor(pesan, katalog, aktif)
            if inspect.isawaitable(hasil):
                hasil = await hasil
            return Extraction.model_validate(hasil), None
        except Exception as exc:  # noqa: BLE001 - satu pengirim gagal tidak boleh menggagalkan impor
            log.warning("Ekstraksi gagal untuk satu pengirim: %s", type(exc).__name__)
            return Extraction(intent="bukan_pesanan", gagal=True), exc


def _terapkan(db: Session, order: Order, change: OrderChange) -> None:
    s = change.sesudah or {}
    order.status = s.get("status", order.status)
    order.jam_kirim = s.get("jam_kirim")
    order.alamat = s.get("alamat")
    order.catatan = s.get("catatan")
    order.total = s.get("total", 0)
    order.tanda = list(s.get("tanda", []))
    order.perubahan_sebelum = change.sebelum
    order.perubahan_sesudah = change.sesudah if change.sebelum else None
    order.items.clear()
    db.flush()
    for it in s.get("items", []):
        order.items.append(
            OrderItem(
                product_id=it.get("product_id"),
                teks_asli=it.get("teks_asli") or "",
                qty=it.get("qty"),
                harga_satuan=it.get("harga_satuan"),
                catatan_item=it.get("catatan_item"),
            )
        )


async def import_batch(
    db: Session,
    batch_id: str,
    file_or_text: IO[bytes] | bytes | str,
    extractor: Extractor | None = None,
    ambang_jumlah_tidak_wajar: int | None = None,
    penjual: str | None = None,
) -> ImportResult:
    """Impor satu berkas ekspor atau teks tempel ke sebuah batch.

    `extractor` bisa diganti (uji, data demo tersimpan). Default: `app.extractor.extract_orders`.
    Melempar `BatchTidakDitemukan`, `FormatTidakDikenal`, `EkstraksiGagalTotal`, atau `ImporBentrok`.
    Pada dua galat terakhir tidak ada yang tersimpan, jadi impor yang sama aman diulang.
    `penjual`: nama pengirim penjual di chat. Pesannya tetap disimpan, tapi tidak diekstrak sebagai pesanan
    (chat satu lawan satu tanpa daftar menu: "51 k" dari penjual bukan pesanan).
    """
    try:
        return await _impor(db, batch_id, file_or_text, extractor, ambang_jumlah_tidak_wajar, penjual)
    except IntegrityError as exc:
        # Sidik unik per batch: impor lain yang berjalan bersamaan sudah menyimpan pesan ini.
        db.rollback()
        raise ImporBentrok(batch_id) from exc
    except Exception:
        db.rollback()
        raise


async def _impor(
    db: Session,
    batch_id: str,
    file_or_text: IO[bytes] | bytes | str,
    extractor: Extractor | None,
    ambang_jumlah_tidak_wajar: int | None,
    penjual: str | None = None,
) -> ImportResult:
    if extractor is None:
        from app.extractor import extract_orders as extractor  # noqa: PLC0415 - hindari impor melingkar

    batch = db.get(Batch, batch_id)
    if batch is None:
        raise BatchTidakDitemukan(batch_id)

    semua = parse_export(file_or_text, batch.tanggal_mulai)
    # Pesan sesudah hari kirim milik PO berikutnya: bila ikut, pesanan baru menimpa pesanan PO ini.
    semua = [p for p in semua if p.waktu.date() <= batch.tanggal_kirim]
    sidik_ada = set(db.scalars(select(MessageRow.sidik).where(MessageRow.batch_id == batch_id)))
    baru = saring_baru(semua, sidik_ada)
    hasil = ImportResult(pesan_baru=len(baru), pesan_dilewati=len(semua) - len(baru))
    if not baru:
        return hasil

    baris_pesan: dict[str, list[MessageRow]] = {}
    per_pengirim: dict[str, list[Message]] = {}
    for p in baru:
        baris = MessageRow(batch_id=batch_id, waktu=p.waktu, pengirim=p.pengirim, isi=p.isi, sidik=p.sidik)
        db.add(baris)
        baris_pesan.setdefault(p.pengirim, []).append(baris)
        per_pengirim.setdefault(p.pengirim, []).append(p)

    # Hanya katalog milik penjual batch ini yang dikirim ke LLM dan dipakai menghitung.
    products = list(db.scalars(select(Product).where(Product.pemilik == batch.pemilik)))

    katalog_llm = katalog_untuk_llm(products)
    katalog = katalog_untuk_rules(products)
    ambang = ambang_jumlah_tidak_wajar or get_settings().jumlah_tidak_wajar_default

    orders = list(
        db.scalars(
            select(Order)
            .where(Order.batch_id == batch_id, Order.status != STATUS_BATAL)
            .options(selectinload(Order.items), selectinload(Order.customer))
            .order_by(Order.dibuat_pada)
        )
    )
    aktif_per_nama: dict[str, Order] = {o.customer.nama_tampil: o for o in orders}
    pakai_per_order: dict[str, dict[str, int]] = {o.id: qty_per_produk(order_ke_dict(o)["items"]) for o in orders}

    # 1) Ekstraksi: satu panggilan per pengirim, paralel. Teks disamarkan dulu.
    kunci = asyncio.Semaphore(MAKS_PARALEL)
    pengirim_urut = [n for n in per_pengirim if n != penjual]
    tugas = []
    for nama in pengirim_urut:
        samaran = [
            m.model_copy(update={"pengirim": anonymize(m.pengirim), "isi": anonymize(m.isi)})
            for m in per_pengirim[nama]
        ]
        aktif = aktif_per_nama.get(nama)
        tugas.append(
            _ekstrak(extractor, kunci, samaran, katalog_llm, pesanan_aktif_untuk_llm(order_ke_dict(aktif) if aktif else None))
        )
    keluaran = await asyncio.gather(*tugas)
    ekstraksi = [e for e, _ in keluaran]
    galat = [g for _, g in keluaran if g is not None]
    if keluaran and len(galat) == len(keluaran):
        # Tidak ada satu pun yang berhasil: ini masalah LLM, bukan isi chat. Jangan simpan apa pun.
        raise EkstraksiGagalTotal("kuota_llm_habis" if any(_kuota_habis(g) for g in galat) else "llm_gagal")

    # 2) Aturan dan simpan: berurutan menurut pesan pertama, supaya hitungan stok tetap.
    disentuh: dict[str, Order] = {}
    for nama, ext in zip(pengirim_urut, ekstraksi, strict=True):
        aktif = aktif_per_nama.get(nama)
        terpakai: dict[str, int] = {}
        for oid, pakai in pakai_per_order.items():
            if aktif is not None and oid == aktif.id:
                continue
            for pid, qty in pakai.items():
                terpakai[pid] = terpakai.get(pid, 0) + qty

        change = apply_intent(
            {
                "catalog": katalog,
                "active_order": order_ke_dict(aktif) if aktif else None,
                "terpakai": terpakai,
                "ambang_jumlah_tidak_wajar": ambang,
            },
            ext,
        )
        if change.aksi == "abaikan":
            continue

        if change.aksi == "buat":
            customer = db.scalar(
                select(Customer).where(Customer.batch_id == batch_id, Customer.nama_tampil == nama)
            ) or Customer(batch_id=batch_id, nama_tampil=nama)
            order = Order(batch_id=batch_id, customer=customer)
            db.add(order)
            db.flush()
            change.sebelum = None
            hasil.pesanan_dibuat += 1
        else:
            order = aktif
            hasil.pesanan_diubah += 1

        _terapkan(db, order, change)
        for baris in baris_pesan[nama]:
            baris.order = order
        db.flush()

        if order.status == STATUS_BATAL:
            aktif_per_nama.pop(nama, None)
            pakai_per_order.pop(order.id, None)
        else:
            aktif_per_nama[nama] = order
            pakai_per_order[order.id] = qty_per_produk((change.sesudah or {}).get("items", []))
        disentuh[order.id] = order

    # Tanda stok dihitung ulang untuk seluruh batch menurut urutan masuk (lihat stok_service).
    segarkan_tanda_stok(db, batch_id)
    hasil.perlu_cek = sum(1 for o in disentuh.values() if o.tanda and o.status != STATUS_BATAL)
    db.commit()
    return hasil
