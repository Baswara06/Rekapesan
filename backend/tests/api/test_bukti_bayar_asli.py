"""Endpoint bukti bayar dengan pembaca asli dan LLM tiruan: saran, pencocokan oleh kode, status tak berubah."""

import json

from app.extractor import llm
from tests.api.conftest import id_pesanan

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def _pasang(monkeypatch, jawaban):
    async def chat(*_a, **_k):
        if isinstance(jawaban, BaseException):
            raise jawaban
        return jawaban

    monkeypatch.setattr(llm, "chat", chat)


def test_bukti_bayar_cocok_dihitung_kode_dan_status_tetap(client, pesanan_contoh, monkeypatch):
    rina = id_pesanan(client, "Bu Rina")
    client.post(f"/api/orders/{rina}/approve")
    _pasang(monkeypatch, json.dumps({"nama": "Rina", "nominal": "Rp 54.000", "cocok": True, "status": "dibayar"}))
    res = client.post(f"/api/orders/{rina}/payment-proof", files={"file": ("b.png", PNG, "image/png")})
    assert res.json() == {"nama": "Rina", "nominal": 54000, "cocok": True}
    assert client.get(f"/api/orders/{rina}").json()["status"] == "dikonfirmasi"


def test_nominal_beda_tidak_cocok_dan_bacaan_gagal_menjadi_502(client, pesanan_contoh, monkeypatch):
    rina = id_pesanan(client, "Bu Rina")
    _pasang(monkeypatch, json.dumps({"nama": "Rina", "nominal": 100}))
    res = client.post(f"/api/orders/{rina}/payment-proof", files={"file": ("b.png", PNG, "image/png")})
    assert res.json()["cocok"] is False

    _pasang(monkeypatch, "tidak terbaca")
    res = client.post(f"/api/orders/{rina}/payment-proof", files={"file": ("b.png", PNG, "image/png")})
    assert res.status_code == 502 and res.json()["error"]["kode"] == "llm_gagal"
