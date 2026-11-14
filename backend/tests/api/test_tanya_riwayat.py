"""Uji riwayat Tanya AI: tersimpan per akun, dilanjutkan dari server, kedaluwarsa 30 hari, dan dibaca agen."""

from datetime import datetime, timedelta

from sqlalchemy import select

from app import agent as modul_agent
from app.agent import alat as alat_agen
from app.db import Percakapan, PesanTanya
from app.schemas import AgentAnswer, TraceStep


def _agen_tiruan(monkeypatch, catatan):
    async def tanya(pertanyaan, lingkup, riwayat, **kw):
        catatan.append({"pertanyaan": pertanyaan, "riwayat": riwayat, **kw})
        return AgentAnswer(answer=f"jawab: {pertanyaan}", trace=[TraceStep(tool="daftar_belum_bayar", hasil={"jumlah": 1})])

    monkeypatch.setattr(modul_agent, "ask_agent", tanya)


def test_percakapan_tersimpan_dan_dilanjutkan_dari_server(client, pesanan_contoh, monkeypatch):
    catatan = []
    _agen_tiruan(monkeypatch, catatan)
    r1 = client.post("/api/agent/ask", json={"pertanyaan": "Siapa belum bayar?"}).json()
    pid = r1["percakapan_id"]
    r2 = client.post("/api/agent/ask", json={"pertanyaan": "Kalau Bu Rina?", "percakapan_id": pid, "riwayat": [{"peran": "pengguna", "isi": "palsu"}]})
    assert r2.json()["percakapan_id"] == pid
    # Riwayat percakapan lanjutan dibaca dari server, bukan dari klien.
    assert catatan[1]["riwayat"] == [{"peran": "pengguna", "isi": "Siapa belum bayar?"}, {"peran": "agen", "isi": "jawab: Siapa belum bayar?"}]
    assert catatan[1]["pemilik"] == "demo" and catatan[1]["percakapan_id"] == pid

    daftar = client.get("/api/agent/percakapan").json()
    assert [(d["judul"], d["jumlah_pesan"]) for d in daftar] == [("Siapa belum bayar?", 4)]
    detail = client.get(f"/api/agent/percakapan/{pid}").json()
    assert [m["peran"] for m in detail["pesan"]] == ["pengguna", "agen", "pengguna", "agen"]
    assert detail["pesan"][1]["trace"][0]["tool"] == "daftar_belum_bayar"

    assert client.delete(f"/api/agent/percakapan/{pid}").status_code == 204
    assert client.get("/api/agent/percakapan").json() == []


def test_percakapan_kedaluwarsa_setelah_30_hari_tanpa_chat(client, db, pesanan_contoh, monkeypatch):
    _agen_tiruan(monkeypatch, [])
    lama = client.post("/api/agent/ask", json={"pertanyaan": "lama"}).json()["percakapan_id"]
    baru = client.post("/api/agent/ask", json={"pertanyaan": "baru"}).json()["percakapan_id"]
    p = db.get(Percakapan, lama)
    p.diubah_pada = datetime.now() - timedelta(days=31)
    db.commit()
    assert [d["id"] for d in client.get("/api/agent/percakapan").json()] == [baru]
    db.expire_all()
    assert db.get(Percakapan, lama) is None
    assert db.scalar(select(PesanTanya).where(PesanTanya.percakapan_id == lama)) is None


def test_percakapan_akun_lain_tidak_bisa_dibuka(client, db, pesanan_contoh, monkeypatch):
    db.add(Percakapan(id="asing", pemilik="bu_sari", judul="rahasia"))
    db.commit()
    assert client.get("/api/agent/percakapan").json() == []
    assert client.get("/api/agent/percakapan/asing").status_code == 404
    assert client.delete("/api/agent/percakapan/asing").status_code == 404
    _agen_tiruan(monkeypatch, [])
    assert client.post("/api/agent/ask", json={"pertanyaan": "x", "percakapan_id": "asing"}).status_code == 404


def test_tool_cari_riwayat_hanya_percakapan_lain_milik_sendiri(db):
    sekarang = datetime.now()
    db.add_all([
        Percakapan(id="p1", pemilik="demo", judul="Soal Bu Wulan", diubah_pada=sekarang),
        Percakapan(id="p2", pemilik="demo", judul="Sekarang", diubah_pada=sekarang),
        Percakapan(id="p3", pemilik="bu_sari", judul="Akun lain", diubah_pada=sekarang),
        Percakapan(id="p4", pemilik="demo", judul="Kedaluwarsa", diubah_pada=sekarang - timedelta(days=40)),
    ])
    db.add_all([
        PesanTanya(percakapan_id="p1", urutan=0, peran="pengguna", isi="Bu Wulan sudah bayar?"),
        PesanTanya(percakapan_id="p2", urutan=0, peran="pengguna", isi="Bu Wulan pesan apa?"),
        PesanTanya(percakapan_id="p3", urutan=0, peran="pengguna", isi="Bu Wulan rahasia"),
        PesanTanya(percakapan_id="p4", urutan=0, peran="pengguna", isi="Bu Wulan lama"),
    ])
    db.commit()
    r = alat_agen.cari_riwayat_tanya(db, "demo", "p2", "wulan")
    assert r["cocok"] == 1 and r["riwayat"][0]["isi"] == "Bu Wulan sudah bayar?" and r["riwayat"][0]["percakapan"] == "Soal Bu Wulan"
    assert alat_agen.cari_riwayat_tanya(db, "demo", "p2", "geprek")["cocok"] == 0
