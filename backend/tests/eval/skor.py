"""Penilaian ekstraktor terhadap `sample/gold.json`. Pemilik: Pangeran.

Tiga hasil per kasus:
- `benar`: intent, daftar (product_id, qty), dan ada/tidaknya jam dan alamat cocok dengan jawaban benar.
- `tertangkap`: salah, tetapi mesin aturan memberi tanda yang memang menandai kesalahan ekstraksi
  (`gagal_diekstrak`, `item_tidak_dikenal`, `jumlah_kosong`, `jumlah_tidak_wajar`, `mungkin_dobel`), sehingga
  penjual diminta memeriksa. Tanda umum (`jam_kosong`, `alamat_kosong`, `stok_kurang`) sengaja tidak dihitung,
  karena muncul juga pada pesanan yang benar.
- `lolos`: salah dan tidak ada tanda. Ini kesalahan yang sampai ke penjual tanpa peringatan, termasuk pesanan
  yang diabaikan diam-diam. Angka ini yang terpenting.

Galat penyedia (kuota habis, jaringan) dihitung terpisah sebagai `galat`, bukan salah ekstraksi.
"""

import asyncio
import json
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.rules import apply_intent, normalisasi_jam
from app.schemas import CatalogEntry, Extraction, Message

GOLD = Path(__file__).resolve().parents[3] / "sample" / "gold.json"
TANDA_PENANGKAP = {"gagal_diekstrak", "item_tidak_dikenal", "jumlah_kosong", "jumlah_tidak_wajar", "mungkin_dobel"}
MAKS_PARALEL = 5
HARGA_UJI = 1  # harga tidak memengaruhi tanda; hanya agar mesin aturan bisa dijalankan

Ekstraktor = Callable[..., Awaitable[Extraction]]


@dataclass
class HasilKasus:
    id: str
    kategori: str
    status: str  # benar | tertangkap | lolos | galat
    alasan: str = ""
    tanda: list[str] = field(default_factory=list)


def muat_gold(path: Path = GOLD) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _item_kunci(e: Extraction) -> Counter:
    return Counter((it.product_id, it.qty) for it in e.items)


def _jam(nilai: str | None) -> str | None:
    return normalisasi_jam(nilai)


def bandingkan(prediksi: Extraction, harapan: Extraction) -> str:
    """Kosong bila cocok, selain itu alasan perbedaan pertama."""
    if prediksi.gagal:
        return "ekstraksi gagal"
    if prediksi.intent != harapan.intent:
        return f"intent {prediksi.intent} (seharusnya {harapan.intent})"
    if _item_kunci(prediksi) != _item_kunci(harapan):
        return "item atau jumlah berbeda"
    if (_jam(prediksi.jam) is None) != (_jam(harapan.jam) is None):
        return "jam salah (ada/tidaknya)"
    if _jam(harapan.jam) and _jam(prediksi.jam) != _jam(harapan.jam):
        return f"jam {prediksi.jam} (seharusnya {harapan.jam})"
    if bool(prediksi.alamat) != bool(harapan.alamat):
        return "alamat salah (ada/tidaknya)"
    return ""


def tanda_untuk(prediksi: Extraction, kasus: dict[str, Any], katalog: list[dict[str, Any]]) -> list[str]:
    """Tanda kuning yang akan diberikan mesin aturan untuk prediksi ini."""
    if prediksi.gagal:
        return ["gagal_diekstrak"]
    aktif = kasus.get("pesanan_aktif")
    konteks = {
        "catalog": {k["id"]: {"nama": k["nama"], "harga": HARGA_UJI, "stok_harian": None, "aktif": True} for k in katalog},
        "active_order": (
            {
                "id": "aktif",
                "status": "perlu_cek",
                "jam_kirim": aktif["jam_kirim"],
                "alamat": aktif["alamat"],
                "catatan": aktif["catatan"],
                "total": 0,
                "tanda": [],
                "items": [{**it, "harga_satuan": HARGA_UJI} for it in aktif["items"]],
            }
            if aktif
            else None
        ),
        "terpakai": {},
    }
    return list(apply_intent(konteks, prediksi).tanda)


def nilai_kasus(kasus: dict[str, Any], katalog: list[dict[str, Any]], prediksi: Extraction) -> HasilKasus:
    alasan = bandingkan(prediksi, Extraction.model_validate(kasus["harapan"]))
    if not alasan:
        return HasilKasus(kasus["id"], kasus["kategori"], "benar")
    tanda = tanda_untuk(prediksi, kasus, katalog)
    status = "tertangkap" if TANDA_PENANGKAP & set(tanda) else "lolos"
    return HasilKasus(kasus["id"], kasus["kategori"], status, alasan, tanda)


async def evaluasi(extractor: Ekstraktor, gold: dict[str, Any] | None = None) -> list[HasilKasus]:
    """Jalankan ekstraktor ke semua kasus gold (paralel, terbatas) dan nilai hasilnya."""
    gold = gold or muat_gold()
    katalog = gold["katalog"]
    entri = [CatalogEntry.model_validate(k) for k in katalog]
    kunci = asyncio.Semaphore(MAKS_PARALEL)

    async def satu(kasus: dict[str, Any]) -> HasilKasus:
        pesan = [Message.model_validate({**p, "sidik": "uji"}) for p in kasus["pesan"]]
        async with kunci:
            try:
                prediksi = await extractor(pesan, entri, kasus.get("pesanan_aktif"))
            except Exception as exc:  # noqa: BLE001 - galat penyedia dilaporkan terpisah
                return HasilKasus(kasus["id"], kasus["kategori"], "galat", f"{type(exc).__name__}: {exc}"[:200])
        return nilai_kasus(kasus, katalog, prediksi)

    return await asyncio.gather(*(satu(k) for k in gold["kasus"]))


def ringkas(hasil: list[HasilKasus]) -> dict[str, int]:
    return dict(Counter(h.status for h in hasil))


def laporan_markdown(hasil: list[HasilKasus]) -> str:
    """Tabel siap tempel ke `docs/evaluasi.md`. Persentase dihitung dari kasus yang dinilai (tanpa galat)."""
    n = ringkas(hasil)
    dinilai = len(hasil) - n.get("galat", 0)

    def baris(nama: str, kunci: str) -> str:
        j = n.get(kunci, 0)
        return f"| {nama} | {j} | {100 * j / dinilai:.1f}% |" if dinilai else f"| {nama} | {j} | - |"

    teks = [
        f"Kasus dinilai: {dinilai} dari {len(hasil)}" + (f" ({n['galat']} galat penyedia)" if n.get("galat") else ""),
        "",
        "| Kategori | Jumlah | Persen |",
        "| --- | --- | --- |",
        baris("Benar seluruhnya", "benar"),
        baris("Salah, **tertangkap** tanda kuning", "tertangkap"),
        baris("Salah, **lolos tanpa tanda**", "lolos"),
        "",
        "| Kasus (kategori) | Benar | Total |",
        "| --- | --- | --- |",
    ]
    per_kat: dict[str, list[HasilKasus]] = {}
    for h in hasil:
        if h.status != "galat":
            per_kat.setdefault(h.kategori, []).append(h)
    for kat, hs in sorted(per_kat.items()):
        teks.append(f"| {kat} | {sum(h.status == 'benar' for h in hs)} | {len(hs)} |")
    salah = [h for h in hasil if h.status in ("tertangkap", "lolos", "galat")]
    if salah:
        teks += ["", "Kasus yang salah:", "", "| Id | Kategori | Status | Alasan |", "| --- | --- | --- | --- |"]
        teks += [f"| {h.id} | {h.kategori} | {h.status} | {h.alasan} |" for h in salah]
    return "\n".join(teks)
