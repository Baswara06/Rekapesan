"""Skema data bersama antar-modul (rancangan awal).

Ini kontrak antar-modul di `docs/arsitektur.md`. Mengubah bentuk di sini berarti
mengubah kerja orang lain, jadi lakukan lewat Pull Request dan kabari pemilik modul.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Tanda = Literal[
    "item_tidak_dikenal",
    "jumlah_kosong",
    "jumlah_tidak_wajar",
    "alamat_kosong",
    "jam_kosong",
    "stok_kurang",
    "mungkin_dobel",
    "gagal_diekstrak",
]

Intent = Literal["pesan", "ubah", "batal", "bukan_pesanan"]


class Message(BaseModel):
    """Satu pesan WhatsApp hasil parser (Satria)."""

    waktu: datetime
    pengirim: str
    isi: str
    sidik: str = Field(description="sha256(waktu + pengirim + isi + urutan_dalam_menit)")


class CatalogEntry(BaseModel):
    """Katalog yang dikirim ke LLM. TIDAK memuat harga."""

    id: str
    nama: str
    alias: list[str] = []


class ExtractedItem(BaseModel):
    product_id: str | None = None
    teks_asli: str
    qty: int | None = None
    catatan_item: str | None = None


class Extraction(BaseModel):
    """Keluaran ekstraktor LLM (Pangeran). Tidak pernah berisi harga."""

    intent: Intent
    items: list[ExtractedItem] = []
    tanggal: str | None = None
    jam: str | None = None
    alamat: str | None = None
    catatan: str | None = None
    gagal: bool = False


class OrderChange(BaseModel):
    """Hasil penerapan intent ke pesanan (Satria, mesin aturan)."""

    order_id: str | None = None
    aksi: Literal["buat", "ubah", "batal", "abaikan"]
    sebelum: dict[str, Any] | None = None
    sesudah: dict[str, Any] | None = None
    tanda: list[Tanda] = []


class TraceStep(BaseModel):
    tool: str
    argumen: dict[str, Any] = {}
    hasil_ringkas: str = ""


class AgentAnswer(BaseModel):
    answer: str
    trace: list[TraceStep] = []


class ProofSuggestion(BaseModel):
    """Saran dari model vision. Keputusan tetap di kode dan penjual."""

    nama: str | None = None
    nominal: int | None = None
