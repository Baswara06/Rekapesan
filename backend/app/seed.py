"""Data demo untuk Grand Final: katalog, satu batch, dan pesanan hasil impor contoh. Pemilik: Raihan.

    cd backend && python -m app.seed            # isi bila belum ada
    cd backend && python -m app.seed --reset    # hapus batch demo lalu isi ulang

PENTING, jujur soal asal data:
- Chat dari `sample/ekspor-contoh.txt` (samaran, bukan chat asli).
- Hasil ekstraksi di sini DITULIS TANGAN (`EKSTRAKSI_TERSIMPAN`), bukan keluaran LLM. Fungsinya
  cadangan bila internet atau kuota LLM mati saat demo. Semua hitungan setelah itu (harga, total,
  tanda kuning, rekap) tetap dikerjakan mesin aturan, sama seperti impor sungguhan.
- Jangan menyebut hasil seed sebagai kinerja ekstraktor. Angka evaluasi ekstraktor berasal dari `docs/evaluasi.md`.
"""

import argparse
import asyncio
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import Batch, Product, Recipe, get_engine, init_db

from app.schemas import ExtractedItem, Extraction
from app.services import import_batch

NAMA_BATCH = "PO Jumat 13 Nov (DEMO)"
BERKAS_CONTOH = Path(__file__).resolve().parents[2] / "sample" / "ekspor-contoh.txt"

KATALOG = [
    {
        "nama": "Ayam Bakar", "alias": ["aybak", "ayam bkr"], "harga": 18000, "stok_harian": 30,
        "resep": [("Ayam", 0.25, "kg"), ("Beras", 0.1, "kg")],
    },
    {
        "nama": "Nasi Lodeh", "alias": ["lodeh"], "harga": 15000, "stok_harian": 10,
        "resep": [("Beras", 0.1, "kg"), ("Labu siam", 0.15, "kg")],
    },
    {"nama": "Es Teh", "alias": ["esteh"], "harga": 5000, "stok_harian": None, "resep": []},
]


def _item(ids: dict[str, str], menu: str, qty: int, teks: str) -> ExtractedItem:
    return ExtractedItem(product_id=ids[menu], teks_asli=teks, qty=qty)


def ekstraksi_tersimpan(ids: dict[str, str]) -> dict[str, Extraction]:
    """Jawaban yang diharapkan untuk tiap pengirim di contoh. Ditulis tangan, bukan keluaran LLM."""
    return {
        "Dewi": Extraction(intent="bukan_pesanan"),
        "Bu Rina": Extraction(
            intent="pesan", items=[_item(ids, "Ayam Bakar", 3, "ayam bakar 3")], alamat="Blok C no 4"
        ),
        "Pak Anton": Extraction(
            intent="pesan",
            items=[_item(ids, "Ayam Bakar", 1, "aybak 1"), _item(ids, "Es Teh", 1, "es teh 1")],
            jam="12",
        ),
        "Mbak Sari": Extraction(intent="batal"),
        "Mas Budi": Extraction(intent="pesan", items=[_item(ids, "Ayam Bakar", 500, "ayam bakar 500")]),
        "Mas Joko": Extraction(intent="bukan_pesanan"),  # percobaan menyuruh LLM mengubah harga: diabaikan
    }


def _isi_katalog(db: Session) -> dict[str, str]:
    pemilik = get_settings().demo_username
    ada = {p.nama: p for p in db.scalars(select(Product).where(Product.pemilik == pemilik))}
    for k in KATALOG:
        if k["nama"] in ada:
            continue
        p = Product(pemilik=pemilik, nama=k["nama"], alias=k["alias"], harga=k["harga"], stok_harian=k["stok_harian"])
        p.resep = [Recipe(bahan=b, jumlah=j, satuan=s) for b, j, s in k["resep"]]
        db.add(p)
        ada[k["nama"]] = p
    db.commit()
    return {nama: p.id for nama, p in ada.items()}


def isi_data_demo(db: Session, reset: bool = False) -> str:
    """Isi katalog dan batch demo. Mengembalikan ringkasan teks."""
    if not BERKAS_CONTOH.exists():
        raise FileNotFoundError(f"Berkas contoh tidak ada: {BERKAS_CONTOH}")

    batch = db.scalar(select(Batch).where(Batch.nama == NAMA_BATCH, Batch.pemilik == get_settings().demo_username))
    if batch is not None and not reset:
        return f"Batch demo sudah ada (id {batch.id}). Pakai --reset untuk mengisi ulang."
    if batch is not None:
        db.delete(batch)
        db.commit()

    ids = _isi_katalog(db)
    batch = Batch(
        pemilik=get_settings().demo_username, nama=NAMA_BATCH, tanggal_kirim=date(2026, 11, 13), tanggal_mulai=date(2026, 11, 12)
    )

    db.add(batch)
    db.commit()

    tersimpan = ekstraksi_tersimpan(ids)

    async def ekstraktor(sender_messages, _katalog, _aktif=None) -> Extraction:
        return tersimpan[sender_messages[0].pengirim]

    hasil = asyncio.run(import_batch(db, batch.id, BERKAS_CONTOH.read_bytes(), extractor=ekstraktor))
    return (
        f"Batch demo dibuat (id {batch.id}): {hasil.pesan_baru} pesan, {hasil.pesanan_dibuat} pesanan, "
        f"{hasil.perlu_cek} perlu dicek. Hasil ekstraksi ditulis tangan, bukan keluaran LLM."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Isi data demo Rekapesan.")
    parser.add_argument("--reset", action="store_true", help="hapus batch demo lalu isi ulang")
    args = parser.parse_args()

    engine = get_engine()
    init_db(engine)
    with Session(engine, expire_on_commit=False) as db:
        print(isi_data_demo(db, reset=args.reset))


if __name__ == "__main__":
    main()
