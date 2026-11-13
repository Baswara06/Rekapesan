"""Gold set harus sah menurut skema bersama, supaya evaluasi Pangeran tidak gagal karena data."""

import json
from pathlib import Path

from app.schemas import CatalogEntry, Extraction, Message

GOLD = json.loads((Path(__file__).resolve().parents[2] / "sample" / "gold.json").read_text(encoding="utf-8"))


def test_gold_sah_menurut_skema():
    ids = {CatalogEntry.model_validate(k).id for k in GOLD["katalog"]}
    assert len(GOLD["kasus"]) >= 30
    assert len({k["id"] for k in GOLD["kasus"]}) == len(GOLD["kasus"])
    for kasus in GOLD["kasus"]:
        assert kasus["pesan"]
        for p in kasus["pesan"]:
            Message.model_validate({**p, "sidik": "x"})
        harapan = Extraction.model_validate(kasus["harapan"])
        for it in harapan.items:
            assert it.product_id is None or it.product_id in ids, kasus["id"]


def test_gold_memuat_lima_kasus_sulit_dan_tanpa_harga():
    kategori = {k["kategori"] for k in GOLD["kasus"]}
    assert {"ubah", "batal", "item_tidak_dikenal", "jumlah_tidak_wajar", "manipulasi"} <= kategori
    assert "harga" not in json.dumps(GOLD["katalog"])
