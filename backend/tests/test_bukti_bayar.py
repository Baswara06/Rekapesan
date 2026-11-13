"""Uji pembaca bukti bayar dengan LLM tiruan: saran saja, nominal dinormalisasi, galat jelas."""

import asyncio
import base64
import json

import pytest

from app.extractor import bukti, llm
from app.extractor.ekstrak import KeluaranTidakSah

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 16


def jalankan(coro):
    return asyncio.run(coro)


def pasang(monkeypatch, jawaban):
    tercatat = {}

    async def chat(pesan, model=None, max_tokens=0):
        tercatat.update(pesan=pesan, model=model)
        if isinstance(jawaban, BaseException):
            raise jawaban
        return jawaban

    monkeypatch.setattr(llm, "chat", chat)
    return tercatat


@pytest.mark.parametrize(
    ("mentah", "diharapkan"),
    [(54000, 54000), ("54000", 54000), ("Rp 54.000", 54000), ("Rp54.000,00", 54000), ("54,000", 54000),
     ("IDR 1.250.000", 1250000), (54000.0, 54000), (0, None), (-5, None), ("lima puluh", None), (None, None),
     (True, None), (12.5, None), ("", None),
     ("IDR 14,000.00", 14000), ("14,000.00", 14000), ("IDR 4,000.00", 4000)],  # format struk QRIS BCA asli
)
def test_nominal_dinormalisasi(mentah, diharapkan):
    assert bukti.nominal_dari(mentah) == diharapkan


def test_deteksi_mime():
    assert bukti.deteksi_mime(PNG) == "image/png" and bukti.deteksi_mime(JPEG) == "image/jpeg"
    assert bukti.deteksi_mime(b"RIFF\x00\x00\x00\x00WEBPxx") == "image/webp"
    assert bukti.deteksi_mime(b"%PDF-1.4") is None


def test_baca_bukti_mengembalikan_saran(monkeypatch):
    tercatat = pasang(monkeypatch, json.dumps({"nama": "RINA WULANDARI", "nominal": "Rp 54.000"}))
    saran = jalankan(bukti.read_payment_proof(PNG))
    assert (saran.nama, saran.nominal) == ("RINA WULANDARI", 54000)
    isi = tercatat["pesan"][1]["content"]
    url = next(b["image_url"]["url"] for b in isi if b["type"] == "image_url")
    assert url == "data:image/png;base64," + base64.b64encode(PNG).decode()


def test_model_vision_dari_pengaturan_dipakai(monkeypatch):
    class Cfg:
        vision_model = "model-vision"

    monkeypatch.setattr(bukti, "get_settings", lambda: Cfg())
    tercatat = pasang(monkeypatch, json.dumps({"nama": None, "nominal": None}))
    saran = jalankan(bukti.read_payment_proof(JPEG))
    assert tercatat["model"] == "model-vision" and (saran.nama, saran.nominal) == (None, None)


def test_tanpa_model_vision_memakai_model_utama(monkeypatch):
    class Cfg:
        vision_model = ""

    monkeypatch.setattr(bukti, "get_settings", lambda: Cfg())
    tercatat = pasang(monkeypatch, json.dumps({"nama": "A", "nominal": 1}))
    jalankan(bukti.read_payment_proof(PNG))
    assert tercatat["model"] is None


def test_hanya_saran_tidak_ada_kolom_lain(monkeypatch):
    pasang(monkeypatch, json.dumps({"nama": "A", "nominal": 100, "status": "dibayar", "cocok": True}))
    saran = jalankan(bukti.read_payment_proof(PNG))
    assert set(saran.model_dump()) == {"nama", "nominal"}


def test_keluaran_rusak_dan_bukan_gambar_dan_galat_penyedia(monkeypatch):
    pasang(monkeypatch, "maaf tidak terbaca")
    with pytest.raises(KeluaranTidakSah):
        jalankan(bukti.read_payment_proof(PNG))
    with pytest.raises(KeluaranTidakSah):
        jalankan(bukti.read_payment_proof(b"%PDF-1.4 bukan gambar"))
    pasang(monkeypatch, ConnectionError("putus"))
    with pytest.raises(ConnectionError):
        jalankan(bukti.read_payment_proof(PNG))
