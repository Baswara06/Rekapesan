from app import agent as modul_agent
from app import extractor as modul_extractor
from app.schemas import AgentAnswer, ProofSuggestion, TraceStep
from tests.api.conftest import id_pesanan

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def _setujui_rina_dan_anton(client):
    rina, anton = id_pesanan(client, "Bu Rina"), id_pesanan(client, "Pak Anton")
    client.patch(f"/api/orders/{rina}", json={"jam_kirim": "12:00"})
    client.post(f"/api/orders/{rina}/approve")
    client.post(f"/api/orders/{anton}/approve")
    return rina, anton


def test_rekap_dan_daftar_belanja_lewat_endpoint(client, pesanan_contoh):
    kosong = client.get("/api/batches/b-1/recap").json()
    assert kosong["omzet"] == 0 and kosong["menunggu_persetujuan"] == 3

    _setujui_rina_dan_anton(client)
    rekap = client.get("/api/batches/b-1/recap").json()
    assert rekap["omzet"] == 54000 + 23000
    assert rekap["menunggu_persetujuan"] == 1  # Mas Budi masih menunggu
    assert {p["nama"]: p["qty"] for p in rekap["produksi"]} == {"Ayam Bakar": 4, "Es Teh": 1}
    assert len(rekap["belum_bayar"]) == 2

    belanja = client.get("/api/batches/b-1/shopping-list").json()
    assert belanja == [
        {"bahan": "Ayam", "jumlah": 1.0, "satuan": "kg"},
        {"bahan": "Beras", "jumlah": 0.4, "satuan": "kg"},
    ]

    assert client.get("/api/batches/tidak-ada/recap").status_code == 404
    assert client.get("/api/batches/tidak-ada/shopping-list").status_code == 404


def test_konfirmasi_bayar_hanya_untuk_pesanan_yang_disetujui(client, pesanan_contoh):
    rina = id_pesanan(client, "Bu Rina")
    res = client.post(f"/api/orders/{rina}/payment-confirm")
    assert res.status_code == 409 and res.json()["error"]["kode"] == "validasi_gagal"

    client.post(f"/api/orders/{rina}/approve")
    assert client.post(f"/api/orders/{rina}/payment-confirm").json() == {"order_id": rina, "status": "dibayar"}
    assert client.post(f"/api/orders/{rina}/payment-confirm").json()["status"] == "dibayar"  # idempoten
    assert client.get("/api/batches/b-1/recap").json()["belum_bayar"] == []
    assert client.post("/api/orders/tidak-ada/payment-confirm").status_code == 404


def test_bukti_bayar_hanya_saran_status_tidak_berubah(client, pesanan_contoh, monkeypatch):
    rina = id_pesanan(client, "Bu Rina")
    client.post(f"/api/orders/{rina}/approve")

    async def baca(_gambar):
        return ProofSuggestion(nama="RINA", nominal=54000)

    monkeypatch.setattr(modul_extractor, "read_payment_proof", baca)
    res = client.post(f"/api/orders/{rina}/payment-proof", files={"file": ("bukti.png", PNG, "image/png")})
    assert res.status_code == 200 and res.json() == {"nama": "RINA", "nominal": 54000, "cocok": True}
    assert client.get(f"/api/orders/{rina}").json()["status"] == "dikonfirmasi"  # belum berubah

    async def salah(_gambar):
        return ProofSuggestion(nama="RINA", nominal=50000)

    monkeypatch.setattr(modul_extractor, "read_payment_proof", salah)
    res = client.post(f"/api/orders/{rina}/payment-proof", files={"file": ("bukti.png", PNG, "image/png")})
    assert res.json()["cocok"] is False

    client.post(f"/api/orders/{rina}/payment-confirm")
    assert client.get(f"/api/orders/{rina}").json()["status"] == "dibayar"


def test_bukti_bayar_menolak_bukan_gambar_dan_pembaca_belum_siap(client, pesanan_contoh):
    rina = id_pesanan(client, "Bu Rina")
    res = client.post(f"/api/orders/{rina}/payment-proof", files={"file": ("x.txt", b"halo", "text/plain")})
    assert res.status_code == 422 and res.json()["error"]["kode"] == "validasi_gagal"
    # Pembaca bukti bayar (Pangeran) masih stub: galat seragam, bukan 500.
    res = client.post(f"/api/orders/{rina}/payment-proof", files={"file": ("b.png", PNG, "image/png")})
    assert res.status_code == 503 and res.json()["error"]["kode"] == "llm_gagal"


def test_agen_tanya_jawab_menyertakan_trace(client, pesanan_contoh, monkeypatch):
    async def tanya(pertanyaan, batch_id, riwayat):
        assert batch_id == "b-1" and riwayat == []
        return AgentAnswer(
            answer="Ayam bakar jam 12:00: 4 porsi.",
            trace=[TraceStep(tool="rekap_produksi", argumen={"jam": "12:00"}, hasil_ringkas="4")],
        )

    monkeypatch.setattr(modul_agent, "ask_agent", tanya)
    res = client.post("/api/agent/ask", json={"batch_id": "b-1", "pertanyaan": "Berapa ayam bakar jam 12?", "riwayat": []})
    assert res.status_code == 200
    assert res.json() == {
        "jawaban": "Ayam bakar jam 12:00: 4 porsi.",
        "trace": [{"tool": "rekap_produksi", "argumen": {"jam": "12:00"}, "hasil_ringkas": "4"}],
    }


def test_agen_galat_seragam(client, pesanan_contoh):
    res = client.post("/api/agent/ask", json={"batch_id": "tidak-ada", "pertanyaan": "halo"})
    assert res.status_code == 404
    res = client.post("/api/agent/ask", json={"batch_id": "b-1", "pertanyaan": "halo"})  # agen masih stub
    assert res.status_code == 503 and res.json()["error"]["kode"] == "llm_gagal"
    assert client.post("/api/agent/ask", json={"batch_id": "b-1", "pertanyaan": ""}).status_code == 422
